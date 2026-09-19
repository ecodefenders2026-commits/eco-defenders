# 🛡️ ECO DEFENDERS — AI-Enabled Multi-Hazard Early Warning & Emergency Response System

**ECO DEFENDERS** is a lightweight, real-time Machine Learning disaster intelligence pipeline that ingests IoT sensor node telemetry from river basins and dam catchments, performs fast server-side XGBoost inference, computes hydrological time-to-threshold dynamics, enforces sensor failsafe quality checks, and serves structured risk predictions directly to an interactive emergency dashboard.

---

## 🚀 Key Features

- **XGBoost Flood Intelligence Engine**: Predicts probability of river stage breaching dangerous flood thresholds within a 60-minute prediction horizon with 99.6% accuracy and 98.8% recall.
- **Sensor Quality & Failsafe Layer**: Automatically intercepts missing values, negative rainfall, physical level jumps, frozen sensors, and invalid coordinates before model execution.
- **Deterministic Hydrological Engine**: Physics-based $dL/dt$ calculation of estimated time-to-threshold ($TTT$) in minutes.
- **AI Explainability**: Provides top contributing risk factors (feature importance breakdowns) for every prediction.
- **Multi-Hazard Contract Compatibility**: Standardized JSON response contract extensible to future modules (Cyclone, Landslide, Forest Fire).
- **Interactive Live Dashboard**: Modern dark-mode web application featuring animated risk score gauges, live node cards, Chart.js time-series trend graphs, and alert banners.
- **Scenario Simulator & Demo Mode**: One-click prototype simulator triggering 6 preset disaster escalation states (`NORMAL`, `HEAVY_RAIN`, `RAPIDLY_RISING_WATER`, `FLOOD_WARNING`, `CRITICAL_FLOOD`, `SENSOR_FAILURE`).

---

## 📁 Repository Structure

```
eco/
├── data/                     # Raw and processed hydrological time-series CSVs & SQLite DB
├── models/                   # XGBoost model JSON, scaler PKL, schema, metadata
├── src/
│   ├── data_pipeline.py      # Hydrological data engineering & rolling feature generator
│   ├── train.py              # XGBoost training script & baseline model benchmarking
│   └── simulator.py          # Real-time IoT sensor telemetry simulator CLI
├── backend/
│   ├── app.py                # FastAPI server entry point & static file routing
│   ├── schema.py             # Pydantic API request/response JSON contracts
│   ├── validator.py          # Sensor quality validation & failsafe layer
│   ├── inference.py          # XGBoost prediction engine & feature explainer
│   ├── hydrological.py       # Deterministic time-to-threshold calculator
│   └── db.py                 # SQLite database integration
├── static/                   # Emergency Web Dashboard UI (HTML / CSS / JS)
├── tests/                    # Pytest unit and integration test suite
├── docs/                     # ARCHITECTURE, DATASETS, MODEL_CARD, API documentation
├── requirements.txt          # Python dependencies
└── run_demo.py               # One-click script to launch server, simulator & UI
```

---

## 🛠️ Quick Start

### 1. Installation
```bash
git clone https://github.com/eco-defenders/eco.git
cd eco
pip install -r requirements.txt
```

### 2. Train the Model Pipeline
```bash
python src/train.py
```

### 3. Run Automated Tests
```bash
python -m pytest tests/ -v
```

### 4. Launch One-Click Interactive Prototype Demo
```bash
python run_demo.py
```
This automatically starts the FastAPI inference server at `http://127.0.0.1:8000/`, seeds active node telemetry, and opens the live Emergency Response Dashboard in your default browser.

---

## ⚡ API Endpoint Example

### `POST /api/v1/predict/flood`
```json
{
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
```

#### Response:
```json
{
  "status": "success",
  "prediction": {
    "risk_score": 87,
    "flood_probability": 0.87,
    "risk_category": "HIGH",
    "severity": "SEVERE",
    "warning_required": true,
    "estimated_time_to_threshold_minutes": 42,
    "secondary_hazard": "FLASH_FLOOD"
  },
  "location": {
    "node_id": "NODE_017",
    "latitude": 18.1234,
    "longitude": 78.5678
  },
  "model": {
    "name": "xgboost_flood",
    "version": "1.0.0"
  },
  "timestamp": "2026-09-17T19:30:00+05:30"
}
```
