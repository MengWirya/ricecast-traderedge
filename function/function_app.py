# Fix 1: Forecast now starts from TODAY, not end of training data
# Fix 2: Passes historical prices to scorer for real CI grounding
# Fix 3: Returns new 5-tier decision fields + explanation reasons

import azure.functions as func
import json, io, os, logging
import pandas as pd
from datetime import datetime, timezone
 
import joblib
from azure.storage.blob import BlobServiceClient
 
from supply_pressure_scorer import compute_supply_pressure
from trader_advice import get_trader_advice, build_explanation
 
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
 
_model     = None
_master_df = None
 
FEATURE_COLS = [
    "production_dev_pct", "price_mom_3m", "price_accel",
    "harvest_window", "rainfall_dev_pct",
]
 
 
def _blob():
    return BlobServiceClient.from_connection_string(os.environ["BLOB_CONNECTION_STRING"])
 
 
def _load_model():
    container = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
    blob_name  = os.environ.get("MODEL_BLOB_NAME", "prophet_model.pkl")
    data = _blob().get_blob_client(container, blob_name).download_blob().readall()
    return joblib.load(io.BytesIO(data))
 
 
def _load_master_df():
    container = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
    try:
        data = _blob().get_blob_client(container, "master_df_sample.csv").download_blob().readall()
        return pd.read_csv(io.BytesIO(data), parse_dates=["ds"])
    except Exception as e:
        logging.warning(f"master_df_sample load failed: {e}")
        empty = pd.DataFrame({"ds": pd.Series(dtype="datetime64[ns]")})
        for col in FEATURE_COLS + ["y", "lean_season"]:
            empty[col] = pd.Series(dtype="float64")
        return empty
 
 
def _build_future_df(model, horizon_months: int, today: pd.Timestamp) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """
    FIX: Build future dataframe starting from TODAY, not end of training data.
    Prophet's make_future_dataframe always starts from the last training date.
    We need to generate a future df manually starting from the current month.
    """
    future_dates = pd.date_range(
        start=today.replace(day=1),          # start of current month
        periods=horizon_months,
        freq="MS"
    )
    future = pd.DataFrame({"ds": future_dates})
 
    # Merge known features from master_df where dates overlap
    if _master_df is not None and len(_master_df) > 0:
        future = future.merge(
            _master_df[["ds"] + FEATURE_COLS],
            on="ds", how="left"
        )
 
    # Fill unknown future months with neutral
    for col in FEATURE_COLS:
        if col not in future.columns:
            future[col] = 0.0
        else:
            future[col] = future[col].fillna(0.0)
 
    # Harvest window always derived from calendar — never trust fill
    future["harvest_window"] = future["ds"].dt.month.isin([3, 4, 5, 7, 8, 9]).astype(int)
    future["lean_season"]    = future["ds"].dt.month.isin([10, 11, 12, 1, 2]).astype(int)
 
    # Prophet requires a continuous history to predict. Append history + future.
    if _master_df is not None and len(_master_df) > 0:
        hist = _master_df[["ds"] + FEATURE_COLS].copy()
        hist["harvest_window"] = hist["ds"].dt.month.isin([3, 4, 5, 7, 8, 9]).astype(int)
        hist["lean_season"]    = hist["ds"].dt.month.isin([10, 11, 12, 1, 2]).astype(int)
        for col in FEATURE_COLS:
            hist[col] = hist[col].fillna(0.0)
        combined = pd.concat([hist, future], ignore_index=True).drop_duplicates("ds").sort_values("ds")
    else:
        # Fallback: extend from model's training end
        combined = model.make_future_dataframe(periods=horizon_months, freq="MS")
        for col in FEATURE_COLS:
            combined[col] = 0.0
        combined["harvest_window"] = combined["ds"].dt.month.isin([3, 4, 5, 7, 8, 9]).astype(int)
        combined["lean_season"]    = combined["ds"].dt.month.isin([10, 11, 12, 1, 2]).astype(int)
 
    return combined, future_dates
 
 
def _get_current_price() -> float:
    if _master_df is not None and len(_master_df) > 0 and "y" in _master_df.columns:
        p = _master_df["y"].dropna()
        if len(p) > 0:
            return float(p.iloc[-1])
    try:
        container = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
        data = _blob().get_blob_client(container, "current_price.json").download_blob().readall()
        info = json.loads(data)
        if info.get("current_price"):
            return float(info["current_price"])
    except Exception:
        pass
    return 13500.0
 
 
def _get_historical_prices() -> list:
    """Last 24 months of actual prices for volatility grounding."""
    if _master_df is not None and "y" in _master_df.columns:
        return _master_df["y"].dropna().tail(24).tolist()
    return []
 
 
