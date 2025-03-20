# Node 2: Sender and Receiver
from flask import Flask, request, jsonify
import requests
import threading
import time
from datetime import datetime

# Flask App for Node 2
node2 = Flask(__name__)

# Endpoint to receive events
@node2.route('/event', methods=['POST'])
def receive_event():
    event = request.get_json()
    time.sleep(5)
    print(f"Node 2 received: {event}")
    # Send the received event back to Node 1
    try:
        response = requests.post('http://127.0.0.1:5000/event', json=event)
        print(f"Node 2 sent event back to Node 1, Response: {response.status_code}")
    except Exception as e:
        print(f"Node 2 failed to send event back to Node 1: {e}")
    return jsonify({"status": "received and forwarded"}), 200

# Run Node 2 Flask app in a thread
def run_node2():
    node2.run(port=5001)

if __name__ == "__main__":
    # Start Flask app
    run_node2()
