# =============================================================================
# function/supply_pressure_scorer.py
# Converts Prophet forecast output → supply pressure signal dict.
# Mirrors the scoring logic used in the backtest notebook exactly.
# =============================================================================
 
import pandas as pd
 
 
def compute_supply_pressure(
    forecast_df: pd.DataFrame,
    current_price: float,
) -> dict:
    """
    Parameters:
        forecast_df   : Prophet .predict() output — future-only slice (next N months)
        current_price : Latest actual price (IDR/kg) from PIHPS/master_df
 
    Returns full signal dict consumed by function_app.py and the dashboard.
    """
    if len(forecast_df) == 0 or current_price <= 0:
        return _neutral_signal()
 
    last_yhat        = float(forecast_df["yhat"].iloc[-1])
    price_change_pct = (last_yhat - current_price) / current_price
 
    # Seasonal context from forecast dates
    future_months = forecast_df["ds"].dt.month
    harvest_near  = int(future_months.isin([3, 4, 5, 7, 8, 9]).sum() >= 2)
    lean_near     = int(future_months.isin([10, 11, 12, 1, 2]).sum() >= 2)
 
    # CI width as uncertainty measure (% of current price)
    ci_width_pct = float(
        ((forecast_df["yhat_upper"] - forecast_df["yhat_lower"]) / current_price)
        .mean() * 100
    )
 
    # ── Glut score ────────────────────────────────────────────────────────
    # High when: price falling + harvest season approaching
    glut_score  = max(0.0, -price_change_pct * 300)
    glut_score += 25 if harvest_near else 0
    glut_score  = min(100.0, round(glut_score, 1))
 
    # ── Shortage score ────────────────────────────────────────────────────
    # High when: price rising + lean season approaching
    shortage_score  = max(0.0, price_change_pct * 300)
    shortage_score += 20 if lean_near else 0
    shortage_score  = min(100.0, round(shortage_score, 1))
 
    # ── Dominant signal ───────────────────────────────────────────────────
    if glut_score > shortage_score and glut_score >= 20:
        dominant = "GLUT"
    elif shortage_score > glut_score and shortage_score >= 20:
        dominant = "SHORTAGE"
    else:
        dominant = "NEUTRAL"
 
    # ── Intensity ─────────────────────────────────────────────────────────
    peak      = max(glut_score, shortage_score)
    intensity = "HIGH" if peak >= 70 else "MEDIUM" if peak >= 40 else "LOW"
 
    return {
        "dominant_signal":  dominant,
        "intensity":        intensity,
        "glut_score":       int(glut_score),
        "shortage_score":   int(shortage_score),
        "ci_width_pct":     round(ci_width_pct, 1),
        "price_change_pct": round(price_change_pct * 100, 1),
        "forecast_values":  forecast_df["yhat"].round(0).astype(int).tolist(),
        "ci_lower":         forecast_df["yhat_lower"].round(0).astype(int).tolist(),
        "ci_upper":         forecast_df["yhat_upper"].round(0).astype(int).tolist(),
        "forecast_dates":   forecast_df["ds"].dt.strftime("%Y-%m-%d").tolist(),
    }
 
 
def _neutral_signal() -> dict:
    return {
        "dominant_signal":  "NEUTRAL",
        "intensity":        "LOW",
        "glut_score":       0,
        "shortage_score":   0,
        "ci_width_pct":     0.0,
        "price_change_pct": 0.0,
        "forecast_values":  [],
        "ci_lower":         [],
        "ci_upper":         [],
        "forecast_dates":   [],
    }