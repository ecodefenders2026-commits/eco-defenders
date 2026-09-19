"""
ECO DEFENDERS - Data Engineering & Preprocessing Pipeline
-------------------------------------------------------
Fetches/generates raw multi-node IoT hydrological and meteorological time-series data,
performs quality checks, standardizes units, constructs rolling temporal features
(zero target leakage), formulates future horizon flood target, and saves processed datasets.
"""

import os
import sys
import math
import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "raw", "hydro_sensor_raw.csv")
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "processed", "flood_timeseries_engineered.csv")

# Flood Danger Stage Thresholds per Node (meters)
NODE_THRESHOLDS = {
    "NODE_001": 5.0,
    "NODE_002": 5.5,
    "NODE_003": 4.8,
    "NODE_004": 6.2,
    "NODE_005": 5.2,
}

NODE_METADATA = {
    "NODE_001": {"lat": 18.1234, "lon": 78.5678, "dam_cap": 25.0},
    "NODE_002": {"lat": 18.2345, "lon": 78.6789, "dam_cap": 30.0},
    "NODE_003": {"lat": 18.3456, "lon": 78.7890, "dam_cap": 20.0},
    "NODE_004": {"lat": 18.4567, "lon": 78.8901, "dam_cap": 35.0},
    "NODE_005": {"lat": 18.5678, "lon": 78.9012, "dam_cap": 22.0},
}


def generate_realistic_hydrological_dataset(num_days=90, interval_minutes=15):
    """
    Generates a high-fidelity multi-node hydrological time-series dataset based on 
    rainfall-runoff physics (unit hydrograph principles and water balance equations).
    Includes monsoon storm pulses, river level surges, soil moisture dynamics, and dam releases.
    """
    os.makedirs(os.path.join(DATA_DIR, "raw"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "processed"), exist_ok=True)
    
    np.random.seed(42)
    start_time = pd.Timestamp("2026-06-01 00:00:00")
    total_steps = (num_days * 24 * 60) // interval_minutes
    timestamps = pd.date_range(start=start_time, periods=total_steps, freq=f"{interval_minutes}min")
    
    records = []
    
    for node_id, meta in NODE_METADATA.items():
        base_stage = 1.5 + np.random.uniform(-0.2, 0.2)
        water_level = base_stage
        soil_moisture = 35.0
        dam_water_level = meta["dam_cap"] * 0.45
        runoff_buffer = [0.0] * 8  # Hydrograph lag filter
        
        # Simulate storm pulses throughout 90 days monsoon period
        storm_days = np.array([5, 12, 18, 27, 34, 45, 52, 60, 71, 80, 85])
        storm_intensity = np.array([30, 50, 70, 90, 45, 110, 130, 60, 85, 150, 75]) # mm/hr peak
        
        for i, ts in enumerate(timestamps):
            day_idx = i * interval_minutes / (24 * 60)
            
            # Check storm activity
            rain_rate = 0.0
            for s_day, s_int in zip(storm_days, storm_intensity):
                dist = abs(day_idx - s_day)
                if dist < 1.5:  # storm lasts ~3 days with peak at s_day
                    rain_rate += s_int * math.exp(-((dist / 0.4) ** 2)) * np.random.uniform(0.8, 1.2)
            
            # Diurnal temperature/humidity cycle
            hour = ts.hour
            temp = 28.0 + 5.0 * math.sin((hour - 8) * math.pi / 12) + np.random.normal(0, 0.5)
            humidity = 75.0 - 15.0 * math.sin((hour - 8) * math.pi / 12) + (rain_rate * 0.15)
            humidity = min(100.0, max(30.0, humidity))
            pressure = 1012.0 - (rain_rate * 0.1) + np.random.normal(0, 0.5)
            wind_speed = 5.0 + (rain_rate * 0.08) + np.random.exponential(1.5)
            
            # Convert rain rate (mm/hr) to 15-min interval mm rainfall
            rainfall_mm = max(0.0, (rain_rate / 4.0) + np.random.normal(0, 0.05) if rain_rate > 0.5 else 0.0)
            rainfall_mm = round(rainfall_mm, 2)
            
            # Soil moisture infiltration dynamics (saturation limit 95%)
            soil_moisture += (rainfall_mm * 0.4) - 0.12  # gradual infiltration - evaporation
            soil_moisture = min(98.0, max(20.0, soil_moisture))
            
            # Non-linear runoff coefficient dependent on soil saturation
            runoff_factor = 0.05 + 0.55 * ((max(0.0, soil_moisture - 40.0) / 58.0) ** 1.5)
            instant_runoff = rainfall_mm * runoff_factor
            
            # Unit hydrograph lag filter (realistic basin delay)
            runoff_buffer.pop(0)
            runoff_buffer.append(instant_runoff)
            routed_runoff = sum(w * r for w, r in zip([0.05, 0.08, 0.12, 0.15, 0.25, 0.20, 0.10, 0.05], runoff_buffer))
            
            # River level hydrograph response (realistic rate: max ~0.3 - 0.6 m/hr rise in storms)
            stage_rise = routed_runoff * 0.025
            stage_fall = (water_level - base_stage) * 0.02  # base recession
            water_level += stage_rise - stage_fall + np.random.normal(0, 0.01)
            water_level = max(0.5, water_level)
            
            # River flow rating curve Q = k * h^1.67
            river_flow = 14.0 * (water_level ** 1.67) + np.random.normal(0, 0.5)
            river_flow = max(2.0, river_flow)
            
            # Dam water level dynamics
            dam_inflow = routed_runoff * 0.8
            dam_water_level += (dam_inflow * 0.02) - 0.01
            dam_water_level = min(meta["dam_cap"], max(5.0, dam_water_level))
            
            records.append({
                "node_id": node_id,
                "timestamp": ts.isoformat(),
                "rainfall_mm": round(rainfall_mm, 2),
                "water_level_m": round(water_level, 2),
                "river_flow": round(river_flow, 2),
                "soil_moisture": round(soil_moisture, 2),
                "dam_water_level_m": round(dam_water_level, 2),
                "dam_capacity": meta["dam_cap"],
                "temperature": round(temp, 2),
                "humidity": round(humidity, 2),
                "pressure": round(pressure, 2),
                "wind_speed": round(wind_speed, 2),
                "latitude": meta["lat"],
                "longitude": meta["lon"]
            })
            
    df = pd.DataFrame(records)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"[OK] Real-time raw hydrological dataset generated with {len(df)} records at {RAW_DATA_PATH}")
    return df


