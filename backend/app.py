"""
ECO DEFENDERS - FastAPI Inference Server & Web Backend
---------------------------------------------------
Main application entry point. Exposes versioned REST APIs for real-time ML inference,
sensor quality checks, historical telemetry retrieval, node status grid, and simulator.
"""

import os
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.schema import (
    SensorPayload, PredictionResponse, LocationDetails, ModelDetails, 
    SensorQualityStatus, PredictionDetails, FireSensorPayload, FirePredictionResponse
)
from backend.validator import validate_sensor_payload
from backend.inference import run_flood_inference
from backend.fire_inference import run_fire_inference
from backend.db import (
    init_db, save_reading_and_prediction, save_fire_reading_and_prediction,
    get_latest_node_statuses, get_node_history
)
from backend.hydrological import NODE_THRESHOLDS

app = FastAPI(
    title="ECO DEFENDERS AI Multi-Hazard Engine",
    description="Real-Time XGBoost Flood & Forest Fire Early Warning Pipeline",
    version="2.0.0"
)

# Enable CORS for Web Dashboard Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "online",
        "system": "ECO DEFENDERS Multi-Hazard Engine",
        "model_version": "xgboost_flood_v1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    }


@app.post("/api/v1/predict/flood", response_model=PredictionResponse)
def predict_flood(payload: SensorPayload):
    start_time = time.time()
    raw_dict = payload.model_dump()
    
    # 1. Sensor Validation Layer
    quality = validate_sensor_payload(raw_dict)
    
    if quality["status"] == "ERROR":
        # System failsafe response
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Sensor Quality Failsafe Violation",
                "issues": quality["issues"]
            }
        )
        
    # 2. Run XGBoost ML & Hydrological Engine Inference
    inference_result = run_flood_inference(quality["payload"], quality)
    
    # 3. Construct API Contract Response
    response = {
        "status": "success",
        "prediction": inference_result,
        "location": {
            "node_id": payload.node_id,
            "latitude": payload.latitude,
            "longitude": payload.longitude
        },
        "sensor_quality": {
            "status": quality["status"],
            "issues": quality["issues"]
        },
        "model": {
            "name": "xgboost_flood",
            "version": "1.0.0"
        },
        "timestamp": payload.timestamp
    }
    
    # 4. Save to Database
    try:
        save_reading_and_prediction(raw_dict, response)
    except Exception as e:
        print(f"[DB WARN] Failed to save prediction: {e}")
        
    return response


@app.post("/api/v1/predict/fire", response_model=FirePredictionResponse)
def predict_fire(payload: FireSensorPayload):
    raw_dict = payload.model_dump()
    
    # 1. Physical Validity Check
    issues = []
    status = "OK"
    if payload.thermal_temp_c < -20.0 or payload.thermal_temp_c > 400.0:
        issues.append(f"Thermal camera reading out of physical range: {payload.thermal_temp_c}°C")
        status = "WARNING"
    if payload.pm25_ugm3 < 0.0 or payload.pm25_ugm3 > 1500.0:
        issues.append(f"PM2.5 particulate reading out of physical range: {payload.pm25_ugm3} ug/m3")
        status = "WARNING"
        
    # 2. Run Forest Fire Inference
    fire_result = run_fire_inference(raw_dict)
    
    response = {
        "status": "success",
        "prediction": fire_result,
        "location": {
            "node_id": payload.node_id,
            "latitude": payload.latitude or 18.2500,
            "longitude": payload.longitude or 78.6500
        },
        "sensor_quality": {
            "status": status,
            "issues": issues
        },
        "model": {
            "name": "xgboost_forest_fire",
            "version": "1.0.0"
        },
        "timestamp": payload.timestamp
    }
    
    # 3. Save to Database
    try:
        save_fire_reading_and_prediction(raw_dict, response)
    except Exception as e:
        print(f"[DB WARN] Failed to save fire prediction: {e}")
        
    return response


@app.get("/api/v1/nodes")
def get_nodes():
    statuses = get_latest_node_statuses()
    return {"nodes": statuses}


@app.get("/api/v1/history/{node_id}")
def get_history(node_id: str, limit: int = 40):
    history = get_node_history(node_id, limit=limit)
    return {"node_id": node_id, "history": history}


