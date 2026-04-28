# PROMPT 04 â€” Model Training, Backtest, and Dashboard

> Read `00_PROJECT_CONTEXT.md` first.
> This module combines model training and the Streamlit dashboard into one cohesive step.

## Part 1 â€” Model training and validation

Build `notebooks/03_model_training.ipynb`.

### Load processed data

```python
import pandas as pd
import numpy as np
import warnings
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

warnings.filterwarnings('ignore')

train = pd.read_csv('data/processed/train_df.csv', parse_dates=['ds'])
holdout = pd.read_csv('data/processed/holdout_df.csv', parse_dates=['ds'])
master = pd.read_csv('data/processed/master_df.csv', parse_dates=['ds'])
```

### Prophet configuration

Use:
- `seasonality_mode='multiplicative'`
- `yearly_seasonality=True`
- `weekly_seasonality=False`
- `daily_seasonality=False`
- `changepoint_prior_scale=0.05`
- `interval_width=0.80`

Add regressors:
- `production_dev_pct`
- `price_mom_3m`
- `price_accel`
- `harvest_window`
- `rainfall_dev_pct`

### Forecast generation

- Build a future dataframe for the holdout period
- Merge the feature values for all future `ds`
- Fill missing regressors with neutral defaults
- Predict and save forecast output in `data/processed/forecast_df.csv`

### Holdout validation

Compute:
- Directional accuracy
- MAE
- MAPE
- Mean CI width

Report: target directional accuracy > 55%.

### Save model

- Persist the trained model to `models/prophet_model.pkl`
- Validate by loading it again and running a simple test predict
- Write training results to `models/model_card.md`

---

## Part 2 â€” Streamlit dashboard

Build the dashboard in `dashboard/`.

### Dashboard goal
- Display the current supply pressure signal
- Show forecast line chart with confidence intervals
- Show a trader action card in Bahasa Indonesia
- Present a gauge for glut vs shortage pressure

### Components
- `dashboard/components/supply_gauge.py`
- `dashboard/components/forecast_chart.py`
- `dashboard/components/trader_action_card.py`

### Dashboard behavior
- Call the Azure Function backend at `FUNCTION_ENDPOINT`
- Display:
  - latest `dominant_signal`
  - `intensity`
  - `trader_action`
  - forecast chart
  - CI band and holdout context

### User-facing text
- All labels, headings, and advice text must be in Bahasa Indonesia
- The dashboard is aimed at rice traders at Pasar Induk Malang

### Acceptance

- The dashboard runs locally with `streamlit run dashboard/app.py`
- It consumes the function API successfully
- It renders a clear signal card, gauge, and forecast chart
- It uses Bahasa Indonesia for all user-facing strings
