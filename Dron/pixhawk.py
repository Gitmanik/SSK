from pymavlink import mavutil
import time
import requests
import routeros_api

# Dane logowania do MikroTik
host = "192.168.88.1"  # Adres IP MikroTika
username = "admin"
password = "haslo"

# Połączenie z MikroTik API
connection = routeros_api.RouterOsApiPool(host, username=username, password=password, port=8728, plaintext_login=True)
api = connection.get_api()

master = mavutil.mavlink_connection('/dev/ttyACM0', baud=115200)
print("Connected")

master.wait_heartbeat()
print("Heartbeat from system (system %u component %u)" % (master.target_system, master.target_system))

master.mav.request_data_stream_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_DATA_STREAM_ALL,
    1,  # Rate in Hz
    1   # Start streaming
)

with open('/etc/machine-id', 'r') as f:
    machine_id = f.read()

print(f"machine_id: {machine_id}")

def post_gps(lat, lon):
    requests.post('http://192.168.0.80:5000/api/gps', json = {'type': 'gps', 'id': machine_id, 'lat': msg.lat/1e7, 'lon': msg.lon/1e7})

def post_mesh(data):
    requests.post('http://192.168.0.80:5000/api/mesh', json = {'mesh': data})

while True:
    msg = master.recv_match(blocking=True)
    if not msg:
        continue

    msg_type = msg.get_type()

    if msg_type == "GPS_RAW_INT":
        # ArduPilot / PX4 generally use this for raw GPS data
        lat = msg.lat  # latitude in 1e-7 degrees
        lon = msg.lon  # longitude in 1e-7 degrees
        alt = msg.alt  # altitude in millimeters (above MSL in many firmwares)
        post_gps(msg.lat, msg.lon)
        print("-" * 40)
        print(f"GPS: lat={lat/1e7} lon={lon/1e7} alt={alt/1000}m")

    # Pobieranie tabeli rejestracji klientów mesh
    wireless_table = api.get_resource('/interface/wireless/registration-table')
    clients = wireless_table.get()

    print("-" * 40)
    print('Mesh data:')
    # Wyświetlenie danych
    for client in clients:
        print(f"MAC: {client['mac-address']}")
        print(f"IP: {client.get('last-ip', 'Brak')}")
        print(f"Signal Strength: {client['signal-strength']} dBm")
        print(f"CCQ: {client['tx-ccq']} %")
        print(f"Rx Rate: {client['rx-rate']} Mbps, Tx Rate: {client['tx-rate']} Mbps")
        print("-" * 40)

    post_mesh(clients)

    # Zamknięcie połączenia
    connection.disconnect()


    time.sleep(1)
