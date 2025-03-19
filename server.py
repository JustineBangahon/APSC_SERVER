import cv2
import threading
import queue
import time
from flask import Flask, Response, render_template, request, jsonify
import os
import logging
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Camera RTSP URLs 
CAMERA_URLS = {
    1: "rtsp://camera1:camera1@192.168.43.67/stream1",
    2: "rtsp://camera2:camera2@192.168.43.68/stream1", 
    3: "rtsp://camera3:camera3@192.168.43.69/stream1"
}

# Global variables to track camera states
camera_states = {
    1: False,
    2: False,
    3: False
}

# Queues for each camera's frames
frame_queues = {
    1: queue.Queue(maxsize=1),
    2: queue.Queue(maxsize=1),
    3: queue.Queue(maxsize=1)
}

def capture_camera(camera_id):
    """Capture frames from a specific camera"""
    url = CAMERA_URLS[camera_id]
    cap = None
    
    while True:
        try:
            # Only attempt to capture if camera state is True
            if not camera_states[camera_id]:
                time.sleep(1)
                continue
            
            # If not already connected, try to connect
            if cap is None or not cap.isOpened():
                cap = cv2.VideoCapture(url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            
            # Read frame
            ret, frame = cap.read()
            
            if not ret:
                logging.error(f"Failed to capture frame from camera {camera_id}")
                cap.release()
                cap = None
                time.sleep(2)
                continue
            
            # Resize frame to reduce bandwidth and processing
            frame = cv2.resize(frame, (640, 480))
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            
            # Clear the queue and put the latest frame
            try:
                frame_queues[camera_id].get_nowait()
            except queue.Empty:
                pass
            
            frame_queues[camera_id].put(buffer.tobytes())
        
        except Exception as e:
            logging.error(f"Error in camera {camera_id} capture: {e}")
            time.sleep(2)

def generate_frames(camera_id):
    """Generate frames for a specific camera"""
    while True:
        try:
            # Wait for a frame if camera is open
            if camera_states[camera_id]:
                frame = frame_queues[camera_id].get(timeout=2)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(1)
        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Error generating frames for camera {camera_id}: {e}")
            time.sleep(1)

# Start capture threads for all cameras
for camera_id in CAMERA_URLS:
    thread = threading.Thread(target=capture_camera, args=(camera_id,), daemon=True)
    thread.start()

@app.route('/')
def index():
    """Render the main page with camera status"""
    return render_template('index.html', cameras=camera_states)

@app.route('/camera/<int:camera_id>/stream')
def video_feed(camera_id):
    """Video streaming route"""
    return Response(generate_frames(camera_id), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/alexa', methods=['POST'])
def alexa_endpoint():
    """
    Main endpoint for Alexa Skill requests
    Follows the Alexa Skills Kit JSON interface
    """
    try:
        # Validate the request is from Alexa Skill
        # You might want to add signature verification here
        request_payload = request.json
        logging.info(f"Received Alexa request: {request_payload}")

        # Extract request type and intent
        request_type = request_payload.get('request', {}).get('type')
        
        # Handle Launch Request
        if request_type == 'LaunchRequest':
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "Welcome to Surveillance Camera Control. You can say open camera 1, or close camera 2."
                    },
                    "shouldEndSession": False
                }
            })
        
        # Handle Intent Requests
        elif request_type == 'IntentRequest':
            intent = request_payload['request']['intent']
            intent_name = intent['name']
            
            # Open Camera Intent
            if intent_name == 'OpenCameraIntent':
                return process_open_camera_intent(intent)
            
            # Close Camera Intent
            elif intent_name == 'CloseCameraIntent':
                return process_close_camera_intent(intent)
            
            # Show All Cameras Intent
            elif intent_name == 'ShowAllCamerasIntent':
                return open_all_cameras()
        
        # Handle session end
        elif request_type == 'SessionEndedRequest':
            return jsonify({"version": "1.0", "response": {}})
        
        # Unhandled request type
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "I'm sorry, I didn't understand that command."
                },
                "shouldEndSession": True
            }
        })
    
    except Exception as e:
        logging.error(f"Alexa endpoint error: {e}")
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "There was an error processing your request."
                },
                "shouldEndSession": True
            }
        })

def process_open_camera_intent(intent):
    """Process Open Camera Intent"""
    slots = intent.get('slots', {})
    cameras_to_open = []
    
    # Check for all cameras
    if slots.get('AllCameras', {}).get('value'):
        cameras_to_open = list(CAMERA_URLS.keys())
    
    # Check for specific camera numbers
    if slots.get('CameraNumber', {}).get('value'):
        cameras_to_open.append(int(slots['CameraNumber']['value']))
    
    if slots.get('FirstCamera', {}).get('value'):
        cameras_to_open.append(int(slots['FirstCamera']['value']))
    
    if slots.get('SecondCamera', {}).get('value'):
        cameras_to_open.append(int(slots['SecondCamera']['value']))
    
    # Validate camera numbers
    valid_cameras = [cam for cam in cameras_to_open if cam in CAMERA_URLS]
    
    if not valid_cameras:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Please specify a valid camera number."
                },
                "shouldEndSession": False
            }
        })
    
    # Open specified cameras
    for cam in valid_cameras:
        camera_states[cam] = True
    
    camera_list = " and ".join(map(str, valid_cameras))
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": f"Opening camera {camera_list}"
            },
            "shouldEndSession": True
        }
    })

def process_close_camera_intent(intent):
    """Process Close Camera Intent"""
    slots = intent.get('slots', {})
    cameras_to_close = []
    
    # Check for all cameras
    if slots.get('AllCameras', {}).get('value'):
        cameras_to_close = list(CAMERA_URLS.keys())
    
    # Check for specific camera numbers
    if slots.get('CameraNumber', {}).get('value'):
        cameras_to_close.append(int(slots['CameraNumber']['value']))
    
    if slots.get('FirstCamera', {}).get('value'):
        cameras_to_close.append(int(slots['FirstCamera']['value']))
    
    if slots.get('SecondCamera', {}).get('value'):
        cameras_to_close.append(int(slots['SecondCamera']['value']))
    
    # Validate camera numbers
    valid_cameras = [cam for cam in cameras_to_close if cam in CAMERA_URLS]
    
    if not valid_cameras:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Please specify a valid camera number."
                },
                "shouldEndSession": False
            }
        })
    
    # Close specified cameras
    for cam in valid_cameras:
        camera_states[cam] = False
    
    camera_list = " and ".join(map(str, valid_cameras))
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": f"Closing camera {camera_list}"
            },
            "shouldEndSession": True
        }
    })

def open_all_cameras():
    """Open all cameras"""
    for cam in CAMERA_URLS:
        camera_states[cam] = True
    
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": "Opening all cameras"
            },
            "shouldEndSession": True
        }
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Port from environment or default
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
