"""
End-to-End API Integration Tests with FastAPI TestClient
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"


def test_predict_flood_valid_contract():
    payload = {
        "node_id": "NODE_017",
        "timestamp": "2026-09-17T19:30:00+05:30",
        "rainfall_mm": 32.4,
        "water_level_m": 4.72,
        "river_flow": 185.3,
        "soil_moisture": 68.2,
        "dam_water_level_m": 18.4,
        "dam_capacity": 25.0,
        "temperature": 28.5,
        "humidity": 81.0,
        "pressure": 1004.2,
        "wind_speed": 11.6,
        "latitude": 18.1234,
        "longitude": 78.5678
    }
    res = client.post("/api/v1/predict/flood", json=payload)
    assert res.status_code == 200
    data = res.json()
    
    assert data["status"] == "success"
    assert "prediction" in data
    assert "location" in data
    assert "sensor_quality" in data
    assert "model" in data
    assert data["location"]["node_id"] == "NODE_017"
    assert "risk_score" in data["prediction"]
    assert "flood_probability" in data["prediction"]


def test_predict_flood_failsafe_invalid():
    invalid_payload = {
        "node_id": "NODE_999",
        "timestamp": "2026-09-17T19:30:00+05:30",
        "rainfall_mm": 10.0,
        "water_level_m": 3.0,
        "river_flow": 50.0,
        "soil_moisture": 50.0,
        "temperature": 25.0,
        "humidity": 70.0,
        "pressure": 1010.0,
        "wind_speed": 5.0,
        "latitude": 999.0,  # Invalid lat
        "longitude": 78.5678
    }
    res = client.post("/api/v1/predict/flood", json=invalid_payload)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["error"] == "Sensor Quality Failsafe Violation"


def test_node_synchronization_and_history():
    # 1. Post inference for NODE_FLOOD_01
    payload = {
        "node_id": "NODE_FLOOD_01",
        "timestamp": "2026-09-17T20:00:00+05:30",
        "rainfall_mm": 38.5,
        "water_level_m": 4.85,
        "river_flow": 190.0,
        "soil_moisture": 78.0,
        "dam_water_level_m": 22.5,
        "dam_capacity": 25.0,
        "temperature": 25.0,
        "humidity": 80.0,
        "pressure": 1002.0,
        "wind_speed": 14.2,
        "latitude": 18.1234,
        "longitude": 78.5678
    }
    res = client.post("/api/v1/predict/flood", json=payload)
    assert res.status_code == 200
    pred = res.json()["prediction"]
    assert pred["danger_threshold_m"] == 5.0
    assert pred["dam_capacity_m"] == 25.0
    
    # 2. Check /api/v1/nodes returns exactly the two nodes (Flood & Fire)
    nodes_res = client.get("/api/v1/nodes")
    assert nodes_res.status_code == 200
    nodes = nodes_res.json()["nodes"]
    assert len(nodes) == 2, "Must return exactly two nodes: Flood and Fire"
    node_ids = [n["node_id"] for n in nodes]
    assert "NODE_FLOOD_01" in node_ids
    assert "NODE_FIRE_01" in node_ids
    
    flood_node = next(n for n in nodes if n["node_id"] == "NODE_FLOOD_01")
    assert flood_node["water_level_m"] == 4.85
    assert flood_node["rainfall_mm"] == 38.5
    
    # 3. Check /api/v1/history/NODE_FLOOD_01 returns reading
    hist_res = client.get("/api/v1/history/NODE_FLOOD_01")
    assert hist_res.status_code == 200
    hist = hist_res.json()["history"]
    assert len(hist) > 0, "NODE_FLOOD_01 should have historical records"
    assert hist[-1]["water_level_m"] == 4.85
    assert hist[-1]["rainfall_mm"] == 38.5


def test_predict_fire_valid_contract():
    payload = {
        "node_id": "NODE_FIRE_01",
        "timestamp": "2026-09-18T00:30:00+05:30",
        "thermal_temp_c": 125.0,
        "pm25_ugm3": 380.0,
        "ambient_temp_c": 38.0,
        "humidity_pct": 18.0,
        "wind_speed_ms": 14.5,
        "fuel_moisture_pct": 5.0,
        "latitude": 18.2500,
        "longitude": 78.6500
    }
    res = client.post("/api/v1/predict/fire", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    pred = data["prediction"]
    assert pred["risk_score"] >= 80, "Severe hotspot and high PM2.5 must yield high fire risk score"
    assert pred["risk_category"] in ["HIGH", "VERY HIGH", "CRITICAL"]
    assert pred["thermal_danger_threshold_c"] == 65.0
    assert pred["pm25_danger_threshold_ugm3"] == 120.0
    
    # History check for NODE_FIRE_01
    hist_res = client.get("/api/v1/history/NODE_FIRE_01")
    assert hist_res.status_code == 200
    hist = hist_res.json()["history"]
    assert len(hist) > 0
    assert hist[-1]["thermal_temp_c"] == 125.0
    assert hist[-1]["pm25_ugm3"] == 380.0

