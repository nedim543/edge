from flask import Flask, request, jsonify
from kubernetes import client, config
import datetime
import os
import requests
import socket

app = Flask(__name__)

# Lokale Datenstrukturen für Events und die Footprint-Matrix
local_events = {}  # Liste von lokal gespeicherten Events
footprint_matrix = {} # Footprint-Matrix: {node: count}

# Liste von Peers (andere Nodes), die zur Kommunikation verwendet werden
peers = []  # Dynamisch durch Registrierung gefüllt
pod_ips = []

namespace = "edge-network"

# Lade die Kubernetes-Konfiguration
#TODO: service ip
try:
    config.load_incluster_config()  # Für den Einsatz in einem Kubernetes-Cluster
except:
    config.load_kube_config()  # Für lokale Entwicklung

#aktualisiert die podliste und initzalisiert die footprint matrix
def update_podlist():
    global pod_ips, footprint_matrix

    # Kubernetes API-Client
    v1 = client.CoreV1Api()

    # Temporäre Liste für IPs
    temp_pod_ips = []
    
    # Pods im Namespace abrufen
    try:
        pods = v1.list_namespaced_pod(namespace)
        for pod in pods.items:
            # Pod-IP abrufen
            if pod.status.pod_ip:
                pod_url = f"http://{pod.status.pod_ip}:5000"
                temp_pod_ips.append(pod_url)

            # Container-Umgebungsvariablen abrufen
            containers = pod.spec.containers
            for container in containers:
                if container.env:
                    for env_var in container.env:
                        if env_var.name == "NAME":  # Prüfen, ob `NAME` existiert
                            if env_var.value not in footprint_matrix:
                                footprint_matrix[env_var.value] = 0  # Initialisieren
    except client.exceptions.ApiException as e:
        print(f"Fehler beim Abrufen der Pods: {e}")

    # Globale Variablen aktualisieren
    pod_ips = temp_pod_ips
    

@app.route('/pods', methods=['GET'])
def get_pod_ips():
    

    try:
       update_podlist()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"pod_ips": pod_ips, 'matrix': footprint_matrix})

@app.route('/register', methods=['POST'])
def register_node():
    """
    Registrierung von anderen Nodes (Peers).
    Jeder Node kann seine Adresse übermitteln, und diese wird der Peer-Liste hinzugefügt.
    """
    global peers
    data = request.json
    peers.append(data['node_address'])
    footprint_node = data['node']
    footprint_matrix[footprint_node] = 0
    print(peers)
    return jsonify({'status': 'Node registered', 'peers': peers}), 200


@app.route('/event', methods=['POST'])
def process_event():
    """
    Phase 1: Verarbeite ein eingehendes Event.
    1. Speichere das Event lokal.
    2. Suche den besten Vorgänger (Predecessor) des Events.
    3. Aktualisiere die lokale Footprint-Matrix.
    """
    global local_events, footprint_matrix

    # Eingehendes Event im JSON-Format
    event = request.json 
    timestamp = event['timestamp']#datetime.datetime.strptime(event['timestamp'], '%Y-%m-%d %H:%M:%S')
    activity = event['activity']
    caseid = event['caseid']
    node = event['node']

    #TODO: caseid: [list]
    # Schritt 1: Speichere das Event lokal
    # Überprüfen, ob die CaseID bereits existiert, wenn nicht, initialisieren
    if caseid not in local_events:
        local_events[caseid] = [] 

    local_events[caseid].append({
        'timestamp': timestamp,
        'activity': activity,
        'caseid': caseid,
        'node': node,
        'predecessor': "",  # Vorgänger wird später gesucht
        'successor': ""
    })
    """
    print("localEvent Liste::::::::::::")
    print(local_events)
    print("timestemp:::::::::::::::::")
    print(timestamp)
    """

    update_podlist()
    
    # Schritt 2: Suche den besten Vorgänger (Predecessor)
    predecessor = find_predecessor(caseid, timestamp, node)
    print(predecessor)
    

    # Schritt 3: Aktualisiere die Footprint-Matrix basierend auf Vorgänger und aktuellem Event
    if predecessor:
        print("TEST TEST TEST")
        print(predecessor['node'])
        update_footprint_matrix(timestamp, caseid, predecessor)

    return jsonify({'status': 'Event processed', 'predecessor': predecessor}), 200



