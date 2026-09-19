"""
ECO DEFENDERS - XGBoost Inference Engine & Risk Scoring System
------------------------------------------------------------
Loads saved production model artifacts, constructs temporal feature vectors
from real-time sensor payloads, evaluates flood risk probability, calculates
risk scores, determines severity levels, and extracts top risk contributing factors.
"""

import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb

from backend.validator import RECENT_READINGS_BUFFER
from backend.hydrological import calculate_time_to_threshold, NODE_THRESHOLDS

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_flood_v1.json")
SCHEMA_PATH = os.path.join(MODELS_DIR, "feature_schema.json")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")

# Global singleton model instances
_XGB_MODEL = None
_FEATURE_COLUMNS = []
_TOP_FEATURES_IMPORTANCE = {}


def load_model_pipeline():
    global _XGB_MODEL, _FEATURE_COLUMNS, _TOP_FEATURES_IMPORTANCE
    if _XGB_MODEL is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}. Run python src/train.py first!")
            
        _XGB_MODEL = xgb.XGBClassifier()
        _XGB_MODEL.load_model(MODEL_PATH)
        
        with open(SCHEMA_PATH, "r") as f:
            schema = json.load(f)
            _FEATURE_COLUMNS = schema["feature_columns"]
            
        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)
            _TOP_FEATURES_IMPORTANCE = {k: v for k, v in metadata.get("top_features", [])}
            
    return _XGB_MODEL, _FEATURE_COLUMNS, _TOP_FEATURES_IMPORTANCE


def build_feature_vector(node_id: str, current_payload: dict) -> pd.DataFrame:
    """
    Constructs a 1-row feature vector using current payload and recent node telemetry history.
    """
    buffer = RECENT_READINGS_BUFFER.get(node_id, [current_payload])
    df_buf = pd.DataFrame(buffer)
    df_buf["timestamp"] = pd.to_datetime(df_buf["timestamp"], format="mixed", errors="coerce")
    df_buf = df_buf.sort_values("timestamp")
    
    # Calculate temporal rolling features from buffer
    rain = current_payload.get("rainfall_mm", 0.0)
    water = current_payload.get("water_level_m", 0.0)
    flow = current_payload.get("river_flow", 15.0)
    soil = current_payload.get("soil_moisture", 35.0)
    dam_water = current_payload.get("dam_water_level_m", 15.0)
    dam_cap = current_payload.get("dam_capacity", 25.0)
    temp = current_payload.get("temperature", 28.0)
    hum = current_payload.get("humidity", 75.0)
    press = current_payload.get("pressure", 1013.0)
    wind = current_payload.get("wind_speed", 5.0)
    
    # Buffer rolling estimates
    recent_rains = df_buf["rainfall_mm"].tolist() if "rainfall_mm" in df_buf else [rain]
    recent_waters = df_buf["water_level_m"].tolist() if "water_level_m" in df_buf else [water]
    
    rainfall_15m = rain
    rainfall_30m = sum(recent_rains[-2:]) if len(recent_rains) >= 2 else rain
    rainfall_1h = sum(recent_rains[-4:]) if len(recent_rains) >= 4 else rain * 2.5
    rainfall_3h = sum(recent_rains[-12:]) if len(recent_rains) >= 12 else rainfall_1h * 2.0
    rainfall_6h = sum(recent_rains[-24:]) if len(recent_rains) >= 24 else rainfall_3h * 1.5
    
    water_level_change_15m = (recent_waters[-1] - recent_waters[-2]) if len(recent_waters) >= 2 else 0.0
    water_level_rate_per_hour = water_level_change_15m * 4.0
    water_level_max_3h = max(recent_waters[-12:]) if len(recent_waters) >= 12 else max(recent_waters)
    water_level_mean_1h = float(np.mean(recent_waters[-4:])) if len(recent_waters) >= 4 else water
    
    river_flow_change_15m = 0.0
    soil_moisture_trend_1h = 0.0
    pressure_change_3h = 0.0
    temp_change_1h = 0.0
    
    ts = pd.to_datetime(current_payload.get("timestamp"), format="mixed", errors="coerce")
    hour_of_day = ts.hour if hasattr(ts, "hour") else 12
    day_of_year = ts.dayofyear if hasattr(ts, "dayofyear") else 180
    dam_fill_ratio = dam_water / max(1.0, dam_cap)
    
    feature_dict = {
        "rainfall_mm": rain,
        "water_level_m": water,
        "river_flow": flow,
        "soil_moisture": soil,
        "dam_water_level_m": dam_water,
        "dam_fill_ratio": dam_fill_ratio,
        "temperature": temp,
        "humidity": hum,
        "pressure": press,
        "wind_speed": wind,
        "rainfall_15m": rainfall_15m,
        "rainfall_30m": rainfall_30m,
        "rainfall_1h": rainfall_1h,
        "rainfall_3h": rainfall_3h,
        "rainfall_6h": rainfall_6h,
        "water_level_change_15m": water_level_change_15m,
        "water_level_rate_per_hour": water_level_rate_per_hour,
        "water_level_max_3h": water_level_max_3h,
        "water_level_mean_1h": water_level_mean_1h,
        "river_flow_change_15m": river_flow_change_15m,
        "soil_moisture_trend_1h": soil_moisture_trend_1h,
        "pressure_change_3h": pressure_change_3h,
        "temp_change_1h": temp_change_1h,
        "hour_of_day": hour_of_day,
        "day_of_year": day_of_year
    }
    
    return pd.DataFrame([feature_dict])


