"""Unit tests for supply_pressure_scorer.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'function'))

import pandas as pd
from supply_pressure_scorer import compute_supply_pressure, score_to_intensity


def make_forecast(price_change_pct, harvest_window=0, lean_season=0,
                  production_dev=0.0, rainfall_dev=0.0, ci_width_abs=500):
    base_price = 12000
    yhat = base_price * (1 + price_change_pct)
    rows = []
    for _ in range(3):
        rows.append({
            'yhat': yhat,
            'yhat_lower': yhat - ci_width_abs,
            'yhat_upper': yhat + ci_width_abs,
            'harvest_window': harvest_window,
            'lean_season': lean_season,
            'production_dev_pct': production_dev,
            'rainfall_dev_pct': rainfall_dev,
        })
    return pd.DataFrame(rows)


def test_clear_glut_signal():
    fc = make_forecast(price_change_pct=-0.20, harvest_window=1, production_dev=0.15)
    result = compute_supply_pressure(fc, current_price=12000)
    assert result['dominant_signal'] == 'GLUT'
    assert result['intensity'] in ('MEDIUM', 'HIGH')


def test_clear_shortage_signal():
    fc = make_forecast(price_change_pct=0.20, lean_season=1, production_dev=-0.15)
    result = compute_supply_pressure(fc, current_price=12000)
    assert result['dominant_signal'] == 'SHORTAGE'
    assert result['intensity'] in ('MEDIUM', 'HIGH')


def test_neutral_stable_market():
    fc = make_forecast(price_change_pct=0.01)
    result = compute_supply_pressure(fc, current_price=12000)
    assert result['dominant_signal'] == 'NEUTRAL'
    assert result['intensity'] == 'LOW'


def test_score_thresholds():
    assert score_to_intensity(75) == 'HIGH'
    assert score_to_intensity(50) == 'MEDIUM'
    assert score_to_intensity(20) == 'LOW'


def test_output_keys():
    fc = make_forecast(price_change_pct=0.10)
    result = compute_supply_pressure(fc, current_price=12000)
    required = {'glut_score', 'shortage_score', 'dominant_signal',
                'intensity', 'price_change_pct', 'ci_width_pct'}
    assert required.issubset(result.keys())
