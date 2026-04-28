"""
supply_pressure_scorer.py

Converts a Prophet forecast dataframe into a supply pressure assessment
for UMKM rice traders at pasar induk level.

No LLM calls. No external APIs. Pure Python + pandas + numpy.
"""

import pandas as pd
import numpy as np
from typing import Dict

INTENSITY_THRESHOLDS = {
    'HIGH': 70,
    'MEDIUM': 40,
}


def score_to_intensity(score: float) -> str:
    if score >= INTENSITY_THRESHOLDS['HIGH']:
        return 'HIGH'
    elif score >= INTENSITY_THRESHOLDS['MEDIUM']:
        return 'MEDIUM'
    return 'LOW'


def _compute_glut_score(
    price_change_pct: float,
    harvest_window_sum: int,
    production_dev_mean: float,
    ci_width_pct: float,
) -> float:
    score = 0.0
    if price_change_pct < 0:
        score += min(50, abs(price_change_pct) * 300)
    if harvest_window_sum >= 2:
        score += 20
    elif harvest_window_sum == 1:
        score += 10
    if production_dev_mean > 0.10:
        score += 20
    elif production_dev_mean > 0.05:
        score += 10
    if ci_width_pct > 0.20:
        score *= 0.85
    return min(100.0, score)


def _compute_shortage_score(
    price_change_pct: float,
    lean_season_sum: int,
    production_dev_mean: float,
    rainfall_dev_mean: float,
    ci_width_pct: float,
) -> float:
    score = 0.0
    if price_change_pct > 0:
        score += min(50, abs(price_change_pct) * 300)
    if lean_season_sum >= 2:
        score += 20
    elif lean_season_sum == 1:
        score += 10
    if production_dev_mean < -0.10:
        score += 20
    elif production_dev_mean < -0.05:
        score += 10
    if rainfall_dev_mean < -0.25:
        score += 10
    elif rainfall_dev_mean < -0.10:
        score += 5
    if ci_width_pct > 0.20:
        score *= 0.85
    return min(100.0, score)


def compute_supply_pressure(
    forecast_df: pd.DataFrame,
    current_price: float,
    horizon_days: int = 30,
) -> Dict:
    future_fc = forecast_df.tail(max(1, horizon_days // 30))
    if len(future_fc) == 0:
        future_fc = forecast_df.tail(1)
    yhat_mean = future_fc['yhat'].mean()
    yhat_lower_mean = future_fc['yhat_lower'].mean()
    yhat_upper_mean = future_fc['yhat_upper'].mean()
    price_change_pct = (yhat_mean - current_price) / current_price
    ci_width_pct = (yhat_upper_mean - yhat_lower_mean) / current_price
    harvest_window_sum = int(future_fc.get('harvest_window', pd.Series([0])).sum())
    lean_season_sum = int(future_fc.get('lean_season', pd.Series([0])).sum())
    production_dev_mean = float(future_fc.get('production_dev_pct', pd.Series([0.0])).mean())
    rainfall_dev_mean = float(future_fc.get('rainfall_dev_pct', pd.Series([0.0])).mean())
    glut_score = _compute_glut_score(
        price_change_pct, harvest_window_sum, production_dev_mean, ci_width_pct
    )
    shortage_score = _compute_shortage_score(
        price_change_pct,
        lean_season_sum,
        production_dev_mean,
        rainfall_dev_mean,
        ci_width_pct,
    )
    if glut_score > shortage_score and glut_score >= INTENSITY_THRESHOLDS['MEDIUM']:
        dominant_signal = 'GLUT'
        active_score = glut_score
    elif shortage_score > glut_score and shortage_score >= INTENSITY_THRESHOLDS['MEDIUM']:
        dominant_signal = 'SHORTAGE'
        active_score = shortage_score
    else:
        dominant_signal = 'NEUTRAL'
        active_score = max(glut_score, shortage_score)
    intensity = score_to_intensity(active_score)
    feature_contributions = {
        'price_momentum': abs(price_change_pct) * 300,
        'harvest_timing': harvest_window_sum * 10,
        'production_signal': abs(production_dev_mean) * 100,
        'rainfall_deficit': max(0.0, -rainfall_dev_mean) * 30,
    }
    top_feature = max(feature_contributions, key=feature_contributions.get)
    return {
        'glut_score': round(glut_score),
        'shortage_score': round(shortage_score),
        'dominant_signal': dominant_signal,
        'intensity': intensity,
        'price_change_pct': round(price_change_pct * 100, 1),
        'ci_width_pct': round(ci_width_pct * 100, 1),
        'yhat_mean': round(yhat_mean),
        'top_driving_feature': top_feature,
        'driving_features': {k: round(v) for k, v in feature_contributions.items()},
    }
