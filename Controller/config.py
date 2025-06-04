gs_ip = "127.0.0.1"
gs_port = 5000

import requests

# Dane logowania do MikroTik
username = "admin"
password = ""

hosts = {
    "dron1": {"mac": "CC:2D:E0:1C:CC:C3", "ip": "192.168.0.1"},# Dron 1 - Master (adres mac do zmiany)
    "dron2": {"mac": "CC:2D:E0:1C:CC:C8", "ip": "192.168.0.55"},# Dron 2 (adres mac do zmiany)
    "dron3": {"mac": "CC:2D:E0:27:80:91", "ip": "192.168.0.53"},# Dron 3 (adres mac do zmiany)
}

drones = [
    {"id": "dron3", "role": "master"},
    # id do zmiany !!! (dron 1 przyjmuje stala pozycje, nie jest kontrolowany przez algorytm)
    {"id": "dron1", "role": "relay", "target": "dron2", "target_lider": "dron3"},  # id do zmiany !!!
    {"id": "dron2", "role": "lider", "target": "dron1"}  # id do zmiany !!!
]

def get_current_position(machine_id):
    try:
        resp=requests.get(f'http://{gs_ip}:{gs_port}/api/gps/latest/{machine_id}', timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {'lat': data['lat'], 'lon': data['lon']}
    except Exception as e:
        print(f"Bład pobierania pozycji drona: {machine_id}",e)
        return None

mock = False