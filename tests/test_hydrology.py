"""
Unit Tests for Hydrological Physics Engine & Time-To-Threshold Calculation
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.hydrological import calculate_time_to_threshold


def test_time_to_threshold_normal_rising():
    # Danger threshold for NODE_001 is 5.0m
    # Current water level 4.0m, rising at 0.5 m/hr -> (5.0 - 4.0)/0.5 = 2 hours = 120 min
    ttt = calculate_time_to_threshold("NODE_001", current_water_level=4.0, rate_per_hour=0.5)
    assert ttt == 120


def test_time_to_threshold_falling_or_stationary():
    # Negative or zero rate of rise -> None
    assert calculate_time_to_threshold("NODE_001", current_water_level=4.0, rate_per_hour=0.0) is None
    assert calculate_time_to_threshold("NODE_001", current_water_level=4.0, rate_per_hour=-0.2) is None


def test_time_to_threshold_already_flooded():
    # Water level >= threshold (5.0m) -> 0 minutes
    assert calculate_time_to_threshold("NODE_001", current_water_level=5.2, rate_per_hour=0.5) == 0
