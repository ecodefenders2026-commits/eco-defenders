# ECO DEFENDERS — Technical System Architecture

## Architecture Overview

ECO DEFENDERS employs a hybrid machine-learning and deterministic hydrological inference pipeline designed for low-latency emergency disaster response.

```
[IoT Smart Sensor Nodes / Simulators]
            │
            ▼ (POST /api/v1/predict/flood)
┌────────────────────────────────────────────────────────┐
│  FastAPI Inference Server                              │
│  ├── 1. Sensor Quality & Failsafe Layer (Validator)    │
│  ├── 2. Feature Transformer (Rolling Windows / Diffs)  │
│  ├── 3. XGBoost Classification Engine (Prob & Risk)    │
│  ├── 4. Time-to-Threshold Hydrological Engine          │
│  ├── 5. Explainability Engine (Feature Importances)    │
│  └── 6. Multi-Hazard Extensibility Contract Builder   │
└──────────────────────────┬─────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
  ┌─────────────────┐             ┌────────────────────┐
  │ SQLite Database │ ◄───────────┤ Web Dashboard UI   │
  │ (Readings,      │  (Polling/  │ (Interactive Map,  │
  │  Predictions,   │   REST API) │  Risk Gauge,       │
  │  Alerts)        │             │  Alert Banner,     │
  └─────────────────┘             │  Scenario Tester)  │
                                  └────────────────────┘
```

---

## Key Subsystems

### 1. IoT Telemetry Layer
Captures sensor parameters:
- `rainfall_mm`
- `water_level_m`
- `river_flow`
- `soil_moisture`
- `dam_water_level_m`, `dam_capacity`
- `temperature`, `humidity`, `pressure`, `wind_speed`
- `latitude`, `longitude`, `node_id`, `timestamp`

### 2. Sensor Quality & Failsafe Layer (`backend/validator.py`)
- Detects physical bounds violations (negative rain, out-of-bound coordinates, extreme pressure).
- Detects sensor freeze conditions (unchanging water level for > 4 consecutive readings).
- Detects impossible physical spikes ($>3.0m$ change in consecutive steps).
- Emits quality status: `OK`, `WARNING`, or `ERROR` (triggering failsafe rejection).

### 3. Machine Learning Inference Engine (`backend/inference.py`)
- Loaded XGBoost model (`models/xgboost_flood_v1.json`).
- Evaluates statistical probability of flood threshold breach within 60 minutes.
- Maps probability $P \in [0, 1]$ to normalized 0–100 Risk Score.
- Categorizes risk levels:
  - `0–20`: VERY LOW (MINIMAL)
  - `21–40`: LOW (MODERATE)
  - `41–60`: MODERATE (MODERATE)
  - `61–80`: HIGH (SEVERE)
  - `81–100`: CRITICAL (EXTREME)

### 4. Hydrological Time-to-Threshold Engine (`backend/hydrological.py`)
- Deterministic calculation of water level rate of rise ($dL/dt$ in $m/hr$).
- Computes estimated time to threshold breach:
  $$\text{Time (min)} = \left(\frac{L_{\text{danger}} - L_{\text{current}}}{dL/dt}\right) \times 60$$
- Returned only when $dL/dt > 0.05\text{ m/hr}$ and sensor quality is acceptable.

### 5. Multi-Hazard Extensibility Contract
Standardized hazard output allows seamless addition of future hazard engines (Cyclone, Landslide, Forest Fire):
```json
{
  "hazard": "FLOOD",
  "risk_score": 87,
  "severity": "SEVERE",
  "confidence": 0.91
}
```

### 6. Interactive Live Web Dashboard (`static/`)
- Responsive glassmorphic UI built with HTML/CSS/JS and Chart.js.
- Real-time polling for node statuses, risk gauges, alert banners, top risk factors, and interactive scenario simulator.
