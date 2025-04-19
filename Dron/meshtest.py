import json

import requests
import routeros_api


def post_mesh(data):
    resp = requests.post(f'http://{gs_ip}:{gs_port}/api/mesh', json = {'id': "meshtest", 'mesh_data': json.dumps(data)})
    print(resp.text)


gs_ip = "127.0.0.1"
# gs_ip = "192.168.0.80"
gs_port = 5000


# Dane logowania do MikroTik
host = "192.168.0.254"  # Adres IP MikroTika
username = "admin"
password = ""

# Połączenie z MikroTik API
connection = routeros_api.RouterOsApiPool(host, username=username, password=password, plaintext_login=False, use_ssl=False, ssl_verify=False)
api = connection.get_api()

# Pobieranie tabeli rejestracji klientów mesh
wireless_table = api.get_resource('/interface/wireless/registration-table')
clients = wireless_table.get()

print("-" * 40)
print('Mesh data:')
# Wyświetlenie danych
for client in clients:
    if client['wds'] != 'true':
        continue
    print(f"MAC: {client['mac-address']}")
    print(f"IP: {client.get('last-ip', 'Brak')}")
    print(f"Signal Strength: {client['signal-strength']} dBm")
    print(f"CCQ: {client['tx-ccq']} %")
    print(f"Rx Rate: {client['rx-rate']} Mbps, Tx Rate: {client['tx-rate']} Mbps")
    print("-" * 40)

post_mesh(clients)

