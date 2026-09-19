"""
Integration Tests for XGBoost Model Inference & Risk Scoring
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.inference import run_flood_inference


def test_xgboost_inference_normal_state():
    payload = {
        "node_id": "NODE_001",
        "timestamp": "2026-09-17T19:30:00+05:30",
        "rainfall_mm": 0.5,
        "water_level_m": 1.5,
        "river_flow": 20.0,
        "soil_moisture": 30.0,
        "dam_water_level_m": 10.0,
        "dam_capacity": 25.0,
        "temperature": 28.0,
        "humidity": 70.0,
        "pressure": 1013.0,
        "wind_speed": 5.0,
        "latitude": 18.1234,
        "longitude": 78.5678
    }
    quality = {"status": "OK", "issues": []}
    result = run_flood_inference(payload, quality)
    
    assert "risk_score" in result
    assert "flood_probability" in result
    assert result["risk_category"] in ["VERY LOW", "LOW"]
    assert result["warning_required"] is False


def test_xgboost_inference_flood_warning():
    payload = {
        "node_id": "NODE_001",
        "timestamp": "2026-09-17T19:30:00+05:30",
        "rainfall_mm": 55.0,
        "water_level_m": 5.2,
        "river_flow": 280.0,
        "soil_moisture": 95.0,
        "dam_water_level_m": 24.5,
        "dam_capacity": 25.0,
        "temperature": 20.0,
        "humidity": 98.0,
        "pressure": 988.0,
        "wind_speed": 25.0,
        "latitude": 18.1234,
        "longitude": 78.5678
    }
    quality = {"status": "OK", "issues": []}
    result = run_flood_inference(payload, quality)
    
    assert result["risk_score"] >= 60
    assert result["risk_category"] in ["HIGH", "CRITICAL"]
    assert result["warning_required"] is True
    assert result["primary_hazard"] == "FLOOD"
