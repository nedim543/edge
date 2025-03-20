# Node 1: Receiver
from flask import Flask, request, jsonify
import requests
import threading
import time
from datetime import datetime

# Flask App for Node 1
node1 = Flask(__name__)

# Endpoint to receive events
@node1.route('/event', methods=['POST'])
def receive_event():
    event = request.get_json()
    time.sleep(5)
    print(f"Node 1 received: {event}")

    try:
        response = requests.post('http://127.0.0.1:5001/event', json=event)
        print(f"Node 1 sent event back to Node 1, Response: {response.status_code}")
    except Exception as e:
        print(f"Node 1 failed to send event back to Node 1: {e}")
    return jsonify({"status": "received and forwarded"}), 200
    
def send_initial_event():
    time.sleep(2)  # Delay to ensure Node 2 is ready
    event = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'activity': 'Start Communication',
        'caseid': 'case_0',
        'node': 'Node1',
        'group': 'initial'
    }
    try:
        response = requests.post('http://127.0.0.1:5001/event', json=event)
        print("test1")
    except Exception as e:
        print(f"Node 1 failed to send initial event: {e}")

# Run Node 1 Flask app in a thread
def run_node1():
    node1.run(port=5000)

if __name__ == "__main__":
    # Start Flask app in a separate thread
    threading.Thread(target=run_node1).start()
    # Send initial event to Node 2
    send_initial_event()
