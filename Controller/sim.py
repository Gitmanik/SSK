import requests
import time
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from shapely.geometry import shape
import matplotlib.patches as mpatches
import threading

gs_ip = "127.0.0.1"
gs_port = 5000
interval_s = 2

drones = [
    {"id": "dron1", "role": "master", "lat": 54.372158, "lon": 18.638540},
    {"id": "dron2", "role": "relay", "target": "dron1", "lat": 54.372167, "lon": 18.638540},
    {"id": "dron3", "role": "lider", "target": "dron2", "lat": 54.372176, "lon": 18.638540}
]

DRONE_URLS = [
    f"http://{gs_ip}:{gs_port}/api/gps/latest/dron1",
    f"http://{gs_ip}:{gs_port}/api/gps/latest/dron2",
    f"http://{gs_ip}:{gs_port}/api/gps/latest/dron3",
]

TARGET_URL = f"http://{gs_ip}:{gs_port}/get-goal"
POLYGONS_URL = f"http://{gs_ip}:{gs_port}/get-polygons"

def get_next_positions():
    try:
        resp = requests.get(f'http://{gs_ip}:{gs_port}/get-next_position', timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("Błąd pobierania następnych pozycji dronów:", e)
        return None

def post_pos(drone):
    try:
        resp = requests.post(
            f'http://{gs_ip}:{gs_port}/api/gps',
            json={'type': 'gps', 'id': drone['id'], 'lat': drone['lat'], 'lon': drone['lon']}
        )
        print(f"Opublikowano: {drone}")
    except Exception as e:
        print("Błąd wysyłania pozycji:", e)

def fetch_position(url):
    try:
        r = requests.get(url, timeout=1)
        r.raise_for_status()
        data = r.json()
        return data['lat'], data['lon']
    except Exception as e:
        print(f"Błąd pobierania {url}: {e}")
        return None, None

def fetch_goal_position(url):
    try:
        r = requests.get(url, timeout=1)
        r.raise_for_status()
        data = r.json()
        return data['latitude'], data['longitude']
    except Exception as e:
        print(f"Błąd pobierania celu {url}: {e}")
        return None, None

def fetch_polygons():
    try:
        r = requests.get(POLYGONS_URL, timeout=2)
        r.raise_for_status()
        data = r.json()
        return [shape(feature['geometry']) for feature in data]
    except Exception as e:
        print(f"Błąd pobierania przeszkód: {e}")
        return []

for drone in drones:
    post_pos(drone)

requests.post(f'http://{gs_ip}:{gs_port}/update-goal', json={"lat": 54.37223982343686, "lon": 18.639593124389652})

fig, ax = plt.subplots()

def update(frame):
    ax.clear()
    polygons = fetch_polygons()
    for poly in polygons:
        if poly.geom_type == 'Polygon':
            x, y = poly.exterior.xy
            ax.add_patch(mpatches.Polygon(xy=list(zip(x, y)), closed=True, color='gray', alpha=0.3))
    drones_positions = []
    for i, url in enumerate(DRONE_URLS, 1):
        lat, lon = fetch_position(url)
        if lat is not None and lon is not None:
            drones_positions.append((i, lat, lon))
            ax.plot(lon, lat, 'bo')
            ax.text(lon, lat, f"Dron {i}", color='blue', fontsize=9)
    target_lat, target_lon = fetch_goal_position(TARGET_URL)
    if target_lat is not None and target_lon is not None:
        ax.plot(target_lon, target_lat, 'r*', markersize=15)
        ax.text(target_lon, target_lat, "Cel", color='red', fontsize=12)
    if not drones_positions and (target_lat is None or target_lon is None):
        return
    lats = [lat for _, lat, _ in drones_positions]
    lons = [lon for _, _, lon in drones_positions]
    if target_lat is not None and target_lon is not None:
        lats.append(target_lat)
        lons.append(target_lon)
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    lat_margin = (lat_max - lat_min) * 0.1 if lat_max != lat_min else 0.0005
    lon_margin = (lon_max - lon_min) * 0.1 if lon_max != lon_min else 0.0005
    ax.set_xlim(lon_min - lon_margin, lon_max + lon_margin)
    ax.set_ylim(lat_min - lat_margin, lat_max + lat_margin)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Pozycje dronów, celu i przeszkody")
    ax.grid(True)

ani = FuncAnimation(fig, update, interval=1000)

def update_drones_loop():
    while True:
        next_positions = get_next_positions()
        if not next_positions:
            print("Brak zadanych pozycji.")
            time.sleep(interval_s)
            continue
        for drone in drones:
            target = next((pos for pos in next_positions if pos['id'] == drone['id']), None)
            if not target:
                print(f"Brak pozycji docelowej dla {drone['id']}")
                continue
            drone['lat'], drone['lon'] = target['lat'], target['lon']
            post_pos(drone)
        time.sleep(interval_s)

threading.Thread(target=update_drones_loop, daemon=True).start()

plt.show()
