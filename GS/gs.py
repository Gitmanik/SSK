import json
from flask import Flask, request, jsonify, render_template, abort
import sqlite3
import os
from collections import defaultdict

app = Flask(__name__)

db_file = "gps_data.db"

# Initialize the SQLite database
def init_db():
    print(f"Database file: {db_file}")
    if not os.path.exists(db_file):
        print("Creating database...")
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE gps_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE mesh_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE polygons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    geojson TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE data_next_position (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

init_db()
@app.route("/api/gps", methods=["POST"])
def receive_gps_data():
    data = request.get_json()
    if not data or "lat" not in data or "lat" not in data or "id" not in data:
        return jsonify({"error": "Invalid data"}), 400

    id = data["id"]
    latitude = data["lat"]
    longitude = data["lon"]

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gps_data (machine_id, latitude, longitude) VALUES (?, ?, ?)", (id, latitude, longitude))
    conn.commit()
    conn.close()

    return jsonify({"message": "Data saved successfully"}), 201

@app.route("/api/gps/latest/<machine_id>", methods=["GET"])
def get_latest_gps(machine_id):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT latitude, longitude FROM gps_data WHERE machine_id = ? ORDER BY timestamp DESC LIMIT 1", (machine_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        lat, lon = row
        return jsonify({'id':machine_id, 'lat':lat, 'lon':lon}), 200
    else:
        return jsonify({'error': 'No GPS data found for this drone'}), 404

@app.route("/api/mesh", methods=["POST"])
def receive_mesh_data():
    data = request.get_json()
    if not data or "id" not in data or "mesh_data" not in data:
        return jsonify({"error": "Invalid data"}), 400

    id = data["id"]
    data = data["mesh_data"]

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mesh_data (machine_id, data) VALUES (?, ?)", (id, data))
    conn.commit()
    conn.close()

    return jsonify({"message": "Data saved successfully"}), 201

@app.route("/")
def display_map():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT machine_id, latitude, longitude FROM gps_data GROUP BY machine_id ORDER BY timestamp DESC")
    data = cursor.fetchall()
    conn.close()

    markers = [
        {"machine_id": row[0], "latitude": row[1], "longitude": row[2]} for row in data
    ]

    return render_template("map.html", markers=markers)

@app.route('/meshdata')
def index():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mesh_data ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    # Group data by machine_id
    grouped_data = defaultdict(lambda: defaultdict(list))  # Nested defaultdict
    for row in rows:
        data = json.loads(row[2])  # Assuming 'data' is the 3rd column in your table
        machine_id = row[1]  # Assuming 'machine_id' is the 2nd column in your table
        timestamp = row[3]  # Assuming 'timestamp' is the 4th column in your table
        grouped_data[machine_id][timestamp].extend(data)  # Group by machine_id and timestamp

    conn.close()

    return render_template('meshdata.html', grouped_data=grouped_data)


# Using OsmAnd map format https://osmand.net/docs/technical/osmand-file-formats/osmand-sqlite/
@app.route("/tiles/<int:zoom>/<int:row>/<int:column>.png")
def query_tile(zoom, column, row):
    zoom = 17 - zoom
    query = 'SELECT image FROM tiles '\
            'WHERE z = ? AND y = ? AND x = ?;'
    g = sqlite3.connect("Trojmiasto.sqlitedb")
    cur = g.execute(query, (zoom, column, row))
    results = cur.fetchall()
    if not results:
        print(f"No tile for {zoom}/{column}/{row} found")
        abort(404)
    the_image = results[0][0]
    return app.response_class(
        the_image,
        mimetype='image/png'
    )

@app.route('/get-polygons', methods=['GET'])
def get_polygons():
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, geojson FROM polygons")
        rows = cursor.fetchall()

        polygons = []
        for row in rows:
            geojson = json.loads(row[1])  # Parse the GeoJSON from the database
            geojson['properties'] = geojson.get('properties', {})  # Ensure properties exist
            geojson['properties']['id'] = row[0]  # Add the polygon's unique ID to properties
            polygons.append(geojson)

        return jsonify(polygons), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/save-polygon', methods=['POST'])
def save_polygon():
    data = request.get_json()

    # Example of extracting GeoJSON data
    geojson = json.dumps(data)  # You can validate or parse this further

    # Save to database (assume we have table 'polygons' with 'id' and 'geojson')
    conn = sqlite3.connect(db_file)  # Replace with your actual database connection
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO polygons (geojson) VALUES (?)", (geojson,))
        conn.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/delete-polygon', methods=['POST'])
def delete_polygon():
    data = request.get_json()

    # Read the polygon's ID from the properties
    polygon_id = data['properties']['id']

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM polygons WHERE id = ?", (polygon_id,))
        conn.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/update-polygon', methods=['POST'])
def update_polygon():
    data = request.get_json()

    # Read the polygon's ID from the properties
    polygon_id = data['properties']['id']

    # Serialize the updated GeoJSON
    geojson = json.dumps(data)

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("UPDATE polygons SET geojson = ? WHERE id = ?", (geojson, polygon_id))
        conn.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/get-goal', methods=['GET'])
def get_goal():
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, latitude, longitude FROM goals ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'No goal found'}), 404
        goal_id, lat, lon = row
        return jsonify({'id': goal_id, 'latitude': lat, 'longitude': lon}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/update-goal', methods=['POST'])
def update_goal():
    try:
        data = request.get_json()
        lat = data.get('lat')
        lon = data.get('lon')

        if lat is None or lon is None:
            return jsonify({"error": "Missing coordinates"}), 400
        lat = float(lat)
        lon = float(lon)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO goals (latitude, longitude) VALUES (?, ?)", (lat, lon))
        conn.commit()

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/delete-goal', methods=['POST'])
def delete_goal():
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals")
        conn.commit()
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/get-next_position', methods=['GET'])
def get_next_position():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT machine_id, latitude, longitude
        FROM data_next_position
        WHERE id IN (
            SELECT MAX(id)
            FROM data_next_position
            GROUP BY machine_id
        )
    """)
    rows = cursor.fetchall()
    conn.close()

    positions = []
    for row in rows:
        positions.append({'id': row[0], 'lat': row[1], 'lon': row[2]})

    if positions:
        return jsonify(positions)
    else:
        return jsonify({'error': 'No next positions found'}), 404

@app.route("/post-next_position", methods=["POST"])
def post_next_position():
    data = request.get_json()
    if not data or "lat" not in data or "lat" not in data or "id" not in data:
        return jsonify({"error": "Invalid data"}), 400

    id = data["id"]
    latitude = data["lat"]
    longitude = data["lon"]

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO data_next_position (machine_id, latitude, longitude) VALUES (?, ?, ?)", (id, latitude, longitude))
    conn.commit()
    conn.close()

    return jsonify({"message": "Data saved successfully"}), 201

if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host='0.0.0.0')

