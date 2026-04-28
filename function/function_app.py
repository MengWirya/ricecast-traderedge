"""
function_app.py

Azure Function HTTP trigger for RiceCast TraderEdge.
Endpoint: GET /api/forecast?horizon=30
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

_model = None
_cache_df = None
_model_loaded_at = None

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _load_model_from_blob():
    from azure.storage.blob import BlobServiceClient

    conn_str = os.environ.get('BLOB_CONNECTION_STRING')
    container = os.environ.get('BLOB_CONTAINER_NAME', 'ricecast')
    model_blob = os.environ.get('MODEL_BLOB_NAME', 'prophet_model.pkl')
    cache_blob = os.environ.get('CACHE_BLOB_NAME', 'feature_cache.csv')

    if not conn_str:
        raise ValueError('BLOB_CONNECTION_STRING environment variable not set.')

    client = BlobServiceClient.from_connection_string(conn_str)
    logging.info(f'Loading model from blob: {container}/{model_blob}')
    model_data = client.get_blob_client(container, model_blob).download_blob().readall()
    model = joblib.load(io.BytesIO(model_data))
    logging.info('Model loaded from Blob Storage.')

    try:
        cache_data = client.get_blob_client(container, cache_blob).download_blob().readall()
        cache_df = pd.read_csv(io.BytesIO(cache_data), parse_dates=['ds'])
        logging.info(f'Feature cache loaded: {len(cache_df)} rows.')
    except Exception as e:
        logging.warning(f'Feature cache not found: {e}. Using fallback.')
        cache_df = None

    return model, cache_df


def _ensure_model_loaded():
    global _model, _cache_df, _model_loaded_at
    if _model is None:
        _model, _cache_df = _load_model_from_blob()
        _model_loaded_at = datetime.now(timezone.utc).isoformat()
        logging.info('Cold start: model loaded and cached in memory.')
    return _model, _cache_df


def _get_harvest_window_for_month(month_series):
    return month_series.isin([3, 4, 5, 7, 8, 9]).astype(int)


def _get_lean_season_for_month(month_series):
    return month_series.isin([10, 11, 12, 1, 2]).astype(int)


def _get_current_price(cache_df) -> float:
    if cache_df is not None and 'y' in cache_df.columns:
        last_price = cache_df['y'].dropna().iloc[-1]
        return float(last_price)
    return 12500.0


def _build_future_df(model, cache_df, horizon_days: int) -> pd.DataFrame:
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
            future[col] = default
        if isinstance(default, pd.Series):
            future[col] = future[col].fillna(pd.Series(default.values, index=future.index))
        else:
            future[col] = future[col].fillna(default)
    return future


@app.route(route='forecast', methods=['GET'])
def forecast(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Forecast request received.')
    try:
        horizon_days = int(req.params.get('horizon', 30))
        horizon_days = max(7, min(90, horizon_days))
        model, cache_df = _ensure_model_loaded()
        current_price = _get_current_price(cache_df)
        future = _build_future_df(model, cache_df, horizon_days)
        forecast_df = model.predict(future)
        from supply_pressure_scorer import compute_supply_pressure
        from trader_advice import generate_trader_advice
        pressure = compute_supply_pressure(
            forecast_df=forecast_df,
            current_price=current_price,
            horizon_days=horizon_days,
        )
        advice = generate_trader_advice(pressure)
        response = {
            **pressure,
            **{k: v for k, v in advice.items() if k not in pressure},
            'forecast_dates': forecast_df['ds'].dt.strftime('%Y-%m-%d').tolist(),
            'forecast_values': [round(v) for v in forecast_df['yhat'].tolist()],
            'forecast_lower': [round(v) for v in forecast_df['yhat_lower'].tolist()],
            'forecast_upper': [round(v) for v in forecast_df['yhat_upper'].tolist()],
            'current_price': current_price,
            'model_loaded_at': _model_loaded_at,
            'data_as_of': cache_df['ds'].max().strftime('%Y-%m') if cache_df is not None else 'unknown',
            'error': None,
        }
        return func.HttpResponse(json.dumps(response, ensure_ascii=False), mimetype='application/json', status_code=200)
    except Exception as e:
        logging.error(f'Forecast error: {e}', exc_info=True)
        error_response = {
            'dominant_signal': 'NEUTRAL',
            'intensity': 'LOW',
            'headline': 'Terjadi kesalahan — coba lagi',
            'full_advice': f'Error: {str(e)}',
            'error': str(e),
        }
        return func.HttpResponse(json.dumps(error_response, ensure_ascii=False), mimetype='application/json', status_code=500)


if __name__ == '__main__':
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..')))
    print('Loading model from local file...')
    local_model = joblib.load(os.path.join(current_dir, '..', 'models', 'prophet_model.pkl'))
    local_cache = pd.read_csv(os.path.join(current_dir, '..', 'data', 'processed', 'master_df.csv'), parse_dates=['ds'])
    future = _build_future_df(local_model, local_cache, 30)
    forecast_df = local_model.predict(future)
    from supply_pressure_scorer import compute_supply_pressure
    from trader_advice import generate_trader_advice
    current_price = float(local_cache['y'].dropna().iloc[-1])
    pressure = compute_supply_pressure(forecast_df, current_price)
    advice = generate_trader_advice(pressure)
    print('\n=== LOCAL TEST RESULT ===')
    print(f"Signal:    {pressure['dominant_signal']} / {pressure['intensity']}")
    print(f"Glut:      {pressure['glut_score']}")
    print(f"Shortage:  {pressure['shortage_score']}")
    print(f"Headline:  {advice['headline']}")
    print(f"\nAdvice:\n{advice['full_advice']}")
    print('========================')
