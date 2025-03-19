from flask import Flask, request, jsonify
import json
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# File-based communication with the Tkinter app
COMMAND_FILE = "camera_commands.json"

@app.route('/')
def home():
    return "Alexa Surveillance Camera API is running!"

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "online"})

@app.route('/api/alexa', methods=['POST'])
def alexa_endpoint():
    try:
        data = request.json
        logging.info(f"Received Alexa request: {data}")
        
        # Verify request is from Alexa
        if 'request' not in data:
            return jsonify({"error": "Invalid request format"}), 400
        
        # Process the request
        request_type = data['request']['type']
        
        # Handle LaunchRequest
        if request_type == 'LaunchRequest':
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "Welcome to Surveillance Camera Control. You can say open camera 1, or remove camera 2."
                    },
                    "shouldEndSession": False
                }
            })
        
        # Handle IntentRequest
        elif request_type == 'IntentRequest':
            intent_name = data['request']['intent']['name']
            
            if intent_name == 'OpenCameraIntent':
                return handle_open_camera(data)
            elif intent_name == 'CloseCameraIntent':
                return handle_close_camera(data)
            else:
                return jsonify({
                    "version": "1.0",
                    "response": {
                        "outputSpeech": {
                            "type": "PlainText",
                            "text": "I didn't understand that command. You can say open camera 1, or remove camera 2."
                        },
                        "shouldEndSession": False
                    }
                })
        
        # Handle SessionEndedRequest
        elif request_type == 'SessionEndedRequest':
            return jsonify({
                "version": "1.0",
                "response": {
                    "shouldEndSession": True
                }
            })
        
        return jsonify({"error": "Unsupported request type"}), 400
        
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

def handle_open_camera(data):
    try:
        slots = data['request']['intent']['slots']
        cameras = []
        open_all = False
        
        # Check for "all" cameras
        if 'AllCameras' in slots and slots['AllCameras'].get('value'):
            open_all = True
        
        # Check for single camera
        if 'CameraNumber' in slots and slots['CameraNumber'].get('value'):
            cameras.append(int(slots['CameraNumber']['value']))
        
        # Check for first camera in a pair
        if 'FirstCamera' in slots and slots['FirstCamera'].get('value'):
            cameras.append(int(slots['FirstCamera']['value']))
        
        # Check for second camera in a pair
        if 'SecondCamera' in slots and slots['SecondCamera'].get('value'):
            cameras.append(int(slots['SecondCamera']['value']))
        
        if not cameras and not open_all:
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "Please specify which camera you want to open."
                    },
                    "shouldEndSession": False
                }
            })
        
        # Write command to file for Tkinter app to read
        with open(COMMAND_FILE, 'w') as f:
            if open_all:
                json.dump({
                    "action": "open",
                    "cameras": [1, 2, 3]  # All available cameras
                }, f)
                response_text = "Opening all cameras"
            else:
                json.dump({
                    "action": "open",
                    "cameras": cameras
                }, f)
                camera_list = " and ".join([str(cam) for cam in cameras])
                response_text = f"Opening camera {camera_list}"
        
        # Generate response
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": response_text
                },
                "shouldEndSession": True
            }
        })
        
    except Exception as e:
        logging.error(f"Error handling open camera: {e}")
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

def handle_close_camera(data):
    try:
        slots = data['request']['intent']['slots']
        cameras = []
        close_all = False
        
        # Check for "all" cameras
        if 'AllCameras' in slots and slots['AllCameras'].get('value'):
            close_all = True
        
        # Check for single camera
        if 'CameraNumber' in slots and slots['CameraNumber'].get('value'):
            cameras.append(int(slots['CameraNumber']['value']))
        
        # Check for first camera in a pair
        if 'FirstCamera' in slots and slots['FirstCamera'].get('value'):
            cameras.append(int(slots['FirstCamera']['value']))
        
        # Check for second camera in a pair
        if 'SecondCamera' in slots and slots['SecondCamera'].get('value'):
            cameras.append(int(slots['SecondCamera']['value']))
        
        if not cameras and not close_all:
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "Please specify which camera you want to close, or say 'all' to close all cameras."
                    },
                    "shouldEndSession": False
                }
            })
        
        # Write command to file for Tkinter app to read
        with open(COMMAND_FILE, 'w') as f:
            if close_all:
                json.dump({
                    "action": "close",
                    "cameras": ["all"]
                }, f)
                response_text = "Closing all cameras"
            else:
                json.dump({
                    "action": "close",
                    "cameras": cameras
                }, f)
                camera_list = " and ".join([str(cam) for cam in cameras])
                response_text = f"Closing camera {camera_list}"
        
        # Generate response
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": response_text
                },
                "shouldEndSession": True
            }
        })
        
    except Exception as e:
        logging.error(f"Error handling close camera: {e}")
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)