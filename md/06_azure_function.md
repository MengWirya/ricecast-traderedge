# PROMPT 06 — Azure Function (HTTP Trigger + Blob Storage)

Context: RiceCast TraderEdge. This prompt builds the Azure Function that
serves as the backend API. The dashboard calls this function to get the
supply pressure forecast.

---

## Architecture recap

```
Dashboard (Streamlit)
    → HTTP GET /api/forecast?horizon=30
    → Azure Function (function_app.py)
        → Download prophet_model.pkl from Blob Storage (cached in memory)
        → Run Prophet.predict() on future dataframe
        → compute_supply_pressure()
        → generate_trader_advice()
        → Return JSON response
```

---

## File: `function/function_app.py`

Build the complete Azure Function:

```python
"""
function_app.py

Azure Function HTTP trigger for RiceCast TraderEdge.
Endpoint: GET /api/forecast?horizon=30

Query parameters:
    horizon (int, optional): forecast horizon in days. Default 30.

Returns JSON:
    {
        "dominant_signal": "GLUT" | "SHORTAGE" | "NEUTRAL",
        "intensity": "LOW" | "MEDIUM" | "HIGH",
        "glut_score": int (0–100),
        "shortage_score": int (0–100),
        "gauge_value": float (-100 to +100),
        "price_change_pct": float,
        "ci_width_pct": float,
        "yhat_mean": int,
        "headline": str (Bahasa Indonesia),
        "full_advice": str (Bahasa Indonesia),
        "signal_color": str (hex),
        "forecast_dates": [str, ...],
        "forecast_values": [float, ...],
        "forecast_lower": [float, ...],
        "forecast_upper": [float, ...],
        "current_price": float,
        "model_loaded_at": str (ISO datetime),
        "data_as_of": str (YYYY-MM),
        "error": null | str
    }
"""

import azure.functions as func
import json
import logging
import os
import io
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Module-level cache — survives warm starts, reset on cold start
_model = None
_cache_df = None        # pre-loaded feature data
_model_loaded_at = None

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ── Blob Storage loader ───────────────────────────────────────────────────

def _load_model_from_blob():
    """Download and deserialise prophet_model.pkl from Azure Blob Storage."""
    from azure.storage.blob import BlobServiceClient

    conn_str      = os.environ.get('BLOB_CONNECTION_STRING')
    container     = os.environ.get('BLOB_CONTAINER_NAME', 'ricecast')
    model_blob    = os.environ.get('MODEL_BLOB_NAME', 'prophet_model.pkl')
    cache_blob    = os.environ.get('CACHE_BLOB_NAME', 'feature_cache.csv')

    if not conn_str:
        raise ValueError("BLOB_CONNECTION_STRING environment variable not set.")

    client = BlobServiceClient.from_connection_string(conn_str)

    # Load model
    logging.info(f"Loading model from blob: {container}/{model_blob}")
    model_data = client.get_blob_client(container, model_blob).download_blob().readall()
    model = joblib.load(io.BytesIO(model_data))
    logging.info("Model loaded from Blob Storage.")

    # Load feature cache (pre-computed latest features)
    try:
        cache_data = client.get_blob_client(container, cache_blob).download_blob().readall()
        cache_df   = pd.read_csv(io.BytesIO(cache_data), parse_dates=['ds'])
        logging.info(f"Feature cache loaded: {len(cache_df)} rows.")
    except Exception as e:
        logging.warning(f"Feature cache not found: {e}. Using fallback.")
        cache_df = None

    return model, cache_df


def _ensure_model_loaded():
    """Load model from Blob on cold start, use cache on warm starts."""
    global _model, _cache_df, _model_loaded_at
    if _model is None:
        _model, _cache_df, = _load_model_from_blob()
        _model_loaded_at = datetime.now(timezone.utc).isoformat()
        logging.info("Cold start: model loaded and cached in memory.")
    return _model, _cache_df


# ── Feature builder ───────────────────────────────────────────────────────

def _build_future_df(model, cache_df, horizon_days: int) -> pd.DataFrame:
    """
    Build a future dataframe for Prophet.predict().
    Uses cached features where available, fills forward for future dates.
    """
    periods = max(1, horizon_days // 30)

    future = model.make_future_dataframe(periods=periods, freq='MS', include_history=False)

    feature_cols = [
        'price_mom_3m', 'price_accel', 'production_dev_pct',
        'harvest_window', 'lean_season',
        'harvest_proximity_days', 'rainfall_dev_pct'
    ]

    if cache_df is not None and len(cache_df) > 0:
        future = future.merge(
            cache_df[['ds'] + [c for c in feature_cols if c in cache_df.columns]],
            on='ds', how='left'
        )

    # Fill missing feature values with neutral defaults
    defaults = {
        'price_mom_3m': 0.0,
        'price_accel': 0.0,
        'production_dev_pct': 0.0,
        'harvest_window': _get_harvest_window_for_month(future['ds'].dt.month),
        'lean_season': _get_lean_season_for_month(future['ds'].dt.month),
        'harvest_proximity_days': 45.0,
        'rainfall_dev_pct': 0.0,
    }
    for col, default in defaults.items():
        if col not in future.columns:
            if isinstance(default, pd.Series):
                future[col] = default.values if len(default) == len(future) else 0
            else:
                future[col] = default
        future[col] = future[col].fillna(
            default.values[0] if isinstance(default, pd.Series) else default
        )

    return future


def _get_harvest_window_for_month(month_series):
    return month_series.isin([3, 4, 5, 7, 8, 9]).astype(int)


def _get_lean_season_for_month(month_series):
    return month_series.isin([10, 11, 12, 1, 2]).astype(int)


def _get_current_price(cache_df) -> float:
    """Get most recent known price from cache."""
    if cache_df is not None and 'y' in cache_df.columns:
        last_price = cache_df['y'].dropna().iloc[-1]
        return float(last_price)
    return 12500.0  # fallback: approximate 2024 Malang beras medium price


# ── HTTP trigger ──────────────────────────────────────────────────────────

@app.route(route="forecast", methods=["GET"])
def forecast(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main endpoint: GET /api/forecast?horizon=30

    Returns supply pressure assessment for East Java rice market.
    """
    logging.info("Forecast request received.")

    try:
        # Parse params
        horizon_days = int(req.params.get('horizon', 30))
        horizon_days = max(7, min(90, horizon_days))  # clamp 7–90 days

        # Load model (cached after first call)
        model, cache_df = _ensure_model_loaded()
        current_price   = _get_current_price(cache_df)

        # Build future dataframe
        future   = _build_future_df(model, cache_df, horizon_days)
        forecast = model.predict(future)

        # Compute supply pressure
        from supply_pressure_scorer import compute_supply_pressure
        from trader_advice import generate_trader_advice

        pressure = compute_supply_pressure(
            forecast_df=forecast,
            current_price=current_price,
            horizon_days=horizon_days
        )
        advice = generate_trader_advice(pressure)

        # Build response
        response = {
            **pressure,
            **{k: v for k, v in advice.items() if k not in pressure},
            'forecast_dates':  forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
            'forecast_values': [round(v) for v in forecast['yhat'].tolist()],
            'forecast_lower':  [round(v) for v in forecast['yhat_lower'].tolist()],
            'forecast_upper':  [round(v) for v in forecast['yhat_upper'].tolist()],
            'current_price':   current_price,
            'model_loaded_at': _model_loaded_at,
            'data_as_of':      cache_df['ds'].max().strftime('%Y-%m') if cache_df is not None else 'unknown',
            'error':           None,
        }

        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype='application/json',
            status_code=200
        )

    except Exception as e:
        logging.error(f"Forecast error: {e}", exc_info=True)
        error_response = {
            'dominant_signal': 'NEUTRAL',
            'intensity': 'LOW',
            'headline': 'Terjadi kesalahan — coba lagi',
            'full_advice': f'Error: {str(e)}',
            'error': str(e),
        }
        return func.HttpResponse(
            json.dumps(error_response),
            mimetype='application/json',
            status_code=500
        )
```

