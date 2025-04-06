import routeros_api

# Dane logowania do MikroTik
host = "192.168.0.1"  # Adres IP MikroTika
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

