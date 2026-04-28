"""Unit tests for trader_advice.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'function'))

from trader_advice import generate_trader_advice


def test_generate_trader_advice_neutral():
    pressure = {
        'dominant_signal': 'NEUTRAL',
        'intensity': 'LOW',
        'price_change_pct': 0.0,
        'ci_width_pct': 5.0,
        'glut_score': 0,
        'shortage_score': 0,
        'top_driving_feature': 'price_momentum',
    }
    result = generate_trader_advice(pressure)
    assert 'headline' in result
    assert 'full_advice' in result
    assert result['dominant_signal'] == 'NEUTRAL'
    assert result['intensity'] == 'LOW'


def test_generate_trader_advice_shortage():
    pressure = {
        'dominant_signal': 'SHORTAGE',
        'intensity': 'HIGH',
        'price_change_pct': 8.5,
        'ci_width_pct': 12.0,
        'glut_score': 10,
        'shortage_score': 75,
        'top_driving_feature': 'production_signal',
    }
    result = generate_trader_advice(pressure)
    assert 'Kekurangan' in result['headline'] or 'SHORTAGE' not in result['headline']
    assert 'produksi padi' in result['full_advice'] or 'Faktor utama' in result['full_advice']