---

## Local testing without Azure

Add a `__main__` block at the bottom of `function_app.py` for local dev:

```python
# ── Local dev runner (not deployed) ──────────────────────────────────────
if __name__ == '__main__':
    """
    Local test: loads model from local file instead of Blob Storage.
    Run: python function/function_app.py
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    print("Loading model from local file...")
    local_model = joblib.load('../models/prophet_model.pkl')
    local_cache = pd.read_csv('../data/processed/master_df.csv', parse_dates=['ds'])

    future   = _build_future_df(local_model, local_cache, 30)
    forecast = local_model.predict(future)

    from supply_pressure_scorer import compute_supply_pressure
    from trader_advice import generate_trader_advice

    current_price = float(local_cache['y'].dropna().iloc[-1])
    pressure = compute_supply_pressure(forecast, current_price)
    advice   = generate_trader_advice(pressure)

    print("\n=== LOCAL TEST RESULT ===")
    print(f"Signal:    {pressure['dominant_signal']} / {pressure['intensity']}")
    print(f"Glut:      {pressure['glut_score']}")
    print(f"Shortage:  {pressure['shortage_score']}")
    print(f"Headline:  {advice['headline']}")
    print(f"\nAdvice:\n{advice['full_advice']}")
    print("========================")
```

---

## Upload model to Blob Storage (run once before deploy)

Create this script as `scripts/upload_model.py`:

```python
"""Upload model and feature cache to Azure Blob Storage."""
import os, joblib, pandas as pd
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
conn_str  = os.environ['BLOB_CONNECTION_STRING']
container = os.environ.get('BLOB_CONTAINER_NAME', 'ricecast')

client = BlobServiceClient.from_connection_string(conn_str)
cc     = client.get_container_client(container)
try:
    cc.create_container()
    print(f"Container '{container}' created.")
except:
    print(f"Container '{container}' already exists.")

# Upload model
with open('models/prophet_model.pkl', 'rb') as f:
    cc.upload_blob('prophet_model.pkl', f, overwrite=True)
print("Uploaded: prophet_model.pkl")

# Upload feature cache (last 12 months of processed data)
df = pd.read_csv('data/processed/master_df.csv')
df.tail(24).to_csv('/tmp/feature_cache.csv', index=False)
with open('/tmp/feature_cache.csv', 'rb') as f:
    cc.upload_blob('feature_cache.csv', f, overwrite=True)
print("Uploaded: feature_cache.csv")
print("Done. Verify in Azure Portal → Storage Account → Containers → ricecast")
```

---

## Acceptance criteria

Run: `python function/function_app.py`

- [ ] Prints signal, headline, and full advice text without errors
- [ ] `full_advice` is in Bahasa Indonesia
- [ ] No `None` values in the output dict
- [ ] Script exits cleanly (no exceptions)
