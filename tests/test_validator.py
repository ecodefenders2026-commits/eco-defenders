"""
Unit Tests for Sensor Validation & Failsafe Layer
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.validator import validate_sensor_payload


def test_valid_sensor_payload():
    valid_payload = {
        "node_id": "NODE_TEST_01",
        "timestamp": "2026-09-19T10:30:00+05:30",
        "rainfall_mm": 12.5,
        "water_level_m": 3.4,
        "river_flow": 120.0,
        "soil_moisture": 65.0,
        "temperature": 25.0,
        "humidity": 80.0,
        "pressure": 1010.0,
        "wind_speed": 10.0,
        "latitude": 18.1234,
        "longitude": 78.5678
    }
    result = validate_sensor_payload(valid_payload)
    assert result["status"] == "OK"
    assert len(result["issues"]) == 0


def test_invalid_coordinates():
    invalid_payload = {
        "node_id": "NODE_TEST_02",
        "timestamp": "2026-09-19T10:30:00+05:30",
        "rainfall_mm": 5.0,
        "water_level_m": 2.0,
        "latitude": 999.0,  # Invalid
        "longitude": 78.5678
    }
    result = validate_sensor_payload(invalid_payload)
    assert result["status"] == "ERROR"
    assert any("latitude" in issue for issue in result["issues"])


def test_negative_rainfall_auto_correction():
    payload = {
        "node_id": "NODE_TEST_03",
        "timestamp": "2026-09-19T10:30:00+05:30",
        "rainfall_mm": -15.0,  # Invalid negative
        "water_level_m": 2.0,
        "latitude": 18.1234,
        "longitude": 78.5678
    }
    result = validate_sensor_payload(payload)
    assert result["status"] == "WARNING"
    assert result["payload"]["rainfall_mm"] == 0.0
