from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

CENTRAL_NODE_URL = "http://central-node:5000/store"

@app.route("/event", methods=["POST"])
def receive_data():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    
    print(f"Received data: {data}")
    
    # Sende die Daten an die zentrale Node
    try:
        response = requests.post(CENTRAL_NODE_URL, json=data)
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
