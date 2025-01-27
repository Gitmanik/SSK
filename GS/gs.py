from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)

db_file = "gps_data.db"

# Initialize the SQLite database
def init_db():
    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
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
        conn.commit()
        conn.close()

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

if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host='0.0.0.0')

