"""
ECO DEFENDERS - XGBoost Model Training & Baseline Benchmarking
------------------------------------------------------------
Trains XGBClassifier on chronological time-series split data, compares against
Logistic Regression, Decision Tree, and Random Forest baselines, and serializes
the full production ML pipeline.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, precision_recall_curve, auc

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from data_pipeline import preprocess_and_engineer_features, RAW_DATA_PATH, PROCESSED_DATA_PATH

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

FEATURE_COLUMNS = [
    "rainfall_mm",
    "water_level_m",
    "river_flow",
    "soil_moisture",
    "dam_water_level_m",
    "dam_fill_ratio",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "rainfall_15m",
    "rainfall_30m",
    "rainfall_1h",
    "rainfall_3h",
    "rainfall_6h",
    "water_level_change_15m",
    "water_level_rate_per_hour",
    "water_level_max_3h",
    "water_level_mean_1h",
    "river_flow_change_15m",
    "soil_moisture_trend_1h",
    "pressure_change_3h",
    "temp_change_1h",
    "hour_of_day",
    "day_of_year"
]

TARGET_COLUMN = "flood_target_60m"


def train_and_evaluate_models():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Always generate freshly processed dataset with boundary conditions
    df = preprocess_and_engineer_features()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
        
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    # Chronological Time-Series Split (70% Train, 15% Val, 15% Test)
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    print(f"[INFO] Dataset Chronological Split:")
    print(f"       Train: {len(train_df)} rows ({train_df['timestamp'].min()} -> {train_df['timestamp'].max()})")
    print(f"       Val  : {len(val_df)} rows ({val_df['timestamp'].min()} -> {val_df['timestamp'].max()})")
    print(f"       Test : {len(test_df)} rows ({test_df['timestamp'].min()} -> {test_df['timestamp'].max()})")
    
    X_train, y_train = train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN]
    X_val, y_val = val_df[FEATURE_COLUMNS], val_df[TARGET_COLUMN]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df[TARGET_COLUMN]
    
    # Fit StandardScaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # Class imbalance weight ratio
    pos_count = (y_train == 1).sum()
    neg_count = (y_train == 0).sum()
    scale_pos_weight = neg_count / max(1, pos_count)
    
    # Monotonic positive constraints for physical variables (+1 strictly non-decreasing)
    monotonic_dict = {
        "water_level_m": 1,
        "river_flow": 1,
        "water_level_rate_per_hour": 1,
        "water_level_change_15m": 1,
        "water_level_max_3h": 1,
        "water_level_mean_1h": 1,
        "rainfall_15m": 1,
        "rainfall_30m": 1,
        "rainfall_1h": 1,
        "rainfall_3h": 1,
        "rainfall_6h": 1,
        "soil_moisture": 1,
        "dam_fill_ratio": 1
    }
    monotone_constraints = tuple(monotonic_dict.get(col, 0) for col in FEATURE_COLUMNS)
    
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=6, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42),
        "XGBoost (Primary)": xgb.XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.03,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=5,
            gamma=0.2,
            reg_alpha=0.1,
            reg_lambda=2.0,
            monotone_constraints=monotone_constraints,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            early_stopping_rounds=30,
            random_state=42
        )
    }
    
    results = {}
    best_xgb_model = None
    
    for name, model in models.items():
        if "XGBoost" in name:
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            best_xgb_model = model
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
        else:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_prob = model.predict_proba(X_test_scaled)[:, 1]
            
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_prob) if len(np.unique(y_test)) > 1 else 0.0
        
        precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_prob)
        pr_auc = auc(recall_curve, precision_curve) if len(np.unique(y_test)) > 1 else 0.0
        cm = confusion_matrix(y_test, y_pred).tolist()
        
        results[name] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "confusion_matrix": cm
        }
        
        print(f"\n[MODEL] Performance: {name}")
        print(f"        Accuracy : {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")
        print(f"        Confusion Matrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")

    # Feature Importance of XGBoost
    importance = best_xgb_model.feature_importances_
    feat_imp = sorted(zip(FEATURE_COLUMNS, [float(x) for x in importance]), key=lambda x: x[1], reverse=True)
    
    # Save Pipeline Artifacts
    xgb_json_path = os.path.join(MODELS_DIR, "xgboost_flood_v1.json")
    scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
    schema_path = os.path.join(MODELS_DIR, "feature_schema.json")
    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
    
    best_xgb_model.save_model(xgb_json_path)
    joblib.dump(scaler, scaler_path)
    
    schema_info = {
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "horizon_minutes": 60,
        "node_thresholds": {
            "NODE_001": 5.0, "NODE_002": 5.5, "NODE_003": 4.8, "NODE_004": 6.2, "NODE_005": 5.2
        }
    }
    with open(schema_path, "w") as f:
        json.dump(schema_info, f, indent=2)
        
    metadata = {
        "model_name": "xgboost_flood",
        "model_version": "1.0.0",
        "trained_timestamp": pd.Timestamp.now().isoformat(),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "hyperparameters": {
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "gamma": 0.1,
            "scale_pos_weight": round(float(scale_pos_weight), 2)
        },
        "evaluation_metrics": results,
        "top_features": feat_imp[:10]
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"\n[OK] Model Pipeline saved successfully in {MODELS_DIR}/:")
    print(f"     - Model: xgboost_flood_v1.json")
    print(f"     - Scaler: scaler.pkl")
    print(f"     - Schema: feature_schema.json")
    print(f"     - Metadata: model_metadata.json")
    return results, metadata


if __name__ == "__main__":
    train_and_evaluate_models()
