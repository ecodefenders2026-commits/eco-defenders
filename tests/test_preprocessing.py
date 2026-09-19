"""
Unit Tests for Data Preprocessing & Feature Engineering
"""

import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_pipeline import generate_realistic_hydrological_dataset, preprocess_and_engineer_features


def test_dataset_generation_and_preprocessing():
    df_raw = generate_realistic_hydrological_dataset(num_days=5, interval_minutes=15)
    assert len(df_raw) > 0
    assert "water_level_m" in df_raw.columns
    assert "rainfall_mm" in df_raw.columns
    
    df_processed = preprocess_and_engineer_features(df_raw)
    assert len(df_processed) > 0
    assert "rainfall_1h" in df_processed.columns
    assert "water_level_rate_per_hour" in df_processed.columns
    assert "flood_target_60m" in df_processed.columns
    assert df_processed["rainfall_1h"].isnull().sum() == 0
