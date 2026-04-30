import pandas as pd
import numpy as np
 
 
# ── 5-tier decision vocabulary (trader-facing) ────────────────────────────────
DECISION_MAP = {
    # (dominant, intensity) → decision key
    ("GLUT",     "HIGH"):   "JUAL_STOK",
    ("GLUT",     "MEDIUM"): "KURANGI",
    ("GLUT",     "LOW"):    "TAHAN",
    ("NEUTRAL",  "LOW"):    "BELI_NORMAL",
    ("SHORTAGE", "LOW"):    "BELI_NORMAL",
    ("SHORTAGE", "MEDIUM"): "BELI_BANYAK",
    ("SHORTAGE", "HIGH"):   "BELI_BANYAK",
}
 
DECISION_CONFIG = {
    "BELI_BANYAK":  {
        "label":       "BELI BANYAK",
        "consequence": "Pasokan kemungkinan menipis — amankan stok sekarang sebelum harga naik",
        "color":       "#065F46",
        "bg":          "#DCFCE7",
        "border":      "#6EE7B7",
    },
    "BELI_NORMAL":  {
        "label":       "BELI NORMAL",
        "consequence": "Kondisi stabil — lanjutkan pembelian stok seperti biasa",
        "color":       "#1D4ED8",
        "bg":          "#EFF6FF",
        "border":      "#93C5FD",
    },
    "TAHAN":        {
        "label":       "TAHAN DULU",
        "consequence": "Sinyal campuran — tunda pembelian besar, pantau harga 1–2 minggu",
        "color":       "#92400E",
        "bg":          "#FEF3C7",
        "border":      "#FCD34D",
    },
    "KURANGI":      {
        "label":       "KURANGI STOK",
        "consequence": "Pasokan mulai berlebih — kurangi pembelian dan jual stok lama lebih cepat",
        "color":       "#7C2D12",
        "bg":          "#FEF2F2",
        "border":      "#FCA5A5",
    },
    "JUAL_STOK":    {
        "label":       "JUAL STOK LAMA",
        "consequence": "Surplus pasokan tinggi — prioritaskan jual stok sebelum harga turun lebih jauh",
        "color":       "#7F1D1D",
        "bg":          "#FEE2E2",
        "border":      "#F87171",
    },
}
 
 
def compute_supply_pressure(
    forecast_df: pd.DataFrame,
    current_price: float,
    historical_prices: list | None = None,     # pass last 12–24 months of actual prices
) -> dict:
    """
    v2 changes:
    - z-score normalization using historical std (not arbitrary *300 multiplier)
    - confidence grounded in real price volatility, not raw CI width
    - returns decision key (5-tier) instead of abstract GLUT/SHORTAGE
    """
    if len(forecast_df) == 0 or current_price <= 0:
        return _neutral_signal()
 
    # ── Historical std for normalization ──────────────────────────────────────
    if historical_prices and len(historical_prices) >= 6:
        hist_std = float(np.std(historical_prices))
    else:
        hist_std = current_price * 0.08   # fallback: assume 8% typical volatility
 
    # ── Forecast signal ───────────────────────────────────────────────────────
    last_yhat        = float(forecast_df["yhat"].iloc[-1])
    price_change     = last_yhat - current_price
    z_score          = price_change / (hist_std + 1e-6)
 
    future_months    = forecast_df["ds"].dt.month
    harvest_near     = int(future_months.isin([3, 4, 5, 7, 8, 9]).sum() >= 2)
    lean_near        = int(future_months.isin([10, 11, 12, 1, 2]).sum() >= 2)
 
    # ── Scores (sigmoid-mapped, data-grounded) ────────────────────────────────
    glut_score     = max(0.0, min(100.0, 50 - z_score * 20 + (15 if harvest_near else 0)))
    shortage_score = max(0.0, min(100.0, 50 + z_score * 20 + (10 if lean_near else 0)))
 
    # ── Dominant signal ───────────────────────────────────────────────────────
    if glut_score > shortage_score and glut_score >= 55:
        dominant = "GLUT"
    elif shortage_score > glut_score and shortage_score >= 55:
        dominant = "SHORTAGE"
    else:
        dominant = "NEUTRAL"
 
    intensity = "HIGH" if max(glut_score, shortage_score) >= 75 else \
                "MEDIUM" if max(glut_score, shortage_score) >= 55 else "LOW"
 
    # ── Confidence: grounded in historical volatility, not raw CI ────────────
    raw_ci_width = float(
        (forecast_df["yhat_upper"] - forecast_df["yhat_lower"]).mean()
    )
    ci_pct_of_std = raw_ci_width / (hist_std + 1e-6)
 
    if ci_pct_of_std < 1.5:
        confidence_key   = "tinggi"
        confidence_label = "Tinggi"
    elif ci_pct_of_std < 3.0:
        confidence_key   = "sedang"
        confidence_label = "Sedang"
    else:
        confidence_key   = "rendah"
        confidence_label = "Rendah ⚠"
 
    # ── 5-tier decision ───────────────────────────────────────────────────────
    decision_key    = DECISION_MAP.get((dominant, intensity), "TAHAN")
    decision_config = DECISION_CONFIG[decision_key]
 
    # ── Price trend label ─────────────────────────────────────────────────────
    pct_change = (last_yhat - current_price) / current_price * 100
    if pct_change <= -5:
        trend_label = "↓ Turun"
        trend_color = "#DC2626"
    elif pct_change >= 5:
        trend_label = "↑ Naik"
        trend_color = "#16A34A"
    else:
        trend_label = "→ Stabil"
        trend_color = "#2563EB"
 
    return {
        # Core decision
        "decision_key":     decision_key,
        "decision_label":   decision_config["label"],
        "consequence":      decision_config["consequence"],
        "decision_color":   decision_config["color"],
        "decision_bg":      decision_config["bg"],
        "decision_border":  decision_config["border"],
 
        # Confidence
        "confidence_key":   confidence_key,
        "confidence_label": confidence_label,
 
        # Trend
        "trend_label":  trend_label,
        "trend_color":  trend_color,
        "price_change_pct": round(pct_change, 1),
 
        # Legacy fields kept for Azure Function response compatibility
        "dominant_signal":  dominant,
        "intensity":        intensity,
        "glut_score":       int(round(glut_score)),
        "shortage_score":   int(round(shortage_score)),
        "ci_width_pct":     round(raw_ci_width / current_price * 100, 1),
 
        # Chart data
        "forecast_values":  forecast_df["yhat"].round(0).astype(int).tolist(),
        "ci_lower":         forecast_df["yhat_lower"].round(0).astype(int).tolist(),
        "ci_upper":         forecast_df["yhat_upper"].round(0).astype(int).tolist(),
        "forecast_dates":   forecast_df["ds"].dt.strftime("%Y-%m-%d").tolist(),
    }
 
 
def _neutral_signal() -> dict:
    cfg = DECISION_CONFIG["TAHAN"]
    return {
        "decision_key":     "TAHAN",
        "decision_label":   cfg["label"],
        "consequence":      cfg["consequence"],
        "decision_color":   cfg["color"],
        "decision_bg":      cfg["bg"],
        "decision_border":  cfg["border"],
        "confidence_key":   "rendah",
        "confidence_label": "Rendah ⚠",
        "trend_label":  "→ Stabil",
        "trend_color":  "#2563EB",
        "price_change_pct": 0.0,
        "dominant_signal":  "NEUTRAL",
        "intensity":        "LOW",
        "glut_score":       0,
        "shortage_score":   0,
        "ci_width_pct":     0.0,
        "forecast_values":  [],
        "ci_lower":         [],
        "ci_upper":         [],
        "forecast_dates":   [],
    }