def preprocess_and_engineer_features(raw_df=None, horizon_steps=4):
    """
    Processes raw sensor readings, standardizes columns, handles invalid sensor values,
    generates rolling window temporal features, and formulates the prediction target.
    
    horizon_steps: 4 steps * 15 min = 60 minute prediction horizon.
    """
    if raw_df is None:
        if not os.path.exists(RAW_DATA_PATH):
            raw_df = generate_realistic_hydrological_dataset()
        else:
            raw_df = pd.read_csv(RAW_DATA_PATH)
            
    df = raw_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by=["node_id", "timestamp"]).reset_index(drop=True)
    
    # 1. Cleaning & Quality Checks
    # Remove impossible values
    df.loc[df["rainfall_mm"] < 0, "rainfall_mm"] = 0.0
    df.loc[df["water_level_m"] < 0, "water_level_m"] = 0.0
    df.loc[df["soil_moisture"] < 0, "soil_moisture"] = 0.0
    df.loc[df["soil_moisture"] > 100, "soil_moisture"] = 100.0
    
    processed_nodes = []
    
    for node_id, group in df.groupby("node_id"):
        g = group.copy().sort_values("timestamp")
        
        # 2. Rolling Rain Accumulations
        g["rainfall_15m"] = g["rainfall_mm"]
        g["rainfall_30m"] = g["rainfall_mm"].rolling(window=2, min_periods=1).sum()
        g["rainfall_1h"] = g["rainfall_mm"].rolling(window=4, min_periods=1).sum()
        g["rainfall_3h"] = g["rainfall_mm"].rolling(window=12, min_periods=1).sum()
        g["rainfall_6h"] = g["rainfall_mm"].rolling(window=24, min_periods=1).sum()
        
        # 3. Water Level Rate of Change (dL/dt in meters per hour)
        g["water_level_change_15m"] = g["water_level_m"].diff().fillna(0.0)
        g["water_level_rate_per_hour"] = g["water_level_change_15m"] * 4.0
        g["water_level_max_3h"] = g["water_level_m"].rolling(window=12, min_periods=1).max()
        g["water_level_mean_1h"] = g["water_level_m"].rolling(window=4, min_periods=1).mean()
        
        # 4. River Flow & Soil Moisture Dynamics
        g["river_flow_change_15m"] = g["river_flow"].diff().fillna(0.0)
        g["soil_moisture_trend_1h"] = g["soil_moisture"].diff(4).fillna(0.0)
        
        # 5. Pressure & Temp Changes
        g["pressure_change_3h"] = g["pressure"].diff(12).fillna(0.0)
        g["temp_change_1h"] = g["temperature"].diff(4).fillna(0.0)
        
        # 6. Temporal cyclical features
        g["hour_of_day"] = g["timestamp"].dt.hour
        g["day_of_year"] = g["timestamp"].dt.dayofyear
        
        # 7. Dam capacity ratio
        g["dam_fill_ratio"] = g["dam_water_level_m"] / g["dam_capacity"]
        
        # 8. ML Target Formulation (Zero Temporal Leakage)
        # Target: Will water level exceed node danger threshold within 60 minutes (horizon_steps=4)?
        danger_threshold = NODE_THRESHOLDS.get(node_id, 5.0)
        g["future_max_water_level_60m"] = g["water_level_m"].shift(-horizon_steps).rolling(window=horizon_steps, min_periods=1).max()
        g["flood_target_60m"] = (g["future_max_water_level_60m"] >= danger_threshold).astype(int)
        
        # Drop rows where target is NaN due to end-of-series shift
        g = g.dropna(subset=["flood_target_60m"]).copy()
        processed_nodes.append(g)
        
    final_df = pd.concat(processed_nodes, ignore_index=True)
    
    # 9. Augment with Continuous Synthetic Boundary Condition Samples
    # Fills sparse hydrological transition spaces (e.g. high rain with low stage, high stage with low rain)
    boundary_df = generate_boundary_condition_samples(n_samples=6000)
    final_df = pd.concat([final_df, boundary_df], ignore_index=True)
    
    final_df.to_csv(PROCESSED_DATA_PATH, index=False)
    
    print(f"[OK] Processed dataset with {len(final_df)} rows and temporal features saved to {PROCESSED_DATA_PATH}")
    print(f"     Class Balance: {final_df['flood_target_60m'].value_counts(normalize=True).to_dict()}")
    return final_df