def run_flood_inference(payload: dict, quality_status: dict) -> dict:
    """
    Main ML inference runner. Produces XGBoost probability, normalized risk score,
    severity category, secondary hazard assessment, time-to-threshold, and explainability factors.
    """
    model, feature_cols, top_imp = load_model_pipeline()
    node_id = payload.get("node_id", "NODE_001")
    
    # Construct feature vector
    X_df = build_feature_vector(node_id, payload)
    X_vec = X_df[feature_cols]
    
    # Execute XGBoost Probability
    prob = float(model.predict_proba(X_vec)[0, 1])
    
    # Calculate Risk Score (0-100)
    risk_score = int(round(prob * 100))
    
    # Risk Category & Severity Mapping
    if risk_score <= 20:
        risk_category = "VERY LOW"
        severity = "MINIMAL"
    elif risk_score <= 40:
        risk_category = "LOW"
        severity = "MODERATE"
    elif risk_score <= 60:
        risk_category = "MODERATE"
        severity = "MODERATE"
    elif risk_score <= 80:
        risk_category = "HIGH"
        severity = "SEVERE"
    else:
        risk_category = "CRITICAL"
        severity = "EXTREME"
        
    threshold = NODE_THRESHOLDS.get(node_id, 5.0)
    current_water = payload.get("water_level_m", 0.0)
    
    # Operational Warning Trigger (Configurable Threshold)
    warning_required = (risk_score >= 60) or (current_water >= threshold * 0.9)
    
    # Time to threshold calculation
    rate_per_hour = float(X_df["water_level_rate_per_hour"].iloc[0])
    ttt = calculate_time_to_threshold(
        node_id, current_water, rate_per_hour, quality_status.get("status", "OK")
    )
    
    # Secondary Hazard Assessment
    secondary_hazard = None
    if rate_per_hour > 0.4 or payload.get("rainfall_mm", 0) > 20.0:
        secondary_hazard = "FLASH_FLOOD"
    elif X_df["dam_fill_ratio"].iloc[0] > 0.9:
        secondary_hazard = "DAM_OVERFLOW"
    elif payload.get("soil_moisture", 0) > 90.0:
        secondary_hazard = "LANDSLIDE_RISK"
        
    # Explainability (Top Risk Contributing Factors)
    top_factors = []
    for col in ["water_level_m", "rainfall_1h", "water_level_rate_per_hour", "soil_moisture", "dam_fill_ratio"]:
        if col in feature_cols:
            val = float(X_df[col].iloc[0])
            imp = top_imp.get(col, 0.10)
            top_factors.append({
                "feature": col,
                "value": round(val, 2),
                "importance": round(imp, 2)
            })
            
    top_factors = sorted(top_factors, key=lambda x: x["importance"], reverse=True)[:3]
    
    return {
        "risk_score": risk_score,
        "flood_probability": round(prob, 4),
        "risk_category": risk_category,
        "severity": severity,
        "warning_required": warning_required,
        "estimated_time_to_threshold_minutes": ttt,
        "danger_threshold_m": threshold,
        "dam_capacity_m": float(payload.get("dam_capacity", 25.0)),
        "primary_hazard": "FLOOD",
        "secondary_hazard": secondary_hazard,
        "confidence": round(0.85 + 0.10 * prob, 2),
        "top_risk_factors": top_factors
    }
