# ECO DEFENDERS — API Specification v1.0.0

## Base URL
`http://localhost:8000/api/v1`

---

## Endpoints

### 1. Flood Risk Inference Endpoint
**`POST /api/v1/predict/flood`**

#### Request Payload
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

#### Success Response (`200 OK`)
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
    "primary_hazard": "FLOOD",
    "secondary_hazard": "FLASH_FLOOD",
    "confidence": 0.91,
    "top_risk_factors": [
      {
        "feature": "water_level_m",
        "value": 4.72,
        "importance": 0.45
      },
      {
        "feature": "rainfall_1h",
        "value": 32.4,
        "importance": 0.32
      }
    ]
  },
  "location": {
    "node_id": "NODE_017",
    "latitude": 18.1234,
    "longitude": 78.5678
  },
  "sensor_quality": {
    "status": "OK",
    "issues": []
  },
  "model": {
    "name": "xgboost_flood",
    "version": "1.0.0"
  },
  "timestamp": "2026-09-17T19:30:00+05:30"
}
```

#### Failsafe Error Response (`400 Bad Request`)
```json
{
  "detail": {
    "error": "Sensor Quality Failsafe Violation",
    "issues": [
      "Invalid latitude coordinate: 999.0"
    ]
  }
}
```

---

### 2. Active Nodes Status Endpoint
**`GET /api/v1/nodes`**

Returns array of active IoT nodes with latest telemetry, risk categories, and water levels.

---

### 3. Node Historical Telemetry Endpoint
**`GET /api/v1/history/{node_id}?limit=40`**

Returns time-series telemetry and prediction history for Chart.js dashboard visualization.

---

### 4. Scenario Simulator Endpoint
**`POST /api/v1/simulate?scenario=FLOOD_WARNING&node_id=NODE_001`**

Supported scenarios:
- `NORMAL`
- `HEAVY_RAIN`
- `RAPIDLY_RISING_WATER`
- `FLOOD_WARNING`
- `CRITICAL_FLOOD`
- `SENSOR_FAILURE`
