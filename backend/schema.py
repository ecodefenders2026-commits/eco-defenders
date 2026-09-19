"""
ECO DEFENDERS - API Schema Contracts (Pydantic Models)
---------------------------------------------------
Defines stable versioned API request/response JSON contracts for real-time
IoT sensor telemetry ingestion, flood inference, and hazard reporting.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SensorPayload(BaseModel):
    node_id: str = Field(..., example="NODE_017")
    timestamp: str = Field(..., example="2026-09-17T19:30:00+05:30")
    rainfall_mm: float = Field(..., example=32.4)
    water_level_m: float = Field(..., example=4.72)
    river_flow: float = Field(..., example=185.3)
    soil_moisture: float = Field(..., example=68.2)
    dam_water_level_m: Optional[float] = Field(25.0, example=18.4)
    dam_capacity: Optional[float] = Field(35.0, example=25.0)
    temperature: float = Field(..., example=28.5)
    humidity: float = Field(..., example=81.0)
    pressure: float = Field(..., example=1004.2)
    wind_speed: float = Field(..., example=11.6)
    latitude: float = Field(..., example=18.1234)
    longitude: float = Field(..., example=78.5678)


class RiskFactor(BaseModel):
    feature: str
    value: float
    importance: float


class SensorQualityStatus(BaseModel):
    status: str = Field(..., example="OK")  # OK, WARNING, ERROR
    issues: List[str] = Field(default_factory=list)


class PredictionDetails(BaseModel):
    risk_score: int = Field(..., example=87)
    flood_probability: float = Field(..., example=0.87)
    risk_category: str = Field(..., example="HIGH")  # VERY LOW, LOW, MODERATE, HIGH, CRITICAL
    severity: str = Field(..., example="SEVERE")      # MINIMAL, MODERATE, SEVERE, EXTREME
    warning_required: bool = Field(..., example=True)
    estimated_time_to_threshold_minutes: Optional[int] = Field(None, example=42)
    danger_threshold_m: Optional[float] = Field(5.0, example=5.0)
    dam_capacity_m: Optional[float] = Field(25.0, example=25.0)
    primary_hazard: str = Field("FLOOD", example="FLOOD")
    secondary_hazard: Optional[str] = Field("FLASH_FLOOD", example="FLASH_FLOOD")
    confidence: float = Field(..., example=0.91)
    top_risk_factors: List[RiskFactor] = Field(default_factory=list)


class LocationDetails(BaseModel):
    node_id: str = Field(..., example="NODE_017")
    latitude: float = Field(..., example=18.1234)
    longitude: float = Field(..., example=78.5678)


class ModelDetails(BaseModel):
    name: str = Field("xgboost_flood", example="xgboost_flood")
    version: str = Field("1.0.0", example="1.0.0")


class PredictionResponse(BaseModel):
    status: str = Field("success", example="success")
    prediction: PredictionDetails
    location: LocationDetails
    sensor_quality: SensorQualityStatus
    model: ModelDetails
    timestamp: str = Field(..., example="2026-09-17T19:30:00+05:30")


class MultiHazardResponse(BaseModel):
    hazard: str = Field(..., example="FLOOD")
    risk_score: int = Field(..., example=87)
    severity: str = Field(..., example="SEVERE")
    confidence: float = Field(..., example=0.91)
    timestamp: str


class FireSensorPayload(BaseModel):
    node_id: str = Field("NODE_FIRE_01", example="NODE_FIRE_01")
    timestamp: str = Field(..., example="2026-09-18T00:30:00+05:30")
    thermal_temp_c: float = Field(..., example=68.5)
    pm25_ugm3: float = Field(..., example=135.0)
    ambient_temp_c: Optional[float] = Field(32.0, example=32.0)
    humidity_pct: Optional[float] = Field(22.0, example=22.0)
    wind_speed_ms: Optional[float] = Field(12.5, example=12.5)
    co2_ppm: Optional[float] = Field(520.0, example=520.0)
    fuel_moisture_pct: Optional[float] = Field(12.0, example=12.0)
    latitude: Optional[float] = Field(18.2500, example=18.2500)
    longitude: Optional[float] = Field(78.6500, example=78.6500)


class FirePredictionDetails(BaseModel):
    risk_score: int = Field(..., example=85)
    fire_probability: float = Field(..., example=0.85)
    risk_category: str = Field(..., example="HIGH")
    severity: str = Field(..., example="SEVERE")
    warning_required: bool = Field(..., example=True)
    thermal_danger_threshold_c: float = Field(65.0, example=65.0)
    pm25_danger_threshold_ugm3: float = Field(120.0, example=120.0)
    estimated_time_to_threshold_minutes: Optional[int] = Field(None, example=35)
    primary_hazard: str = Field("FOREST_FIRE", example="FOREST_FIRE")
    secondary_hazard: Optional[str] = Field(None, example="HAZARDOUS_SMOKE_PLUME")
    confidence: float = Field(..., example=0.92)
    top_risk_factors: List[RiskFactor] = Field(default_factory=list)


class FirePredictionResponse(BaseModel):
    status: str = Field("success", example="success")
    prediction: FirePredictionDetails
    location: LocationDetails
    sensor_quality: SensorQualityStatus
    model: ModelDetails
    timestamp: str = Field(..., example="2026-09-18T00:30:00+05:30")