def generate_boundary_condition_samples(n_samples: int = 6000) -> pd.DataFrame:
    """
    Generates synthetic boundary condition hydrological samples to guarantee continuous,
    physically-sound risk progression across the 3.0m - 5.5m transition zone.
    Prevents decision tree threshold over-sensitivity and spurious feature interactions.
    """
    np.random.seed(42)
    records = []
    
    base_ts = pd.Timestamp("2026-07-15 12:00:00")
    
    for i in range(n_samples):
        # Sample across full spectrum with focus on 2.5m - 5.5m transition zone
        if i % 3 == 0:
            water_level = np.random.uniform(3.0, 5.2)  # Focus on transition boundary
        elif i % 3 == 1:
            water_level = np.random.uniform(1.0, 3.0)  # Low stage
        else:
            water_level = np.random.uniform(4.5, 6.2)  # High stage / breach
            
        threshold = 5.0
        soil = np.random.uniform(25.0, 98.0)
        rain = np.random.uniform(0.0, 60.0)
        
        # Rate of rise: correlated with rain and soil saturation, but with realistic noise
        runoff_potential = (rain / 4.0) * (0.1 + 0.6 * (soil / 100.0))
        rate_per_hour = max(-0.2, min(1.2, (runoff_potential * 0.15) - 0.05 + np.random.normal(0, 0.05)))
        
        flow = max(5.0, 14.0 * (water_level ** 1.67) + np.random.normal(0, 2.0))
        dam_cap = 25.0
        dam_water = min(dam_cap, max(5.0, 12.0 + (water_level * 1.8) + np.random.normal(0, 1.0)))
        dam_fill = dam_water / dam_cap
        
        rain_15m = rain
        rain_30m = rain * np.random.uniform(1.2, 1.8)
        rain_1h = rain * np.random.uniform(2.0, 3.2)
        rain_3h = rain_1h * np.random.uniform(1.4, 2.2)
        rain_6h = rain_3h * np.random.uniform(1.2, 1.8)
        
        water_change_15m = rate_per_hour / 4.0
        water_max_3h = max(water_level, water_level - rate_per_hour * np.random.uniform(0, 1.0))
        water_mean_1h = max(0.5, water_level - (rate_per_hour * 0.5))
        
        # Physics-based projected 60-minute water level
        projected_rise_60m = (rate_per_hour * 1.0) + (rain_1h * 0.005 * (soil / 100.0))
        future_water_60m = water_level + projected_rise_60m
        
        # Smooth sigmoid probability of exceeding danger threshold (5.0m)
        effective_stage = max(water_level, future_water_60m)
        prob = 1.0 / (1.0 + np.exp(-2.8 * (effective_stage - 4.65)))
        target = 1 if (np.random.uniform(0.0, 1.0) < prob) else 0
        
        records.append({
            "node_id": "NODE_001",
            "timestamp": (base_ts + pd.Timedelta(minutes=i * 15)).isoformat(),
            "rainfall_mm": round(rain, 2),
            "water_level_m": round(water_level, 3),
            "river_flow": round(flow, 2),
            "soil_moisture": round(soil, 2),
            "dam_water_level_m": round(dam_water, 2),
            "dam_capacity": dam_cap,
            "temperature": round(25.0 + np.random.normal(0, 2.0), 2),
            "humidity": round(min(100.0, max(40.0, 70.0 + (soil * 0.2))), 2),
            "pressure": round(1010.0 - (rain * 0.15) + np.random.normal(0, 1.0), 2),
            "wind_speed": round(max(1.0, 5.0 + (rain * 0.1) + np.random.exponential(1.5)), 2),
            "latitude": 18.1234,
            "longitude": 78.5678,
            "rainfall_15m": round(rain_15m, 2),
            "rainfall_30m": round(rain_30m, 2),
            "rainfall_1h": round(rain_1h, 2),
            "rainfall_3h": round(rain_3h, 2),
            "rainfall_6h": round(rain_6h, 2),
            "water_level_change_15m": round(water_change_15m, 3),
            "water_level_rate_per_hour": round(rate_per_hour, 3),
            "water_level_max_3h": round(water_max_3h, 3),
            "water_level_mean_1h": round(water_mean_1h, 3),
            "river_flow_change_15m": round(water_change_15m * 8.0, 2),
            "soil_moisture_trend_1h": round((rain_1h * 0.2) - 0.1, 2),
            "pressure_change_3h": round(-rain_1h * 0.04, 2),
            "temp_change_1h": round(-rain_1h * 0.02, 2),
            "hour_of_day": (i % 24),
            "day_of_year": 180 + (i // 96),
            "dam_fill_ratio": round(dam_fill, 3),
            "future_max_water_level_60m": round(future_water_60m, 3),
            "flood_target_60m": target
        })
        
    return pd.DataFrame(records)


if __name__ == "__main__":
    df_raw = generate_realistic_hydrological_dataset()
    preprocess_and_engineer_features(df_raw)
