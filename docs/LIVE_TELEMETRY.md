# ECO DEFENDERS — Live Telemetry Contract

The dashboard is now output-only. Sensor values are no longer entered in the browser.

## Data flow

```text
Sensor / Simulator / ESP32 Gateway
            |
            | POST JSON
            v
/api/v1/telemetry
            |
            v
Validation -> XGBoost -> Database
            |
            v
/api/v1/nodes?live_only=true
            |
            v
Read-only Dashboard
```

## Live ingestion endpoint

`POST /api/v1/telemetry`

Every packet must include `hazard_type`, `node_id`, and `timestamp`.
The `node_id` is preserved through inference, database storage, and dashboard output.

### Flood example

```json
{
  "hazard_type": "FLOOD",
  "node_id": "NODE_FLOOD_07",
  "timestamp": "2026-09-19T11:30:00+05:30",
  "latitude": 18.1234,
  "longitude": 78.5678,
  "rainfall_mm": 38.5,
  "water_level_m": 4.85,
  "river_flow": 190.0,
  "soil_moisture": 78.0,
  "dam_water_level_m": 22.5,
  "dam_capacity": 25.0,
  "temperature": 25.0,
  "humidity": 80.0,
  "pressure": 1002.0,
  "wind_speed": 14.2
}
```

### Forest-fire example

```json
{
  "hazard_type": "FOREST_FIRE",
  "node_id": "NODE_FIRE_09",
  "timestamp": "2026-09-19T11:31:00+05:30",
  "latitude": 18.2500,
  "longitude": 78.6500,
  "thermal_temp_c": 92.0,
  "pm25_ugm3": 280.0,
  "ambient_temp_c": 42.0,
  "humidity_pct": 12.0,
  "wind_speed_ms": 22.0,
  "co2_ppm": 950.0,
  "fuel_moisture_pct": 6.0
}
```

## Dashboard polling

The browser polls `/api/v1/nodes?live_only=true` every 2 seconds.
Nodes are considered live when the server received a prediction within the last 60 seconds.
The browser never posts sensor values in live mode.

## Compatibility

The existing `/api/v1/predict/flood`, `/api/v1/predict/fire`, and `/api/v1/simulate` endpoints remain available for testing and development.