def _get_latest_features() -> dict:
    if _master_df is not None and len(_master_df) > 0:
        last = _master_df.iloc[-1]
        return {col: float(last.get(col, 0) or 0) for col in FEATURE_COLS}
    return {col: 0.0 for col in FEATURE_COLS}
 
 
@app.route(route="forecast", methods=["GET"])
def forecast(req: func.HttpRequest) -> func.HttpResponse:
    global _model, _master_df
    logging.info("TraderEdge v2 forecast request")
 
    try:
        horizon = max(1, min(int(req.params.get("horizon", 3)), 6))
        today   = pd.Timestamp(datetime.now(timezone.utc).date())
 
        if _model is None:
            logging.info("Cold start: loading model")
            _model = _load_model()
        if _master_df is None:
            _master_df = _load_master_df()
 
        # Build future df anchored to today
        full_df, future_dates = _build_future_df(_model, horizon, today)
        forecast_result = _model.predict(full_df)
 
        # Extract only the future horizon rows
        future_only = forecast_result[
            forecast_result["ds"].isin(future_dates)
        ].copy().reset_index(drop=True)
 
        if len(future_only) == 0:
            # If future dates not in forecast, take last N rows
            future_only = forecast_result.tail(horizon).copy().reset_index(drop=True)
 
        future_only["harvest_window"] = future_only["ds"].dt.month.isin([3,4,5,7,8,9]).astype(int)
        future_only["lean_season"]    = future_only["ds"].dt.month.isin([10,11,12,1,2]).astype(int)
 
        current_price     = _get_current_price()
        historical_prices = _get_historical_prices()
        latest_features   = _get_latest_features()
 
        # Score with v2 scorer
        signal = compute_supply_pressure(future_only, current_price, historical_prices)
 
        # Build explanation reasons
        reasons = build_explanation(signal["dominant_signal"], latest_features)
 
        # Build trader advice
        advice = get_trader_advice(signal["dominant_signal"], signal["intensity"], latest_features)
 
        # Season label
        current_month = today.month
        if current_month in [3, 4, 5]:
            season_label = "Panen Raya"
        elif current_month in [7, 8, 9]:
            season_label = "Panen Kedua"
        elif current_month in [10, 11, 12, 1, 2]:
            season_label = "Paceklik"
        else:
            season_label = "Tanam"
 
        # Production label
        prod_dev = latest_features.get("production_dev_pct", 0)
        if prod_dev > 0.10:
            prod_label = f"+{prod_dev*100:.0f}% normal"
        elif prod_dev < -0.10:
            prod_label = f"{prod_dev*100:.0f}% normal"
        else:
            prod_label = "Normal"
 
        response = {
            "status":          "ok",
            "generated_at":    datetime.now(timezone.utc).isoformat(),
            "horizon_months":  horizon,
            "current_price":   int(current_price),
            "forecast_start":  today.strftime("%Y-%m-%d"),
 
            # ── Decision (new in v2) ──────────────────────────────────────────
            "decision_key":    signal["decision_key"],
            "decision_label":  signal["decision_label"],
            "consequence":     signal["consequence"],
            "decision_color":  signal["decision_color"],
            "decision_bg":     signal["decision_bg"],
            "decision_border": signal["decision_border"],
 
            # ── Explanation bullets (new in v2) ───────────────────────────────
            "reasons":         reasons,
 
            # ── Context strip (new in v2) ─────────────────────────────────────
            "season_label":    season_label,
            "trend_label":     signal["trend_label"],
            "trend_color":     signal["trend_color"],
            "prod_label":      prod_label,
            "confidence_label":signal["confidence_label"],
            "price_change_pct":signal["price_change_pct"],
 
            # ── Legacy fields kept for backwards compat ───────────────────────
            "dominant_signal": signal["dominant_signal"],
            "intensity":       signal["intensity"],
            "glut_score":      signal["glut_score"],
            "shortage_score":  signal["shortage_score"],
            "ci_width_pct":    signal["ci_width_pct"],
            "action_text":     advice["action_text"],
            "reason":          advice["reason"],
            "confidence_days": advice["horizon_days"],
 
            # ── Chart data ────────────────────────────────────────────────────
            "forecast_dates":  signal["forecast_dates"],
            "forecast_values": signal["forecast_values"],
            "ci_lower":        signal["ci_lower"],
            "ci_upper":        signal["ci_upper"],
        }
 
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"},
        )
 
    except Exception as e:
        logging.error(f"Forecast error: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
        )
 
 
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({
            "status":       "ok",
            "model_loaded": _model is not None,
            "data_loaded":  _master_df is not None and len(_master_df) > 0,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }),
        mimetype="application/json",
        status_code=200,
    )