import routeros_api

import math
import threading

import config

rssi_map={}
rssi_lock = threading.Lock()

name_to_mac = {name: conf['mac'] for name, conf in config.hosts.items()}

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
        for name, conf in config.hosts.items():
            ip=conf["ip"]
            mac_master = conf["mac"]
            try:
                connection=routeros_api.RouterOsApiPool(
                    ip, username=config.username, password=config.password, plaintext_login=False, use_ssl=False, ssl_verify=False
                )
                api=connection.get_api()
                wireless_table=api.get_resource('/interface/wireless/registration-table')
                clients=wireless_table.get()
                for client in clients:
                    if client.get('wds') != 'true':
                        continue
                    mac_client = client.get('mac-address')
                    rssi= int(client.get('signal-strength', -90).split('@')[0])
                    rssi_map[(mac_master, mac_client)]=rssi
                    print(f"{mac_master} -> {mac_client} : {rssi} dBm")
                connection.disconnect()
            except Exception as e:
                print(f"Blad polaczenia z {ip}: {e}")


import requests
def get_rssi(Drone1, Drone2):
    if config.mock:
        from geopy.distance import distance
        drone1 = config.get_current_position(Drone1)
        drone2 = config.get_current_position(Drone2)
        pos1 = (drone1['lat'], drone1['lon'])
        pos2 = (drone2['lat'], drone2['lon'])
        dist_m = distance(pos1, pos2).meters

        import random
        base_rssi = -30
        rssi = base_rssi - 20 * math.log10(dist_m + 1)
        rssi += random.gauss(0, 2)

        rssi = max(min(rssi, -30), -90)
        return rssi
    else:
        with rssi_lock:
            mac1=name_to_mac.get(Drone1)
            mac2=name_to_mac.get(Drone2)
            if mac1 and mac2:
                return(
                    rssi_map.get((mac1,mac2)) or
                    rssi_map.get((mac2,mac1)) or
                    -90 #  gdy brak danych
                )
            return -90 # gdy brak zasiegu


