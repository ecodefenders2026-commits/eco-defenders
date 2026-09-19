"""
ECO DEFENDERS - Hydrological Physics Engine
------------------------------------------
Calculates deterministic water-level rate of change (dL/dt) and physics-based
estimated time-to-threshold (TTT) until flood stage is breached.
"""

from typing import Optional, Dict

NODE_THRESHOLDS = {
    "NODE_001": 5.0,
    "NODE_002": 5.5,
    "NODE_003": 4.8,
    "NODE_004": 6.2,
    "NODE_005": 5.2,
}


def calculate_time_to_threshold(
    node_id: str,
    current_water_level: float,
    rate_per_hour: float,
    sensor_quality_status: str = "OK"
) -> Optional[int]:
    """
    Computes deterministic time to breach flood threshold in minutes.
    
    Formula:
      T_thresh = Danger Threshold stage (m)
      dL/dt    = Water level rate of rise (m/hr)
      Time (min) = ((T_thresh - current_water_level) / dL/dt) * 60
    """
    if sensor_quality_status == "ERROR":
        return None
        
    threshold = NODE_THRESHOLDS.get(node_id, 5.0)
    
    # If already at or above threshold
    if current_water_level >= threshold:
        return 0
        
    # If water level is not rising or rate is negligible/negative
    if rate_per_hour <= 0.05:
        return None
        
    remaining_height = threshold - current_water_level
    time_hours = remaining_height / rate_per_hour
    time_minutes = int(round(time_hours * 60))
    
    # Cap realistic horizon (max 12 hours / 720 minutes)
    if time_minutes > 720:
        return None
        
    return max(1, time_minutes)
