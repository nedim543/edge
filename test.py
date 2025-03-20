import requests
import time

def send_event(ip, timestamp, caseid, node):
    url = f"http://{ip}/event"
    data = {
        "timestamp": timestamp,
        "activity": "Start Production",
        "caseid": f"case_{caseid}",
        "node": node
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"✅ Erfolgreich gesendet an {node} ({ip}) | CaseID: case_{caseid}")
        else:
            print(f"❌ Fehler {response.status_code} beim Senden an {node}: {response.text}")
    except Exception as e:
        print(f"⚠ Fehler beim Senden an {node}: {e}")

def get_footprint_matrix(ip, node):
    url = f"http://{ip}/footprint_matrix"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            matrix = response.json()
            print(f"\n📊 Footprint-Matrix von Node {node} ({ip}):")
            print(matrix)
        else:
            print(f"❌ Fehler {response.status_code} beim Abrufen der Footprint-Matrix von {node}: {response.text}")
    except Exception as e:
        print(f"⚠ Fehler beim Abrufen der Footprint-Matrix von {node}: {e}")

def main():
    ip1 = "192.168.49.2:30010" #input("Gib die erste IP ein (z. B. 10.244.3.222:5000): ").strip()
    ip2 = "192.168.49.2:30011" #input("Gib die zweite IP ein (z. B. 10.244.3.213:5000): ").strip()
    ip3 = "192.168.49.2:30012" #input("Gib die dritte IP ein (z. B. 10.244.3.250:5000): ").strip()
    
    num_messages = int(input("Wie viele Nachrichten sollen gesendet werden? "))

    if num_messages < 1:
        print("⚠ Anzahl der Nachrichten muss mindestens 1 sein!")
        return

    caseid = 1
    base_timestamp = time.time()

    nodes = [(ip1, "a"), (ip2, "b"), (ip3, "c")]

    for i in range(num_messages):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(base_timestamp + i * 60))
        ip, node = nodes[i % len(nodes)]  # Sicherstellen, dass nur existierende Nodes genutzt werden

        send_event(ip, timestamp, caseid, node)

        if (i + 1) % len(nodes) == 0:  # Case-ID nach vollständiger Runde erhöhen
            caseid += 1

        time.sleep(2)

    # Footprint-Matrix abrufen
    print("\n🔄 Warten, damit die Nodes ihre Footprint-Matrix aktualisieren können...")
    time.sleep(2)

    for ip, node in nodes[:num_messages]:  # Nur genutzte Nodes abfragen
        get_footprint_matrix(ip, node)

if __name__ == "__main__":
    main()