def find_predecessor(caseid, timestamp, node):
    best_predecessor = None
    best_ip = ""

    for peer in pod_ips:
        try:
            print(f"Frage {peer} nach Vorgänger für CaseID {caseid}")

            response = requests.post(f'{peer}/predecessor', json={
                'caseid': caseid,
                'timestamp': timestamp,
                'successor': node #ich selber
            })

            if response.status_code == 200:
                potential_predecessor = response.json().get('predecessor')

                if potential_predecessor:
                    pred_timestamp = potential_predecessor['timestamp'] #datetime.datetime.strptime(potential_predecessor['timestamp'], '%Y-%m-%d %H:%M:%S')

                    # Falls es einen besseren Vorgänger gibt, wird der alte verworfen
                    if (best_predecessor is None or 
                        (pred_timestamp > best_predecessor['timestamp'] and pred_timestamp < timestamp)):
                        best_predecessor = potential_predecessor
                        best_ip = peer

        except Exception as e:
            print(f"Fehler beim Kommunizieren mit {peer}: {e}")

    # **Schritt 2**: Nur dem besten Vorgänger sagen, dass er den `successor` speichern soll
    if best_predecessor:
        try:
            print("Best predecessor: " + best_predecessor)
            requests.post(f'{best_ip}/set_successor', json={
                'caseid': caseid,
                'timestamp': best_predecessor['timestamp'],
                'successor': node
            })
        except Exception as e:
            print(f"Konnte {best_predecessor['node']} nicht benachrichtigen: {e}")

    return best_predecessor

@app.route('/set_successor', methods=['POST'])
def set_successor():
    """
    Setzt den `successor` nur für den besten Vorgänger.
    """
    data = request.json
    print("jo Empfangenes JSON:", data)  # Debug-Ausgabe
    caseid = data['caseid']
    timestamp = data['timestamp']
    successor_node = data['successor'] #data['node']  # Der Nachfolger-Knoten wird hier übermittelt

    # Prüfe, ob das Event in der lokalen Liste existiert
    if caseid not in local_events:
        return jsonify({'status': 'CaseID not found'}), 404

    # Suche nach dem Event, das dem Timestamp entspricht
    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa")
    event_found = False
    for event in local_events[caseid]:
        if event['timestamp'] == timestamp:
            # Das passende Event gefunden, setze den Nachfolger auf den Knoten
            event['successor'] = successor_node  # Hier setzen wir den Nachfolger-Knoten
            event_found = True
            break

    if event_found:
        # Optional: Die Footprint-Matrix nach der Aktualisierung der Events auch hier anpassen.
        #update_footprint_matrix(timestamp, caseid, {"node": successor_node})  # update mit dem neuen Nachfolger
        return jsonify({'status': 'Successor set', 'caseid': caseid, 'timestamp': timestamp}), 200
    else:
        return jsonify({'status': 'Event not found for this timestamp'}), 404


