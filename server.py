# server.py (MINIMAL VERSION FOR RENDER)
from flask import Flask, request, jsonify
import json
import os
import logging
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
# Set RASPBERRY_PI_ADDRESS in your Render environment variables
PI_ADDRESS = os.environ.get('RASPBERRY_PI_ADDRESS', None)

@app.route('/')
def home():
    return "Alexa Surveillance Camera API is running!"

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "online"})

@app.route('/api/test-pi-connection', methods=['GET'])
def test_pi_connection():
    """Test if we can reach the Raspberry Pi"""
    if not PI_ADDRESS:
        return jsonify({"error": "RASPBERRY_PI_ADDRESS not configured"}), 400
    
    try:
        response = requests.get(f"{PI_ADDRESS}/status", timeout=5)
        return jsonify({"status": "success", "pi_response": response.json()}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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

def send_command_to_pi(command_data):
    """Send a command to the Raspberry Pi"""
    if not PI_ADDRESS:
        logging.error("RASPBERRY_PI_ADDRESS not configured")
        return {"error": "RASPBERRY_PI_ADDRESS not configured"}
    
    try:
        response = requests.post(f"{PI_ADDRESS}/command", json=command_data, timeout=5)
        return response.json()
    except Exception as e:
        logging.error(f"Error sending command to Pi: {e}")
        return {"error": f"Failed to send command to Raspberry Pi: {str(e)}"}

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
        
        # Prepare command to send to Raspberry Pi
        if open_all:
            command_data = {
                "action": "open",
                "cameras": [1, 2, 3]  # All available cameras
            }
            response_text = "Opening all cameras"
        else:
            command_data = {
                "action": "open",
                "cameras": cameras
            }
            camera_list = " and ".join([str(cam) for cam in cameras])
            response_text = f"Opening camera {camera_list}"
        
        # Send command to Raspberry Pi
        pi_response = send_command_to_pi(command_data)
        logging.info(f"Pi response: {pi_response}")
        
        # Generate Alexa response
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
        
        # Prepare command to send to Raspberry Pi
        if close_all:
            command_data = {
                "action": "close",
                "cameras": ["all"]
            }
            response_text = "Closing all cameras"
        else:
            command_data = {
                "action": "close",
                "cameras": cameras
            }
            camera_list = " and ".join([str(cam) for cam in cameras])
            response_text = f"Closing camera {camera_list}"
        
        # Send command to Raspberry Pi
        pi_response = send_command_to_pi(command_data)
        logging.info(f"Pi response: {pi_response}")
        
        # Generate Alexa response
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)