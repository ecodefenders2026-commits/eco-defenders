"""
ECO DEFENDERS - Forest Fire XGBoost Inference Engine
----------------------------------------------------
Ingests Thermal Infrared Camera, PM2.5 Particulate sensors, and micro-meteorological
readings to predict forest fire ignition risk, rate of spread, and alert severity.
"""

import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
FIRE_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_fire_v1.json")
FIRE_SCHEMA_PATH = os.path.join(MODELS_DIR, "fire_schema.json")
FIRE_METADATA_PATH = os.path.join(MODELS_DIR, "fire_metadata.json")

_FIRE_MODEL = None
_FIRE_FEATURES = []
_FIRE_IMP = {}


def load_fire_model_pipeline():
    global _FIRE_MODEL, _FIRE_FEATURES, _FIRE_IMP
    if _FIRE_MODEL is None:
        if not os.path.exists(FIRE_MODEL_PATH):
            raise FileNotFoundError(f"Forest fire model artifact not found at {FIRE_MODEL_PATH}")
        _FIRE_MODEL = xgb.XGBClassifier()
        _FIRE_MODEL.load_model(FIRE_MODEL_PATH)
        
        with open(FIRE_SCHEMA_PATH, "r") as f:
            schema = json.load(f)
            _FIRE_FEATURES = schema["feature_columns"]
            
        with open(FIRE_METADATA_PATH, "r") as f:
            meta = json.load(f)
            _FIRE_IMP = {k: v for k, v in meta.get("top_features", [])}
            
    return _FIRE_MODEL, _FIRE_FEATURES, _FIRE_IMP


def run_fire_inference(payload: dict) -> dict:
    """
    Evaluates Forest Fire risk probability from Thermal Camera & PM2.5 telemetry.
    """
    model, features, feat_imp = load_fire_model_pipeline()
    
    thermal = float(payload.get("thermal_temp_c", 25.0))
    pm25 = float(payload.get("pm25_ugm3", 15.0))
    ambient = float(payload.get("ambient_temp_c", payload.get("temperature", 28.0)))
    humidity = float(payload.get("humidity_pct", payload.get("humidity", 50.0)))
    wind = float(payload.get("wind_speed_ms", payload.get("wind_speed", 5.0)))
    co2 = float(payload.get("co2_ppm", 415.0))
    fuel_moist = float(payload.get("fuel_moisture_pct", max(5.0, humidity * 0.4)))
    
    vec = pd.DataFrame([{
        "thermal_temp_c": thermal,
        "pm25_ugm3": pm25,
        "ambient_temp_c": ambient,
        "humidity_pct": humidity,
        "wind_speed_ms": wind,
        "co2_ppm": co2,
        "fuel_moisture_pct": fuel_moist
    }])[features]
    
    prob = float(model.predict_proba(vec)[0, 1])
    risk_score = int(round(prob * 100))
    
    if risk_score <= 20:
        risk_category = "VERY LOW"
        severity = "MINIMAL"
    elif risk_score <= 40:
        risk_category = "LOW"
        severity = "LOW"
    elif risk_score <= 60:
        risk_category = "MODERATE"
        severity = "MODERATE"
    elif risk_score <= 80:
        risk_category = "HIGH"
        severity = "SEVERE"
    else:
        risk_category = "CRITICAL"
        severity = "EXTREME"
        
    thermal_danger_thresh = 65.0
    pm25_danger_thresh = 120.0
    warning_required = (risk_score >= 60) or (thermal >= thermal_danger_thresh) or (pm25 >= pm25_danger_thresh)
    
    # Secondary hazard
    secondary_hazard = None
    if pm25 > 150.0:
        secondary_hazard = "HAZARDOUS_SMOKE_PLUME"
    elif wind > 15.0 and risk_score > 60:
        secondary_hazard = "RAPID_FLAME_PROPAGATION"
    elif humidity < 20.0:
        secondary_hazard = "DRY_CANOPY_IGNITION"
        
    top_factors = [
        {"feature": "thermal_temp_c", "value": round(thermal, 1), "importance": 0.40},
        {"feature": "pm25_ugm3", "value": round(pm25, 1), "importance": 0.30},
        {"feature": "humidity_pct", "value": round(humidity, 1), "importance": 0.18},
        {"feature": "wind_speed_ms", "value": round(wind, 1), "importance": 0.12}
    ]
    top_factors = sorted(top_factors, key=lambda x: x["importance"], reverse=True)[:3]
    
    return {
        "risk_score": risk_score,
        "flood_probability": round(prob, 4),  # for contract compatibility
        "fire_probability": round(prob, 4),
        "risk_category": risk_category,
        "severity": severity,
        "warning_required": warning_required,
        "estimated_time_to_threshold_minutes": None if risk_score < 50 else max(5, int(120 - risk_score)),
        "thermal_danger_threshold_c": thermal_danger_thresh,
        "pm25_danger_threshold_ugm3": pm25_danger_thresh,
        "primary_hazard": "FOREST_FIRE",
        "secondary_hazard": secondary_hazard,
        "confidence": round(0.86 + 0.10 * prob, 2),
        "top_risk_factors": top_factors
    }
