"""
ECO DEFENDERS - Forest Fire XGBoost Training Pipeline
----------------------------------------------------
Generates multi-sensor wildfire telemetry combining Thermal Infrared Camera,
PM2.5 Particulate sensors, meteorological factors (humidity, wind speed, temp),
and trains an XGBoost model with positive monotonic constraints for thermal temp & PM2.5,
and negative monotonic constraints for humidity.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
FIRE_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_fire_v1.json")
FIRE_SCHEMA_PATH = os.path.join(MODELS_DIR, "fire_schema.json")
FIRE_METADATA_PATH = os.path.join(MODELS_DIR, "fire_metadata.json")

FIRE_FEATURE_COLUMNS = [
    "thermal_temp_c",
    "pm25_ugm3",
    "ambient_temp_c",
    "humidity_pct",
    "wind_speed_ms",
    "co2_ppm",
    "fuel_moisture_pct"
]

TARGET_COLUMN = "fire_target"


def generate_wildfire_dataset(n_samples: int = 8000) -> pd.DataFrame:
    """
    Generates synthetic wildfire telemetry across nominal, smoldering, and active fire states.
    Thermal Camera hotspot: nominal 20-35C, smoldering 50-75C, active 80-200C.
    PM2.5 Sensor: nominal 10-30 ug/m3, smoldering 80-180 ug/m3, active 200-600 ug/m3.
    """
    np.random.seed(42)
    records = []
    
    for i in range(n_samples):
        state_rand = np.random.uniform(0, 1)
        if state_rand < 0.50:
            # 1. Nominal / Low Risk State
            thermal = np.random.uniform(18.0, 38.0)
            pm25 = np.random.uniform(5.0, 35.0)
            ambient = np.random.uniform(18.0, 32.0)
            humidity = np.random.uniform(45.0, 95.0)
            wind = np.random.uniform(1.0, 8.0)
            fuel_moist = np.random.uniform(25.0, 70.0)
            co2 = np.random.uniform(390.0, 450.0)
        elif state_rand < 0.75:
            # 2. Elevated / Smoldering Transition Zone
            thermal = np.random.uniform(42.0, 70.0)
            pm25 = np.random.uniform(40.0, 160.0)
            ambient = np.random.uniform(28.0, 38.0)
            humidity = np.random.uniform(20.0, 48.0)
            wind = np.random.uniform(4.0, 15.0)
            fuel_moist = np.random.uniform(12.0, 30.0)
            co2 = np.random.uniform(450.0, 650.0)
        else:
            # 3. Active Wildfire / Critical Breach
            thermal = np.random.uniform(68.0, 160.0)
            pm25 = np.random.uniform(140.0, 600.0)
            ambient = np.random.uniform(32.0, 46.0)
            humidity = np.random.uniform(8.0, 26.0)
            wind = np.random.uniform(8.0, 28.0)
            fuel_moist = np.random.uniform(4.0, 15.0)
            co2 = np.random.uniform(600.0, 1500.0)
            
        # Continuous physics-based probability of active fire danger
        # Thermal danger threshold: 65C. PM2.5 threshold: 120 ug/m3. Low humidity penalty.
        thermal_norm = (thermal - 25.0) / 45.0
        pm_norm = (pm25 - 25.0) / 100.0
        dryness_norm = (60.0 - humidity) / 45.0
        wind_norm = wind / 15.0
        
        composite_index = (0.45 * thermal_norm) + (0.30 * pm_norm) + (0.15 * dryness_norm) + (0.10 * wind_norm)
        prob = 1.0 / (1.0 + np.exp(-3.2 * (composite_index - 0.75)))
        target = 1 if (np.random.uniform(0.0, 1.0) < prob) else 0
        
        records.append({
            "thermal_temp_c": round(thermal, 2),
            "pm25_ugm3": round(pm25, 2),
            "ambient_temp_c": round(ambient, 2),
            "humidity_pct": round(humidity, 2),
            "wind_speed_ms": round(wind, 2),
            "co2_ppm": round(co2, 1),
            "fuel_moisture_pct": round(fuel_moist, 2),
            "fire_target": target
        })
        
    return pd.DataFrame(records)


def train_fire_model():
    os.makedirs(MODELS_DIR, exist_ok=True)
    df = generate_wildfire_dataset(n_samples=8000)
    
    n = len(df)
    train_end = int(n * 0.75)
    train_df = df.iloc[:train_end]
    test_df = df.iloc[train_end:]
    
    X_train = train_df[FIRE_FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[FIRE_FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]
    
    # Monotonic constraints:
    # thermal_temp: +1, pm25: +1, ambient_temp: +1, wind_speed: +1, co2: +1
    # humidity: -1 (higher humidity strictly lowers fire risk)
    # fuel_moisture: -1 (higher moisture strictly lowers fire risk)
    monotonic_dict = {
        "thermal_temp_c": 1,
        "pm25_ugm3": 1,
        "ambient_temp_c": 1,
        "humidity_pct": -1,
        "wind_speed_ms": 1,
        "co2_ppm": 1,
        "fuel_moisture_pct": -1
    }
    monotone_constraints = tuple(monotonic_dict.get(c, 0) for c in FIRE_FEATURE_COLUMNS)
    
    model = xgb.XGBClassifier(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=4,
        reg_lambda=2.0,
        monotone_constraints=monotone_constraints,
        eval_metric="logloss",
        random_state=42
    )
    
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    
    print(f"\n[FOREST FIRE MODEL EVALUATION]")
    print(f"Accuracy : {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")
    
    # Feature importance
    importance = model.feature_importances_
    feat_imp = sorted(zip(FIRE_FEATURE_COLUMNS, [float(x) for x in importance]), key=lambda x: x[1], reverse=True)
    
    model.save_model(FIRE_MODEL_PATH)
    
    schema_info = {
        "feature_columns": FIRE_FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "danger_thresholds": {
            "thermal_temp_c": 65.0,
            "pm25_ugm3": 120.0
        }
    }
    with open(FIRE_SCHEMA_PATH, "w") as f:
        json.dump(schema_info, f, indent=2)
        
    metadata = {
        "model_name": "xgboost_forest_fire",
        "model_version": "1.0.0",
        "metrics": {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4)
        },
        "top_features": feat_imp
    }
    with open(FIRE_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"[OK] Forest Fire Model saved to {FIRE_MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_fire_model()
