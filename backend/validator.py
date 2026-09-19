"""
ECO DEFENDERS - Sensor Quality & Failsafe Layer
---------------------------------------------
Validates incoming IoT sensor readings before machine learning inference.
Detects sensor freezes, impossible physical spikes, stale timestamps,
out-of-bound environmental values, and missing required parameters.
"""

from typing import Dict, Any
from datetime import datetime, timezone
import pandas as pd

# In-memory buffer of recent node telemetry to detect frozen or jumping sensors
RECENT_READINGS_BUFFER: Dict[str, list] = {}


def validate_sensor_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates sensor readings for physical validity and temporal consistency.
    Returns dictionary with status ('OK', 'WARNING', 'ERROR') and list of detected issues.
    """
    issues = []
    status = "OK"
    
    node_id = payload.get("node_id", "UNKNOWN")
    
    # 1. Coordinate Validation
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    if lat is None or not (-90 <= lat <= 90):
        issues.append(f"Invalid latitude coordinate: {lat}")
        status = "ERROR"
    if lon is None or not (-180 <= lon <= 180):
        issues.append(f"Invalid longitude coordinate: {lon}")
        status = "ERROR"
        
    # 2. Physical Range Validation
    rain = payload.get("rainfall_mm", 0.0)
    if rain < 0:
        issues.append(f"Negative rainfall reading detected ({rain} mm); reset to 0.0")
        payload["rainfall_mm"] = 0.0
        if status != "ERROR":
            status = "WARNING"
            
    water_level = payload.get("water_level_m", 0.0)
    if water_level < 0:
        issues.append(f"Negative water level reading detected ({water_level} m); invalid sensor")
        status = "ERROR"
    elif water_level > 25.0:
        issues.append(f"Extreme water level reading detected ({water_level} m); potential outlier/sensor fault")
        if status != "ERROR":
            status = "WARNING"
            
    soil = payload.get("soil_moisture", 0.0)
    if soil < 0 or soil > 100:
        issues.append(f"Soil moisture out of bounds [0-100%]: {soil}%")
        if status != "ERROR":
            status = "WARNING"
            
    pressure = payload.get("pressure", 1013.25)
    if pressure < 850 or pressure > 1080:
        issues.append(f"Atmospheric pressure outside meteorological bounds [850-1080 hPa]: {pressure} hPa")
        if status != "ERROR":
            status = "WARNING"
            
    # 3. Timestamp Freshness Check
    ts_str = payload.get("timestamp")
    if ts_str:
        try:
            ts = pd.to_datetime(ts_str, format="mixed", errors="coerce")
            if pd.notnull(ts):
                now = pd.Timestamp.now(tz=ts.tzinfo if ts.tzinfo else None)
                time_diff = abs((now - ts).total_seconds())
                if time_diff > 86400:  # 24 hours stale
                    issues.append(f"Telemetry timestamp is stale ({round(time_diff / 3600, 1)} hours offset)")
                    if status != "ERROR":
                        status = "WARNING"
        except Exception:
            issues.append(f"Unparseable timestamp format: {ts_str}")
            status = "ERROR"
            
    # 4. Temporal Buffer Checks (Frozen sensors & Sudden Spikes)
    if node_id not in RECENT_READINGS_BUFFER:
        RECENT_READINGS_BUFFER[node_id] = []
        
    buffer = RECENT_READINGS_BUFFER[node_id]
    buffer.append(payload)
    if len(buffer) > 10:
        buffer.pop(0)
        
    if len(buffer) >= 4:
        recent_levels = [r.get("water_level_m", 0.0) for r in buffer[-4:]]
        # Frozen check: exact same float value for last 4 consecutive updates
        if len(set(recent_levels)) == 1:
            issues.append(f"Water level sensor reading frozen at {recent_levels[0]} m for 4 consecutive readings")
            if status != "ERROR":
                status = "WARNING"
                
        # Impossible jump check: > 3.0m change between consecutive readings
        last_diff = abs(recent_levels[-1] - recent_levels[-2])
        if last_diff > 3.0:
            issues.append(f"Sudden impossible water level jump of {round(last_diff, 2)} m detected")
            if status != "ERROR":
                status = "WARNING"
                
    return {
        "status": status,
        "issues": issues,
        "payload": payload
    }
