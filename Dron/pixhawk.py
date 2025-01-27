from pymavlink import mavutil
import time
import requests

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
        print(f"GPS: lat={lat/1e7} lon={lon/1e7} alt={alt/1000}m")

    time.sleep(1)
