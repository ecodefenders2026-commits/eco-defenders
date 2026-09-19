"""
Test script for model stability, monotonicity, and continuous risk scaling across 3.0m - 5.0m
"""
import pytest
from backend.inference import run_flood_inference


def test_monotonic_and_smooth_risk_scaling():
    water_levels = [3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.2, 4.4, 4.6, 4.85, 5.0, 5.2]
    prev_prob = -1.0
    scores = []
    
    for wl in water_levels:
        payload = {
            "node_id": "NODE_017",
            "timestamp": "2026-09-17T19:30:00+05:30",
            "rainfall_mm": 38.5,
            "water_level_m": wl,
            "river_flow": 14.0 * (wl ** 1.67),
            "soil_moisture": 78.0,
            "dam_water_level_m": 22.5,
            "dam_capacity": 25.0,
            "temperature": 25.0,
            "humidity": 80.0,
            "pressure": 1002.0,
            "wind_speed": 14.2,
            "latitude": 18.1234,
            "longitude": 78.5678
        }
        res = run_flood_inference(payload, {"status": "OK"})
        prob = res["flood_probability"]
        score = res["risk_score"]
        scores.append((wl, score, prob))
        
        # Risk must be strictly non-decreasing with water level
        assert prob >= prev_prob - 1e-4, f"Monotonicity violation at {wl}m: {prob} < {prev_prob}"
        prev_prob = prob
        
    print("\n[VERIFICATION RESULTS]")
    for wl, score, prob in scores:
        print(f"WL: {wl:4.2f}m -> Risk Score: {score:3d}/100 (Probability: {prob:.4f})")
        
    # At 3.0m, risk should not be extreme (must be < 70)
    assert scores[0][1] < 70, f"Risk at 3.0m should not be extreme: {scores[0][1]}"
    # At 5.0m, danger stage is breached, risk must be >= 90
    assert scores[-2][1] >= 90, f"Risk at 5.0m danger stage must be >= 90: {scores[-2][1]}"


if __name__ == "__main__":
    test_monotonic_and_smooth_risk_scaling()