@app.route('/predecessor', methods=['POST'])
def get_predecessor():
    """
    Antwortet auf die Vorgänger-Anfrage eines anderen Nodes.
    Prüft lokale Events und sucht nach einem Vorgänger-Event mit:
    - Gleicher CaseID
    - Kleinerem Zeitstempel
    - Keinem bereits gesetzten Nachfolger
    """
    print("JA ich suche neich einem Vorgägnger")
    data = request.json
    caseid = data['caseid']
    timestamp = data['timestamp'] #datetime.datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
    successor = data['successor']
    print(data)
    print("--------------------------------------------------------------")
    print(caseid)

    # Prüfe, ob es Events für die CaseID gibt
    if caseid not in local_events:
        return jsonify({'predecessor': None}), 200

    # Suche nach dem besten Vorgänger (maximaler Zeitstempel < timestamp)
    best_predecessor = None
    for event in local_events[caseid]:
        if event['timestamp'] < timestamp and event['successor'] == "":
            if best_predecessor is None or event['timestamp'] > best_predecessor['timestamp']:
                best_predecessor = event

    # Falls ein Vorgänger gefunden wurde, setze den Nachfolger
    if best_predecessor:
        #best_predecessor['successor'] = successor
        print("Gefundener bester Vorgänger:", best_predecessor)
        return jsonify({'predecessor': best_predecessor}), 200
    
    return jsonify({'predecessor': None}), 200 


def finde_element( timestamp, caseid):
    """
    Findet ein Element in einer Liste von Dictionaries basierend auf 'timestamp' und 'caseid'.
    :return: Das passende Element als Dictionary oder None, falls nicht gefunden.
    """
    if caseid in local_events:
        for element in local_events[caseid]:
            if element['timestamp'] == timestamp:
                return element
    return None

def update_footprint_matrix(timestamp, caseid, predecessor):
    """
    Aktualisiert die lokale Footprint-Matrix basierend auf Vorgänger- und Nachfolger-Aktivitäten.
    """
    print("update--------------------------")
    element = finde_element(timestamp,caseid)
    global footprint_matrix

    node_old = element['predecessor']
    node = predecessor['node']
    element['predecessor'] = node

    if node_old != "":
        footprint_matrix[node_old] -= 1
    key = node
    
    if key in footprint_matrix:
        footprint_matrix[key] += 1
    else:
        footprint_matrix[key] = 1


@app.route('/footprint_matrix', methods=['GET'])
def get_footprint_matrix():
    """
    Phase 2: Sende die lokale Footprint-Matrix als Antwort auf eine Anfrage.
    """
    print(footprint_matrix)
    print(local_events)
    print(pod_ips)
    return jsonify(footprint_matrix), 200


if __name__ == '__main__':
    # Dynamischer Port aus Umgebungsvariablen (default: 5000)
    port = int(os.environ.get('FLASK_PORT', 5000))
    # Dynamischer Name der Node
    name = str(os.environ.get('NAME', ""))
    footprint_matrix[name] = 0
    print(f"Starting node {name} on port {port}")

    
    # Starte die Flask-App
    app.run(host='0.0.0.0', port=port)
'''

if __name__ == '__main__':
        # Flask Port
    port = int(os.environ.get('FLASK_PORT', 5000))  # Standard: 5000
    # Node Name
    name = os.environ.get('NAME', "")  # Setzt den Namen des Pods
    # Peer Discovery URL
    peer_discovery_url = os.environ.get('PEER_DISCOVERY_URL', "")

    # Beispiel zur Überprüfung
    
    print(f"Peer discovery service: {peer_discovery_url}")
    

    peer_service = os.environ.get('PEER_DISCOVERY_URL', "flask-service")
    peers = []

    try:
        # Hole die IP-Adressen der anderen Pods
        peer_ips = socket.getaddrinfo(peer_service, port)
        for ip in peer_ips:
            address = f"http://{ip[4][0]}:5000"
            if address not in peers and name not in address:  # Eigenen Pod ausschließen
                peers.append(address)

        # Registriere bei allen Peers
        for peer in peers:
            try:
                requests.post(f'{peer}/register', json={'node_address': f'http://{name}:5000', 'node': name})
            except Exception as e:
                print(f"Error registering with peer {peer}: {e}")

    except Exception as e:
        print(f"Error discovering peers: {e}")

    # Starte Flask-App
    app.run(host='0.0.0.0', port=port)
'''
