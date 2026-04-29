# =============================================================================
# function/function_app.py
# Azure Function HTTP trigger — main entry point.
#
# Flow:
#   1. Cold start: download prophet_model.pkl from Azure Blob Storage
#   2. Warm start: model cached in memory (_model global)
#   3. On request: build future df → Prophet.predict() → score → advice → JSON
#
# Test locally:
#   func start
#   curl "http://localhost:7071/api/forecast?horizon=3"
# =============================================================================
 
import azure.functions as func
import json
import io
import os
import logging
import pandas as pd
from datetime import datetime, timezone
 
import joblib
from azure.storage.blob import BlobServiceClient
 
from supply_pressure_scorer import compute_supply_pressure
from trader_advice import get_trader_advice
 
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
 
# ── Module-level cache — survives across warm invocations ─────────────────────
_model     = None
_master_df = pd.DataFrame()
 
FEATURE_COLS = [
    "production_dev_pct",
    "price_mom_3m",
    "price_accel",
    "harvest_window",
    "rainfall_dev_pct",
]
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def _get_blob_client():
    conn_str = os.environ["BLOB_CONNECTION_STRING"]
    return BlobServiceClient.from_connection_string(conn_str)
 
 
def _load_model():
    """Download and deserialize Prophet model from Blob Storage."""
    container = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
    blob_name = os.environ.get("MODEL_BLOB_NAME", "prophet_model.pkl")
 
    logging.info(f"Loading model from blob: {container}/{blob_name}")
    client = _get_blob_client()
    data   = client.get_blob_client(container, blob_name).download_blob().readall()
    return joblib.load(io.BytesIO(data))
 
 
def _load_master_df():
    """Load cached master_df sample from Blob for feature lookup."""
    container = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
 
    try:
        client = _get_blob_client()
        data   = client.get_blob_client(container, "master_df_sample.csv").download_blob().readall()
        df     = pd.read_csv(io.BytesIO(data), parse_dates=["ds"])
        logging.info(f"master_df_sample loaded: {len(df)} rows")
        return df
    except Exception as e:
        logging.warning(f"Could not load master_df_sample: {e} — using empty features")
        # Return empty df with correct schema so the rest of the code won't break
        empty = pd.DataFrame({"ds": pd.Series(dtype="datetime64[ns]")})
        for col in FEATURE_COLS + ["y", "lean_season"]:
            empty[col] = pd.Series(dtype="float64")
        return empty
 
 
def _build_future_df(model, horizon_months: int) -> pd.DataFrame:
    """Build future dataframe for Prophet.predict() with feature values."""
    global _master_df
 
    future = model.make_future_dataframe(periods=horizon_months, freq="MS")
 
    # Merge known feature values from cached master_df
    if len(_master_df) > 0:
        future = future.merge(
            _master_df[["ds"] + FEATURE_COLS],
            on="ds", how="left"
        )
 
    # Fill any missing feature values (unknown future months) with neutral 0
    for col in FEATURE_COLS:
        if col not in future.columns:
            future[col] = 0.0
        else:
            future[col] = future[col].fillna(0.0)
 
    # Always recalculate harvest_window from calendar — don't trust fill
    future["harvest_window"] = future["ds"].dt.month.isin([3, 4, 5, 7, 8, 9]).astype(int)
 
    return future
 
 
def _get_current_price() -> float:
    """Get latest known price from master_df or current_price.json."""
    global _master_df
 
    # Try master_df first
    if len(_master_df) > 0 and "y" in _master_df.columns:
        price = _master_df["y"].dropna()
        if len(price) > 0:
            return float(price.iloc[-1])
 
    # Fallback: try current_price.json in blob
    try:
        container = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
        client    = _get_blob_client()
        data      = client.get_blob_client(container, "current_price.json").download_blob().readall()
        info      = json.loads(data)
        if info.get("current_price"):
            return float(info["current_price"])
    except Exception:
        pass
 
    # Last resort: hardcoded recent estimate
    logging.warning("Could not determine current price — using 13500 as fallback")
    return 13500.0
 
 
def _get_latest_features() -> dict:
    """Get latest feature values for advice reason generation."""
    global _master_df
    if len(_master_df) > 0:
        last = _master_df.iloc[-1]
        return {col: float(last.get(col, 0) or 0) for col in FEATURE_COLS}
    return {col: 0.0 for col in FEATURE_COLS}
 
 
# ── Main Function ─────────────────────────────────────────────────────────────
 
@app.route(route="forecast", methods=["GET"])
def forecast(req: func.HttpRequest) -> func.HttpResponse:
    global _model, _master_df
 
    logging.info("TraderEdge forecast request received")
 
    try:
        # ── Parse & validate params ──────────────────────────────────────
        try:
            horizon = int(req.params.get("horizon", 3))
        except ValueError:
            horizon = 3
        horizon = max(1, min(horizon, 6))   # clamp: 1–6 months
 
        # ── Cold start: load model and data ─────────────────────────────
        if _model is None:
            logging.info("Cold start: loading model from Blob Storage")
            _model = _load_model()
            logging.info("Model loaded ✓")
 
        if _master_df is None:
            _master_df = _load_master_df()
 
        # ── Build future dataframe and run forecast ──────────────────────
        future   = _build_future_df(_model, horizon)
        forecast_result = _model.predict(future)
 
        # Extract only the future-horizon slice (not historical fitted values)
        future_only = forecast_result.tail(horizon).copy()
        future_only["lean_season"] = future_only["ds"].dt.month.isin([10, 11, 12, 1, 2]).astype(int)
 
        # ── Get current price ────────────────────────────────────────────
        current_price = _get_current_price()
 
        # ── Compute supply pressure signal ───────────────────────────────
        signal = compute_supply_pressure(future_only, current_price)
 
        # ── Generate trader advice ────────────────────────────────────────
        latest_features = _get_latest_features()
        advice = get_trader_advice(
            dominant_signal=signal["dominant_signal"],
            intensity=signal["intensity"],
            features=latest_features,
        )
 
        # ── Build response payload ────────────────────────────────────────
        response = {
            "status":           "ok",
            "generated_at":     datetime.now(timezone.utc).isoformat(),
            "horizon_months":   horizon,
            "current_price":    int(current_price),
 
            # Core signal
            "dominant_signal":  signal["dominant_signal"],
            "intensity":        signal["intensity"],
            "glut_score":       signal["glut_score"],
            "shortage_score":   signal["shortage_score"],
            "ci_width_pct":     signal["ci_width_pct"],
            "price_change_pct": signal["price_change_pct"],
 
            # Trader advice
            "action_text":      advice["action_text"],
            "reason":           advice["reason"],
            "confidence_days":  advice["horizon_days"],
 
            # Chart data
            "forecast_dates":   signal["forecast_dates"],
            "forecast_values":  signal["forecast_values"],
            "ci_lower":         signal["ci_lower"],
            "ci_upper":         signal["ci_upper"],
        }
 
        return func.HttpResponse(
            body=json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}   # allow dashboard to call this
        )
 
    except Exception as e:
        logging.error(f"Error in forecast function: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
        )
 
 
# ── Health check endpoint ─────────────────────────────────────────────────────
 
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Quick ping to verify the Function is running before the demo."""
    return func.HttpResponse(
        body=json.dumps({
            "status": "ok",
            "model_loaded": _model is not None,
            "data_loaded":  _master_df is not None and len(_master_df) > 0,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }),
        mimetype="application/json",
        status_code=200,
    )