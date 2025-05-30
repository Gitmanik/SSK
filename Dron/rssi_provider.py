import routeros_api

import math
import threading

hosts = {
    "dron1": {"mac": "00:11:22:33:44:55", "ip": "192.168.0.254"},# Dron 1 - Master (adres mac do zmiany)
    "dron2": {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.0.253"},# Dron 2 (adres mac do zmiany)
    "dron3": {"mac": "11:22:33:44:55:66", "ip": "192.168.0.252"},# Dron 3 (adres mac do zmiany)
}

username = "admin"
password = ""
rssi_map={}
rssi_lock = threading.Lock()

name_to_mac = {name: conf['mac'] for name, conf in hosts.items()}

def predict_rssi(pos1, pos2, tx_power=-30, n=2.5):
    from pathfinder import heuristic
    if isinstance(pos1, dict):
        pos1 = (float(pos1['lat']), float(pos1['lon']))
    if isinstance(pos2, dict):
        pos2 = (float(pos2['lat']), float(pos2['lon']))
    d = heuristic(pos1, pos2)
    return tx_power - 10 * n * math.log10(d if d > 1 else 1)

def update_rssi_map():
    global rssi_map
    with rssi_lock:
        rssi_map.clear()
        for name, conf in hosts.items():
            ip=conf["ip"]
            mac_master = conf["mac"]
            try:
                connection=routeros_api.RouterOsApiPool(
                    ip, username=username, password=password, plaintext_login=False, use_ssl=False, ssl_verify=False
                )
                api=connection.get_api()
                wireless_table=api.get_resource('/interface/wireless/registration-table')
                clients=wireless_table.get()
                for client in clients:
                    if client.get('wds') != 'true':
                        continue
                    mac_client = client.get('mac-address')
                    rssi= int(client.get('signal-strength', -90))
                    rssi_map[(mac_master, mac_client)]=rssi
                    print(f"{mac_master} -> {mac_client} : {rssi} dBm")
                connection.disconnect()
            except Exception as e:
                print(f"Blad polaczenia z {ip}: {e}")


# --------------wersja bazujaca na danych z MikroTika:--------------------
# def get_rssi(drone1, drone2):
#     with rssi_lock:
#         mac1=name_to_mac.get(drone1)
#         mac2=name_to_mac.get(drone2)
#         if mac1 and mac2:
#             return(
#                 rssi_map.get((mac1,mac2)) or
#                 rssi_map.get((mac2,mac1)) or 
#                 -90 #  gdy brak danych
#             )
#         return -90 # gdy brak zasiegu
#  ^^^^^^^^^^^--wersja bazujaca na danych z MikroTika:---^^^^^^^^^^^^^^^^^^


# wersja symulacyjna - dane mockowe - wszystko co ponizej---------------
import requests
def get_rssi(Drone1, Drone2):
    from geopy.distance import distance
    drone1 = get_current_position(Drone1)
    drone2 = get_current_position(Drone2)
    pos1 = (drone1['lat'], drone1['lon'])
    pos2 = (drone2['lat'], drone2['lon'])
    dist_m = distance(pos1, pos2).meters

    import random
    base_rssi = -30
    rssi = base_rssi - 20 * math.log10(dist_m + 1)
    rssi += random.gauss(0, 2)

    rssi = max(min(rssi, -30), -90)
    return rssi
gs_ip="127.0.0.1"
gs_port=5000
def get_current_position(machine_id):
    try:
        resp=requests.get(f'http://{gs_ip}:{gs_port}/api/gps/latest/{machine_id}', timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {'lat': data['lat'], 'lon': data['lon']}
    except Exception as e:
        print(f"Bład pobierania pozycji drona: {machine_id}",e)
        return None
    
    # wersja symulacyjna - dane mockowe - -------^^^^^^^^^^^^^^^^^^