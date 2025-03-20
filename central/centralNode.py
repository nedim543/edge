from flask import Flask, request, jsonify

app = Flask(__name__)

data_store = {}  # {"a": [{"timestamp": "...", "caseid": "...", "activity": "...", "node": "...", "used_as_predecessor": False}, ...]}
footprint_matrix = {}  # {"a": {"a":0,"b":0,"c":0}, "b": {"a":0,"b":0,"c":0}}

@app.route("/store", methods=["POST"])
def store_data():
    data = request.json
    if not data or "node" not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    node_name = data["node"]

    # Falls neue Node → in footprint_matrix und data_store hinzufügen
    if node_name not in footprint_matrix:
        footprint_matrix[node_name] = {other_node: 0 for other_node in footprint_matrix}  # Initialisiere alle Zählungen auf 0
        for other_node in data_store:  # Stelle sicher, dass alle anderen Nodes auch als Vorgänger gezählt werden
            footprint_matrix[other_node][node_name] = 0  # auch umgekehrt, damit die umgekehrte Zählung existiert

    if node_name not in data_store:
        data_store[node_name] = []
    
    # Neues Event
    event = {
        "timestamp": data["timestamp"],
        "caseid": data["caseid"],
        "activity": data["activity"],
        "node": data["node"],
        "used_as_predecessor": False  # Wird später gesetzt, wenn Node als Vorgänger verwendet wird
    }

    # Vorgänger suchen: Der Vorgänger muss den gleichen caseid haben, älter sein und noch nicht verwendet worden sein
    predecessor_found = False
    best_predecessor = None
    best_predecessor_timestamp = None  # Wir vergleichen direkt die Timestamps

    # Alle Nodes und deren Events durchsuchen
    for other_node in data_store:
        if other_node == node_name:
            continue  # Überspringe die aktuelle Node, da wir nur Vorgänger von anderen Nodes suchen möchten

        for prev_event in data_store[other_node]:  # Events für die andere Node durchsuchen
            # Vorgänger muss denselben caseid haben und der timestamp des Vorgängers muss kleiner sein
            if prev_event["caseid"] == event["caseid"] and prev_event["timestamp"] < event["timestamp"] and not prev_event["used_as_predecessor"]:
                # Vergleiche den timestamp des aktuellen Vorgängers mit dem besten Vorgänger
                if best_predecessor_timestamp is None or prev_event["timestamp"] > best_predecessor_timestamp:
                    best_predecessor = prev_event
                    best_predecessor_timestamp = prev_event["timestamp"]  # Aktualisiere den besten Vorgänger mit dem neuen Timestamp

    # Wenn ein passender Vorgänger gefunden wurde, aktualisiere footprint_matrix und setze "used_as_predecessor" auf True
    if best_predecessor:
        # Vorgänger ist der am dichtesten liegende Event
        predecessor_found = True
        best_predecessor["used_as_predecessor"] = True  # Vorgänger-Flag setzen

        # footprint_matrix aktualisieren: Der aktuelle Node wird als Vorgänger des gefundenen Vorgängers gezählt
        footprint_matrix[node_name][best_predecessor["node"]] += 1

        print(f"Event {event} has {best_predecessor} as its predecessor.")

    # Event speichern
    data_store[node_name].append(event)
    print(f"Stored data for node {node_name}: {event}")
    
    return jsonify({"message": "Data stored successfully"}), 200

@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(data_store), 200

@app.route("/footprint", methods=["GET"])
def get_footprint():
    return jsonify(footprint_matrix), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
