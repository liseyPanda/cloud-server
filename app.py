from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests
import psycopg2
from datetime import datetime

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS

# Elasticsearch
ELASTICSEARCH_URL = "http://elasticsearch-route-kompose-ndrc.apps.osc-trailer.trailer.ndrc.mil"
KIBANA_URL = 'https://kibana-kompose-ndrc.apps.osc-trailer.trailer.ndrc.mil/app/dashboards#/view/f4c19b48-01c6-4fa2-bcac-64a87da4c652?_g=(refreshInterval:(pause:!t,value:60000),time:(from:now%2Fd,to:now%2Fd))&_a=()'

# Sync variable
last_sync = None

# Cloud Database Connection
def db_connection():
    return psycopg2.connect(
        dbname="cloud_db",
        user="cloud_user",
        password="cloud_pass",
        host="cloud-db",
        port=5432
    )

@app.route("/")
def home():
    return "✅ Cloud Server is active & handling updates. Go to /dashboard to view."

# ✅ Updating Data to Cloud DB
@app.route('/update', methods=['POST'])
def update_data():
    data = request.json
    global last_sync
    index = "trucks"
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    response = requests.post(f"{ELASTICSEARCH_URL}/{index}/_doc", json=data)
    last_sync = data["last_updated"]
    conn = None
    
    try:
        print(f"📥 Receiving data {data}")
        conn = db_connection()
        cur = conn.cursor()
        print("✅ Connected to Cloud Database")
        
        cur.execute("""
                    INSERT INTO trucks (truck_id, status, location, event, last_updated)
                    VALUES (%s, %s, %s, %s, %s)
        """, (data.get("truck_id"), data.get("status"), data.get("location"), data.get("event"), data.get("last_updated")))

        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Truck data saved to Cloud DB: {data['truck_id']} at {data['last_updated']}")
        return jsonify(response.json())

    except Exception as e:
        print(f"Database insert error: {e}")
        return jsonify({"error": str(e)}), 500

# ✅ Retrieving Truck Events from Cloud DB
@app.route("/truck-events", methods=["GET"])
def get_truck_events():
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT truck_id, status, location, event, last_updated FROM trucks ORDER BY last_updated DESC LIMIT 10;")
        truck_events = [
            {"truck_id": row[0], "status": row[1], "location": row[2], "event": row[3], "last_updated": row[4]}
            for row in cur.fetchall()
        ]
        cur.close()
        conn.close()
        
        return jsonify(truck_events)

    except Exception as e:
        print(f"Database query error: {e}")
        return jsonify({"error": str(e)}), 500

# ✅ Show Cloud Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', kibana_url=KIBANA_URL)
    
# ♻️ Show last sync of data
@app.route('/last_sync')
def get_last_sync():
    return jsonify({"last_sync": last_sync})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
