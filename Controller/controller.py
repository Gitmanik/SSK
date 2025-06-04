import time
import requests
from pathfinder import algorithm_A_step
from rssi_provider import get_rssi, update_rssi_map
from shapely.geometry import shape
from geopy.distance import distance
import threading
from collections import deque

import config

MIN_RSSI = -70
PREF_RSSI = -60
BUFFER_RADIUS = 0.00001 # ~1m

def rssi_updater():
    while True:
        update_rssi_map()
        time.sleep(6)

def get_polygons():
    try:
        resp = requests.get(f'http://{config.gs_ip}:{config.gs_port}/get-polygons', timeout=5)
        if resp.status_code == 200:
            polygons_geojson = resp.json()
            polygons = [shape(p['geometry']).buffer(BUFFER_RADIUS) for p in polygons_geojson]
            
            return polygons
        return []
    except Exception as e:
        print("Błąd pobierania polygonów:", e)
        return []



def get_goal_position():
    try:
        resp = requests.get(f'http://{config.gs_ip}:{config.gs_port}/get-goal', timeout=5)
        if resp.status_code == 404:
            print("Brak zapisanego celu")
            return None
        resp.raise_for_status()
        data = resp.json()
        lat = data.get('latitude')
        lon = data.get('longitude')
        if lat is not None and lon is not None:
            return {'lat': lat, 'lon': lon, 'id': data.get('id')}
        else:
            print("Niepoprawny format danych celu")
            return None
    except Exception as e:
        print("Błąd pobierania pozycji docelowej:", e)
        return None


def droneAtGoal(pos, goal):
    return distance(pos, goal).meters < 4

def post_next_position(lat, lon, machine_id):
    requests.post(f'http://{config.gs_ip}:{config.gs_port}/post-next_position', json = {'type': 'gps', 'id': machine_id, 'lat': lat, 'lon': lon})

def lider_drone_controller(machine_id, target):
    global posin
    last_positions = deque(maxlen=4)
    while True:
        pos_data = config.get_current_position(machine_id)
        target_pos_data = config.get_current_position(target)

        if not pos_data:
            print("Brak danych o pozycji drona - lider")
            time.sleep(2)
            continue
        if not target_pos_data:
            print("Brak danych o pozycji targeta dla lidera")
            time.sleep(2)
            continue
        pos = (pos_data['lat'], pos_data['lon'])
        target_pos  = (target_pos_data['lat'], target_pos_data['lon'])
        goal = get_goal_position()
        if goal is None:
            print("Brak ustawionego celu")
            time.sleep(2)
            continue
        goal_pos=(goal['lat'], goal['lon'])
        if droneAtGoal(pos, goal_pos):
            lat, lon = goal_pos
            post_next_position(lat, lon, machine_id)
            print(f"Lider [{machine_id}] dotarl do celu")
            time.sleep(5)
            continue
        else: 
            last_positions.append(pos)
        rssi=get_rssi(machine_id,target)
        if rssi < MIN_RSSI:
            print(f"Lider [{machine_id}] - sygnal jest zbyt slaby do {target}: RSSI = {rssi}, lider czeka..")
            time.sleep(5)
            continue
        polygons_geom = get_polygons()
        forbidden = list(last_positions)
        path = algorithm_A_step(pos, goal, polygons_geom, target_pos, forbidden_positions=forbidden)
        if not path:
            print("Nie znaleziono sciezki")
        else:
            print("Wyznaczona sciezka: ")
            for p in path:
                print(p)
            next_point = path[1] if len(path)>1 else goal_pos
            print(f"Lider porusza się do punktu: {next_point}")
            lat, lon = next_point
            post_next_position(lat, lon, machine_id)
        time.sleep(2)

def relay_drone_controller(machine_id, target_master, target_lider):
     last_positions = deque(maxlen=4)
     while True:
        pos = config.get_current_position(machine_id)
        last_positions.append((pos['lat'], pos['lon']))
        master_pos = config.get_current_position(target_master)
        lider_pos = config.get_current_position(target_lider)
        if not pos or not master_pos or not lider_pos:
            time.sleep(2)
            continue
        rssi_master = get_rssi(machine_id, target_master)
        rssi_lider = get_rssi(machine_id, target_lider)
        if rssi_master < PREF_RSSI or rssi_lider < PREF_RSSI:
            print(f"Dron [{machine_id}] ma slaby sygnal do {target_master} lub {target_lider}, RSSI = {rssi_master}, {rssi_lider} - proba poprawy lacznosci")
            intermediate_goal = {
                'lat': (master_pos['lat'] + lider_pos['lat']) / 2,
                'lon': (master_pos['lon'] + lider_pos['lon']) / 2
            }
            polygons = get_polygons()
            forbidden = list(last_positions)
            path = algorithm_A_step((pos['lat'], pos['lon']), (intermediate_goal['lat'], intermediate_goal['lon']), polygons, (lider_pos['lat'], lider_pos['lon']), forbidden_positions=forbidden)
            if not path:
                print("Relay: nie znaleziono ścieżki")
                time.sleep(2)
                continue
            next_point = path[1] if len(path) > 1 else (intermediate_goal['lat'], intermediate_goal['lon'])
            if next_point in last_positions:
                print(f"Relay: next_point {next_point} jest w ostatnich pozycjach, szukam alternatywy...")
                time.sleep(2)
                continue
            last_positions.append(next_point)

            post_next_position(next_point[0], next_point[1], machine_id)
            print(f"Relay [{machine_id}] przesuwa się do {next_point}")
        else:
            print(f"Dron [{machine_id}] do {target_master}, {target_lider}: RSSI OK - {rssi_master}, {rssi_lider}")

        time.sleep(2)

def start_all_drones(drones):
    threads  = []
    for drone in drones:
        if drone['role'] == 'lider':
            t = threading.Thread(target=lider_drone_controller, args=(drone['id'], drone['target']))
        elif drone['role'] == 'relay':
            t = threading.Thread(target=relay_drone_controller, args=(drone['id'], drone['target'], drone['target_lider']))
        else:
            continue
        t.start()
        threads.append(t)
    return threads

if __name__ == "__main__":
    rssi_thread = threading.Thread(target=rssi_updater, daemon=True)
    rssi_thread.start()

    threads = start_all_drones(config.drones)
    for t in threads:
        t.join()