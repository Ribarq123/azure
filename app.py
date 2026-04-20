from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", "5432"),
    "sslmode": "require",
}

API_KEY = os.getenv("API_KEY")


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/metrics", methods=["POST"])
def create_metric():
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required = ["source", "hostname", "metric_name", "metric_value", "status"]
    missing = [field for field in required if field not in data]

    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO metrics (source, hostname, metric_name, metric_value, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at;
            """,
            (
                data["source"],
                data["hostname"],
                data["metric_name"],
                data["metric_value"],
                data["status"]
            )
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Metric stored successfully",
            "id": row[0],
            "created_at": str(row[1])
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/metrics", methods=["GET"])
def get_metrics():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, source, hostname, metric_name, metric_value, status, created_at
            FROM metrics
            ORDER BY id DESC;
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "source": row[1],
                "hostname": row[2],
                "metric_name": row[3],
                "metric_value": float(row[4]),
                "status": row[5],
                "created_at": str(row[6])
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500