@app.post("/api/v1/simulate")
def trigger_simulation(scenario: str = "FLOOD_WARNING", node_id: str = "NODE_FLOOD_01"):
    """
    Triggers simulated preset telemetry payloads pushing directly into inference pipeline.
    Scenarios: NORMAL, HEAVY_RAIN, RAPIDLY_RISING_WATER, FLOOD_WARNING, CRITICAL_FLOOD, SENSOR_FAILURE,
               NORMAL_FOREST, SMOKE_WARNING, CRITICAL_FIRE
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    
    scenarios = {
        "NORMAL": {
            "node_id": node_id, "timestamp": ts, "rainfall_mm": 1.2, "water_level_m": 1.8,
            "river_flow": 22.0, "soil_moisture": 42.0, "dam_water_level_m": 12.0, "dam_capacity": 25.0,
            "temperature": 27.5, "humidity": 72.0, "pressure": 1012.0, "wind_speed": 4.5,
            "latitude": 18.1234, "longitude": 78.5678
        },
        "HEAVY_RAIN": {
            "node_id": node_id, "timestamp": ts, "rainfall_mm": 18.5, "water_level_m": 3.2,
            "river_flow": 85.0, "soil_moisture": 75.0, "dam_water_level_m": 18.5, "dam_capacity": 25.0,
            "temperature": 24.0, "humidity": 88.0, "pressure": 1005.0, "wind_speed": 12.0,
            "latitude": 18.1234, "longitude": 78.5678
        },
        "RAPIDLY_RISING_WATER": {
            "node_id": node_id, "timestamp": ts, "rainfall_mm": 35.0, "water_level_m": 4.5,
            "river_flow": 160.0, "soil_moisture": 88.0, "dam_water_level_m": 22.0, "dam_capacity": 25.0,
            "temperature": 22.5, "humidity": 94.0, "pressure": 998.0, "wind_speed": 18.0,
            "latitude": 18.1234, "longitude": 78.5678
        },
        "FLOOD_WARNING": {
            "node_id": node_id, "timestamp": ts, "rainfall_mm": 48.0, "water_level_m": 4.9,
            "river_flow": 210.0, "soil_moisture": 92.0, "dam_water_level_m": 24.0, "dam_capacity": 25.0,
            "temperature": 21.0, "humidity": 96.0, "pressure": 994.0, "wind_speed": 22.0,
            "latitude": 18.1234, "longitude": 78.5678
        },
        "CRITICAL_FLOOD": {
            "node_id": node_id, "timestamp": ts, "rainfall_mm": 65.0, "water_level_m": 5.8,
            "river_flow": 310.0, "soil_moisture": 98.0, "dam_water_level_m": 24.9, "dam_capacity": 25.0,
            "temperature": 20.0, "humidity": 99.0, "pressure": 988.0, "wind_speed": 28.0,
            "latitude": 18.1234, "longitude": 78.5678
        },
        "SENSOR_FAILURE": {
            "node_id": node_id, "timestamp": ts, "rainfall_mm": -10.0, "water_level_m": 30.0,
            "river_flow": -5.0, "soil_moisture": 150.0, "dam_water_level_m": 0.0, "dam_capacity": 25.0,
            "temperature": 99.0, "humidity": 0.0, "pressure": 500.0, "wind_speed": -2.0,
            "latitude": 999.0, "longitude": 999.0
        },
        "NORMAL_FOREST": {
            "node_id": "NODE_FIRE_01", "timestamp": ts,
            "thermal_temp_c": 26.5, "pm25_ugm3": 14.5, "ambient_temp_c": 27.0,
            "humidity_pct": 65.0, "wind_speed_ms": 3.5, "co2_ppm": 412.0, "fuel_moisture_pct": 45.0,
            "latitude": 18.2500, "longitude": 78.6500
        },
        "SMOKE_WARNING": {
            "node_id": "NODE_FIRE_01", "timestamp": ts,
            "thermal_temp_c": 54.0, "pm25_ugm3": 95.0, "ambient_temp_c": 35.0,
            "humidity_pct": 24.0, "wind_speed_ms": 11.0, "co2_ppm": 580.0, "fuel_moisture_pct": 18.0,
            "latitude": 18.2500, "longitude": 78.6500
        },
        "CRITICAL_FIRE": {
            "node_id": "NODE_FIRE_01", "timestamp": ts,
            "thermal_temp_c": 92.0, "pm25_ugm3": 280.0, "ambient_temp_c": 42.0,
            "humidity_pct": 12.0, "wind_speed_ms": 22.0, "co2_ppm": 950.0, "fuel_moisture_pct": 6.0,
            "latitude": 18.2500, "longitude": 78.6500
        }
    }
    
    if scenario not in scenarios:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario}'")
        
    payload = scenarios[scenario]
    
    # Check if fire scenario
    if scenario in ["NORMAL_FOREST", "SMOKE_WARNING", "CRITICAL_FIRE"]:
        res = predict_fire(FireSensorPayload(**payload))
        return {"simulation": scenario, "response": res}
        
    # Predict flood
    if scenario == "SENSOR_FAILURE":
        try:
            val = validate_sensor_payload(payload)
            if val["status"] == "ERROR":
                return {
                    "simulation": scenario,
                    "status": "FAILSAFE_TRIGGERED",
                    "detected_issues": val["issues"]
                }
        except Exception as e:
            return {"simulation": scenario, "status": "FAILSAFE_TRIGGERED", "error": str(e)}
            
    res = predict_flood(SensorPayload(**payload))
    return {"simulation": scenario, "response": res}


# Mount Static Files for Dashboard
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ECO DEFENDERS API active. Dashboard static files pending."}
