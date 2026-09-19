"""
ECO DEFENDERS - SQLite Database Integration & Time-Series Storage
--------------------------------------------------------------
Manages database operations for storing IoT sensor readings, risk predictions,
active early warning alerts, and model version metadata.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "eco_defenders.db")


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Sensor Readings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        rainfall_mm REAL,
        water_level_m REAL,
        river_flow REAL,
        soil_moisture REAL,
        dam_water_level_m REAL,
        temperature REAL,
        humidity REAL,
        pressure REAL,
        wind_speed REAL,
        latitude REAL,
        longitude REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Predictions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        water_level_m REAL,
        rainfall_mm REAL,
        flood_probability REAL,
        risk_score INTEGER,
        risk_category TEXT,
        severity TEXT,
        estimated_time_to_threshold INTEGER,
        secondary_hazard TEXT,
        sensor_quality_status TEXT,
        model_version TEXT,
        warning_required INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Non-destructive migrations for existing SQLite databases
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN water_level_m REAL;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN rainfall_mm REAL;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN hazard_type TEXT DEFAULT 'FLOOD';")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN thermal_temp_c REAL;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN pm25_ugm3 REAL;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN confidence REAL;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN fire_probability REAL;")
    except Exception:
        pass
    
    # 3. Alerts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        hazard_type TEXT DEFAULT 'FLOOD',
        risk_category TEXT,
        risk_score INTEGER,
        message TEXT,
        timestamp TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE'
    );
    """)
    
    # 4. Model Versions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        version TEXT NOT NULL,
        accuracy REAL,
        f1_score REAL,
        deployed_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Create Time-Series Indexes for Fast Queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_node_ts ON sensor_readings(node_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_node_ts ON predictions(node_id, timestamp);")
    
    conn.commit()
    conn.close()


# Ensure database tables exist on module import
init_db()


def save_reading_and_prediction(payload: dict, response: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Save reading
    cursor.execute("""
    INSERT INTO sensor_readings (
        node_id, timestamp, rainfall_mm, water_level_m, river_flow,
        soil_moisture, dam_water_level_m, temperature, humidity,
        pressure, wind_speed, latitude, longitude
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload.get("node_id"), payload.get("timestamp"),
        payload.get("rainfall_mm"), payload.get("water_level_m"),
        payload.get("river_flow"), payload.get("soil_moisture"),
        payload.get("dam_water_level_m"), payload.get("temperature"),
        payload.get("humidity"), payload.get("pressure"),
        payload.get("wind_speed"), payload.get("latitude"),
        payload.get("longitude")
    ))
    
    # Save prediction
    pred = response.get("prediction", {})
    loc = response.get("location", {})
    qual = response.get("sensor_quality", {})
    mod = response.get("model", {})
    water_val = payload.get("water_level_m", 1.5)
    rain_val = payload.get("rainfall_mm", 0.0)
    
    cursor.execute("""
    INSERT INTO predictions (
        node_id, timestamp, latitude, longitude, water_level_m, rainfall_mm,
        flood_probability, risk_score, risk_category, severity, estimated_time_to_threshold,
        secondary_hazard, sensor_quality_status, model_version, warning_required, confidence
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        loc.get("node_id"), response.get("timestamp"),
        loc.get("latitude"), loc.get("longitude"),
        water_val, rain_val,
        pred.get("flood_probability"), pred.get("risk_score"),
        pred.get("risk_category"), pred.get("severity"),
        pred.get("estimated_time_to_threshold_minutes"),
        pred.get("secondary_hazard"), qual.get("status"),
        mod.get("version"), 1 if pred.get("warning_required") else 0,
        pred.get("confidence")
    ))
    
    # Save active alert if warning required
    if pred.get("warning_required"):
        cursor.execute("""
        INSERT INTO alerts (node_id, hazard_type, risk_category, risk_score, message, timestamp)
        VALUES (?, 'FLOOD', ?, ?, ?, ?)
        """, (
            loc.get("node_id"), pred.get("risk_category"), pred.get("risk_score"),
            f"FLOOD WARNING: Node {loc.get('node_id')} reached {pred.get('risk_category')} risk (Score {pred.get('risk_score')}/100)",
            response.get("timestamp")
        ))
        
    conn.commit()
    conn.close()


def save_fire_reading_and_prediction(payload: dict, response: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    thermal = payload.get("thermal_temp_c", 25.0)
    pm25 = payload.get("pm25_ugm3", 15.0)
    node_id = payload.get("node_id", "NODE_FIRE_01")
    ts = payload.get("timestamp") or response.get("timestamp")
    
    pred = response.get("prediction", {})
    loc = response.get("location", {})
    qual = response.get("sensor_quality", {})
    mod = response.get("model", {})
    
    # Save reading
    cursor.execute("""
    INSERT INTO sensor_readings (
        node_id, timestamp, temperature, humidity, wind_speed, latitude, longitude
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        node_id, ts, payload.get("ambient_temp_c", 30.0),
        payload.get("humidity_pct", 40.0), payload.get("wind_speed_ms", 5.0),
        loc.get("latitude", 18.25), loc.get("longitude", 78.65)
    ))
    
    # Save prediction
    cursor.execute("""
    INSERT INTO predictions (
        node_id, timestamp, latitude, longitude, hazard_type,
        thermal_temp_c, pm25_ugm3,
        flood_probability, risk_score, risk_category, severity,
        estimated_time_to_threshold, secondary_hazard, sensor_quality_status,
        model_version, warning_required, confidence, fire_probability
    ) VALUES (?, ?, ?, ?, 'FOREST_FIRE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        node_id, ts, loc.get("latitude", 18.25), loc.get("longitude", 78.65),
        thermal, pm25,
        pred.get("fire_probability", 0.0), pred.get("risk_score", 0),
        pred.get("risk_category", "LOW"), pred.get("severity", "MINIMAL"),
        pred.get("estimated_time_to_threshold_minutes"),
        pred.get("secondary_hazard"), qual.get("status", "OK"),
        mod.get("version", "1.0.0"), 1 if pred.get("warning_required") else 0,
        pred.get("confidence"), pred.get("fire_probability")
    ))
    
    if pred.get("warning_required"):
        cursor.execute("""
        INSERT INTO alerts (node_id, hazard_type, risk_category, risk_score, message, timestamp)
        VALUES (?, 'FOREST_FIRE', ?, ?, ?, ?)
        """, (
            node_id, pred.get("risk_category"), pred.get("risk_score"),
            f"WILDFIRE ALERT: Node {node_id} detected {pred.get('risk_category')} fire risk (Thermal: {thermal}C, PM2.5: {pm25} ug/m3)",
            ts
        ))
        
    conn.commit()
    conn.close()


def get_latest_node_statuses(live_only: bool = False, stale_after_seconds: int = 60):
    """Return the latest real status for every node without rewriting node IDs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p1.*,
           COALESCE(p1.water_level_m, r.water_level_m) as latest_water_level_m,
           COALESCE(p1.rainfall_mm, r.rainfall_mm) as latest_rainfall_mm,
           p1.thermal_temp_c as latest_thermal_temp_c,
           p1.pm25_ugm3 as latest_pm25_ugm3,
           r.river_flow, r.soil_moisture, r.temperature, r.humidity, r.pressure, r.wind_speed
    FROM predictions p1
    INNER JOIN (
        SELECT node_id, MAX(prediction_id) as max_id
        FROM predictions
        GROUP BY node_id
    ) p2 ON p1.node_id = p2.node_id AND p1.prediction_id = p2.max_id
    LEFT JOIN sensor_readings r
      ON r.node_id = p1.node_id AND r.timestamp = p1.timestamp
    ORDER BY p1.prediction_id DESC;
    """)
    rows = cursor.fetchall()
    conn.close()

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    results = []
    node_names = {
        "NODE_FLOOD_01": "River Basin Station",
        "NODE_FIRE_01": "Forest Catchment Station",
    }

    for row in rows:
        item = dict(row)
        received_at = item.get("created_at") or item.get("timestamp")
        age_seconds = None

        if received_at:
            try:
                parsed = datetime.fromisoformat(str(received_at).replace("Z", ""))
                age_seconds = max(0, int((now_utc - parsed).total_seconds()))
            except Exception:
                age_seconds = None

        hazard = item.get("hazard_type") or "FLOOD"
        node_id = item.get("node_id")
        item["hazard_type"] = hazard
        item["node_id"] = node_id
        item["node_name"] = node_names.get(node_id, f"Monitoring Node {node_id}")
        item["hazard_label"] = "Forest Fire Analysis" if hazard == "FOREST_FIRE" else "Flood Risk Analysis"
        item["last_received_at"] = received_at
        item["age_seconds"] = age_seconds
        item["is_online"] = age_seconds is not None and age_seconds <= stale_after_seconds

        item["water_level_m"] = item.get("latest_water_level_m")
        item["rainfall_mm"] = item.get("latest_rainfall_mm")
        item["thermal_temp_c"] = item.get("latest_thermal_temp_c")
        item["pm25_ugm3"] = item.get("latest_pm25_ugm3")

        if hazard == "FLOOD":
            item["danger_threshold_m"] = 5.0
            item["dam_capacity_m"] = 25.0
        else:
            item["thermal_danger_threshold_c"] = 65.0
            item["pm25_danger_threshold_ugm3"] = 120.0

        if live_only and not item["is_online"]:
            continue

        results.append(item)

    return results


def get_node_history(node_id: str, limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.timestamp, p.node_id, p.risk_score, p.flood_probability, p.risk_category, p.severity,
           p.estimated_time_to_threshold, p.secondary_hazard,
           COALESCE(p.hazard_type, 'FLOOD') as hazard_type,
           COALESCE(p.water_level_m, r.water_level_m, 1.85) as water_level_m,
           COALESCE(p.rainfall_mm, r.rainfall_mm, 0.0) as rainfall_mm,
           COALESCE(p.thermal_temp_c, 26.5) as thermal_temp_c,
           COALESCE(p.pm25_ugm3, 18.0) as pm25_ugm3,
           COALESCE(r.river_flow, 25.0) as river_flow,
           COALESCE(r.soil_moisture, 45.0) as soil_moisture,
           COALESCE(r.temperature, 28.0) as temperature,
           COALESCE(r.humidity, 50.0) as humidity,
           COALESCE(r.wind_speed, 5.0) as wind_speed
    FROM predictions p
    LEFT JOIN sensor_readings r ON r.node_id = p.node_id AND r.timestamp = p.timestamp
    WHERE p.node_id = ?
    ORDER BY p.prediction_id DESC
    LIMIT ?
    """, (node_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows][::-1]  # Chronological order
