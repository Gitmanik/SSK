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
        cursor.execute("SELECT geojson FROM polygons")
        rows = cursor.fetchall()
        polygons = [{'geojson': row[0]} for row in rows]
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


if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host='0.0.0.0')

