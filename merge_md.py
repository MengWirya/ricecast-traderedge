from pathlib import Path

base = Path(r'c:/Users/mengw/OneDrive/Documents/Profesional Work/ricecast-traderedge/md')
files = {
    '01_project_setup.md': '''# PROMPT 01 — Project Setup, Context, and Data Pipeline Overview

> Read `00_PROJECT_CONTEXT.md` first. This file combines the project scaffold, environment setup, and high-level data pipeline context into one coherent reference.

## What this file contains
- Project purpose, user story, and core output
- Folder structure and file layout
- Development and Azure Function requirements
- Environment variables and Azure config
- Git ignore policy
- Model card template
- Data source summary and model design
- Supply pressure scoring logic
- Key project constraints and acceptance criteria

---

## Step 1 — Create folder structure

Create the following directory tree:

```
ricecast-traderedge/
├── notebooks/
├── function/
├── dashboard/
│   └── components/
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── models/
└── tests/
```

---

## Step 2 — requirements-dev.txt

Create `requirements-dev.txt` with exact pinned dependencies:

```
# Core model
prophet==1.1.5
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.4.2
statsmodels==0.14.2

# Momentum / technical analysis
pandas-ta==0.3.14b0

# Visualisation (notebooks)
matplotlib==3.8.4
plotly==5.20.0

# Dashboard
streamlit==1.33.0
requests==2.31.0

# Azure
azure-functions==1.18.0
azure-storage-blob==12.19.1

# Serialisation
joblib==1.3.2

# Dev & testing
pytest==8.1.1
black==24.3.0
python-dotenv==1.0.1
jupyter==7.1.3
ipykernel==6.29.4
```

---

## Step 3 — function/requirements.txt

Create `function/requirements.txt` with the slim production runtime dependencies:

```
prophet==1.1.5
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.4.2
joblib==1.3.2
azure-functions==1.18.0
azure-storage-blob==12.19.1
python-dotenv==1.0.1
```

---

## Step 4 — Azure Functions config

Create `function/host.json`:

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

Create `function/local.settings.json` for local development only:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BLOB_CONNECTION_STRING": "your_connection_string_here",
    "BLOB_CONTAINER_NAME": "ricecast",
    "MODEL_BLOB_NAME": "prophet_model.pkl"
  }
}
```

---

## Step 5 — .env.example

Create `.env.example`:

```
# Azure Blob Storage
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
BLOB_CONTAINER_NAME=ricecast
MODEL_BLOB_NAME=prophet_model.pkl

# Dashboard → Function URL
FUNCTION_ENDPOINT=https://your-function-app.azurewebsites.net/api/forecast
```

---

## Step 6 — .gitignore

Ignore local environment files, data, and large models:

```
# Environment
.env
local.settings.json
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/

# Data — raw files never committed (too large, may contain sensitive info)
data/raw/
data/processed/

# Model artifact — large binary
models/prophet_model.pkl

# Jupyter checkpoints
.ipynb_checkpoints/

# OS
.DS_Store
Thumbs.db

# Azure
.azure/
```

---

## Step 7 — models/model_card.md template

Create `models/model_card.md`:

```markdown
# RiceCast TraderEdge — Model Card

## Model details
- **Type:** Facebook Prophet (multiplicative seasonality)
- **Version:** (fill after training)
- **Trained:** (date)
- **Training data:** (date range and sources)

## Validation summary
- **Holdout directional accuracy:**
- **MAE:**
- **MAPE:**

## Notes
- Forecast is directional only, not exact price prediction.
- Model is valid for Jawa Timur rice market only.
- All user-facing text is in Bahasa Indonesia.
```

---

## Project context and tech stack

RiceCast TraderEdge is an AI-powered supply pressure detector for UMKM rice traders at Pasar Induk Gadang Malang. It is intended to provide a structured signal, not an exact price prediction.

### Core output

A structured signal containing:
- `dominant_signal`: `GLUT` | `SHORTAGE` | `NEUTRAL`
- `intensity`: `HIGH` | `MEDIUM` | `LOW`
- `trader_action`: Bahasa Indonesia advice
- `confidence_days`: 7–30
- `forecast_values`, `ci_lower`, `ci_upper`

### Tech stack

| Layer | Technology | Why |
|---|---|---|
| Forecasting model | Facebook Prophet (Python) | Interpretable, fits monthly rice price seasonality |
| Backend | Azure Functions (Python) | HTTP trigger, lightweight deployment |
| Model storage | Azure Blob Storage | Stores `prophet_model.pkl` and feature cache |
| Frontend | Streamlit | Fast dashboard, deployable to Azure App Service |
| Language | Python 3.11 | |

### Data sources

| Dataset | Role | Source |
|---|---|---|
| WFP Indonesia Food Prices | Primary price series | HDX / humdata.org |
| PIHPS Malang | Malang rice price supplement | bi.go.id |
| BPS monthly production | Supply deviation feature | bps.go.id |
| BMKG rainfall | Supporting weather regressor | dataonline.bmkg.go.id |

### Prophet model design

Use Prophet with:
- `seasonality_mode='multiplicative'`
- `yearly_seasonality=True`
- `weekly_seasonality=False`
- `daily_seasonality=False`
- `changepoint_prior_scale=0.05`
- `interval_width=0.80`

Regressors:
- `production_dev_pct`
- `price_mom_3m`
- `price_accel`
- `harvest_window`
- `rainfall_dev_pct`

### Supply pressure scoring logic

The scoring module should produce:
- `glut_score` — price decline + harvest proximity
- `shortage_score` — price rise + lean season
- `dominant_signal` — the higher score if above threshold, else `NEUTRAL`
- `intensity` — `HIGH` / `MEDIUM` / `LOW`

Example scoring rule:
```python
def compute_supply_pressure(...):
    price_change_pct = (last_yhat - current_price) / current_price
    glut_score = max(0, -price_change_pct * 300) + (25 if harvest_near else 0)
    shortage_score = max(0, price_change_pct * 300) + (20 if lean_near else 0)
```

### Key constraints

- No managed Azure ML endpoints
- No Azure OpenAI
- No live scraping during demo
- Do not expose exact price predictions to users
- User-facing text in Bahasa Indonesia
- Wide uncertainty intervals must be visible

---

## Acceptance criteria

- Project scaffold exists exactly as specified
- `requirements-dev.txt` and `function/requirements.txt` are pinned correctly
- Azure config files are present and local-only values are ignored in git
- Model card template is created
- Project context and data source expectations are documented clearly
- All high-level constraints are stated explicitly
''',
    '02_data_pipeline.md': '''# PROMPT 02 — Data Pipeline, Model Training, and Backtest

> Read `00_PROJECT_CONTEXT.md` first.
> This module covers both the data pipeline and the first model training/backtest notebook.

## Part 1 — Data pipeline

The goal is to build `data/processed/master_df.csv` and supporting CSVs using raw inputs from `data/raw/`.

### Expected raw files
- `data/raw/wfp_food_prices_idn.csv`
- `data/raw/pihps_malang_beras.xlsx`
- `data/raw/bps_produksi_padi_bulanan.xlsx`
- `data/raw/bmkg_rainfall_jatim.csv`

### Required outputs
- `data/processed/master_df.csv`
- `data/processed/train_df.csv` (`ds` < 2024-01-01)
- `data/processed/holdout_df.csv` (`ds` >= 2024-01-01)

### Master dataframe columns
| Column | Type | Description |
|---|---|---|
| `ds` | datetime (month-start) | Month start date |
| `y` | float | Mean rice price IDR/kg, Beras Medium, Jawa Timur |
| `production_dev_pct` | float | Deviation from seasonal production mean |
| `price_mom_3m` | float | 3-month rolling price change |
| `price_accel` | float | Momentum acceleration |
| `harvest_window` | int | 1 if harvest season |
| `lean_season` | int | 1 if lean season |
| `harvest_proximity_days` | int | Days until next major harvest window |
| `rainfall_dev_pct` | float | Rainfall deviation feature |

### Step 1 — WFP / HDX price data

Write `load_wfp_prices(path)`:
- Read CSV
- Print columns and sample rows
- Filter `adm1_name` contains `Jawa Timur`
- Filter `commodity` contains `Rice`
- Keep `date`, `market`, `commodity`, `price`, `unit`
- Convert `date` to datetime
- Resample monthly mean price
- Rename to `ds`, `y_wfp`
- Validate date range includes before 2015 and after 2022

### Step 2 — PIHPS Malang price data

Write `load_pihps_malang(path)`:
- Read Excel, skip first 2 rows
- Inspect and normalize column names
- Identify the date column and medium rice price column
- Convert date with `dayfirst=True`
- Drop null price rows
- Resample to monthly mean
- Rename to `ds`, `y_pihps`
- If file is missing, return `None` with warning

### Step 3 — BPS production data

Write `load_bps_production(path)`:
- Read Excel, skip first 3 rows
- Print columns for inspection
- Identify Jawa Timur production column and date/month column
- Compute seasonal mean by month
- Create `production_dev_pct` = (actual - mean) / mean
- Return `ds`, `production_gkg`, `production_dev_pct`

### Step 4 — BMKG rainfall data

Write `load_bmkg_rainfall(path)`:
- Read CSV and inspect columns
- Identify date and rainfall columns
- Resample to monthly totals if needed
- Compute `rainfall_dev_pct` by monthly seasonal mean
- Return `ds`, `rainfall_mm`, `rainfall_dev_pct`

### Step 5 — Harvest calendar features

Write `build_harvest_features(date_series)`:
- `harvest_window` = 1 for months [3,4,5,7,8,9]
- `lean_season` = 1 for months [10,11,12,1,2]
- `harvest_proximity_days` = days until next March 1 if not in harvest
- Return columns `ds`, `harvest_window`, `lean_season`, `harvest_proximity_days`

### Step 6 — Select price series

Write `select_price_series(df_wfp, df_pihps)`:
- If both present: merge on `ds`, average `y_wfp` and `y_pihps`
- If only WFP present: use `y_wfp`
- If only PIHPS present: use `y_pihps`
- Assert final series has at least 48 rows
- Return `ds`, `y`

### Step 7 — Build master dataframe

Write `build_master_df(price_df, bps_df, bmkg_df, harvest_df)`:
- Start from `price_df`
- Left-join `bps_df`, `bmkg_df`, `harvest_df`
- Fill missing `production_dev_pct` and `rainfall_dev_pct` with 0
- Drop rows with null `y`
- Save `data/processed/master_df.csv`
- Return final dataframe

### Step 8 — Data quality report

Print a formatted report showing:
- price source used
- date range
- total rows
- missing `y`
- missing feature fills
- feature summary counts
- final columns

### Step 9 — Train / holdout split

Save split CSVs:
- `train_df.csv` for `ds < 2024-01-01`
- `holdout_df.csv` for `ds >= 2024-01-01`

---

## Part 2 — Model training & backtest

This section builds the initial Prophet model and validates it on holdout data.

### Model training notebook expectations

Build `notebooks/03_model_training.ipynb`:
- Load `data/processed/master_df.csv`
- Add lag features and price momentum
- Build Prophet regressors
- Fit the model on training data
- Save `models/prophet_model.pkl`
- Run cross-validation and holdout validation
- Save performance CSVs

### Training configuration

Use Prophet with:
- `seasonality_mode='multiplicative'`
- `yearly_seasonality=True`
- `weekly_seasonality=False`
- `daily_seasonality=False`
- `changepoint_prior_scale=0.05`
- `interval_width=0.80`

Regressors:
- `production_dev_pct`
- `price_mom_3m`
- `price_accel`
- `harvest_window`
- `rainfall_dev_pct`

### Forecast generation

- Build a future dataframe using actual feature values when available
- Fill missing regressors with neutral defaults
- Predict future `yhat`, `yhat_lower`, `yhat_upper`
- Save `data/processed/forecast_df.csv`

### Holdout validation

Compute:
- Directional accuracy
- MAE
- MAPE

The primary metric is directional accuracy; target > 55% on holdout.

### Save model

- Save the trained Prophet model to `models/prophet_model.pkl`
- Optionally verify with a round-trip load and predict test
- Write key training summary to `models/model_card.md`

### Backtest hero events

Validate the model against documented events:
- Q2 2022 post-harvest glut
- Q3 2023 El Niño shortage

Backtest should demonstrate lead time before the event and support the supply pressure narrative.
''',
    '03_feature_engineering.md': '''# PROMPT 03 — Feature Engineering and Azure Function Backend

> Read `00_PROJECT_CONTEXT.md` first.
> This module combines advanced feature engineering with the backend API that serves the supply pressure forecast.

## Part 1 — Feature engineering

Build `notebooks/02_feature_engineering.ipynb` to enrich `data/processed/master_df.csv`.

### Required features
- `price_mom_1m`
- `price_mom_3m`
- `price_accel`
- `production_dev_pct`
- `harvest_window`
- `lean_season`
- `harvest_proximity_days`
- `rainfall_dev_pct`

### Load and inspect

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

master = pd.read_csv('data/processed/master_df.csv', parse_dates=['ds'])
print(master.head())
```

### Momentum feature engineering

```python
master['price_mom_1m'] = master['y'].pct_change(1)
master['price_mom_3m'] = master['y'].pct_change(3)
master['price_accel'] = master['price_mom_1m'] - master['price_mom_3m']
master[['price_mom_1m','price_mom_3m','price_accel']] = master[['price_mom_1m','price_mom_3m','price_accel']].fillna(0)
```

### Validate feature quality

- Ensure `master['y'].isna().sum() == 0`
- Ensure no NaNs remain in the engineered momentum columns
- Print correlations with `y`
- Warn if any feature correlation exceeds 0.8

### Seasonal decomposition

Use `statsmodels` seasonal decomposition to validate multiplicative seasonality:

```python
from statsmodels.tsa.seasonal import seasonal_decompose

decomp = seasonal_decompose(master.set_index('ds')['y'], model='multiplicative', period=12, extrapolate_trend='freq')
```

Save a plot of the decomposition for model justification.

### Supply pressure visual

Create and save a scatter plot that shows the relationship between:
- `production_dev_pct`
- `price_mom_3m`
- `harvest_window`

This is the core TraderEdge motivation chart.

### Save enriched data

Save the final dataframe and updated splits:
```python
master.to_csv('data/processed/master_df.csv', index=False)
train_df = master[master['ds'] < '2024-01-01']
holdout_df = master[master['ds'] >= '2024-01-01']
train_df.to_csv('data/processed/train_df.csv', index=False)
holdout_df.to_csv('data/processed/holdout_df.csv', index=False)
```

---

## Part 2 — Azure Function backend

Build the HTTP backend in `function/`.

### API requirements
- Endpoint: `GET /api/forecast?horizon=30`
- Loads `prophet_model.pkl` from Azure Blob Storage
- Runs Prophet forecast for the requested horizon
- Computes supply pressure signal
- Returns JSON response with forecast, signal, and trader advice

### Function package files
- `function/requirements.txt`
- `function/host.json`
- `function/local.settings.json` (local only)
- `function/function_app.py`
- `function/supply_pressure_scorer.py`
- `function/trader_advice.py`

### Backend behavior
- Cache the model and features in memory across warm invocations
- Load model from Blob Storage on cold start
- Build a future dataframe with known or default feature values
- Predict using Prophet
- Return structured JSON including:
  - `dominant_signal`
  - `intensity`
  - `glut_score`
  - `shortage_score`
  - `forecast_dates`
  - `forecast_values`
  - `ci_lower`
  - `ci_upper`
  - `price_change_pct`
  - `confidence_days`
  - `trader_action`

### Advice generation

The dashboard text must be generated by rule-based templates in `function/trader_advice.py` and should not use any LLM service.

### Acceptance

- Function starts locally with `func start`
- The endpoint returns valid JSON
- Model loads from Blob Storage with the configured env vars
- Response text is in Bahasa Indonesia
''',
    '04_model_training.md': '''# PROMPT 04 — Model Training, Backtest, and Dashboard

> Read `00_PROJECT_CONTEXT.md` first.
> This module combines model training and the Streamlit dashboard into one cohesive step.

## Part 1 — Model training and validation

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

## Part 2 — Streamlit dashboard

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
'''
}
for name, content in files.items():
    p = base / name
    p.write_text(content, encoding='utf-8')
    print('wrote', name)
for duplicate in ['01_DATA_PIPELINE.md', '02_MODEL.md', '03_FUNCTION.md', '04_DASHBOARD.md']:
    d = base / duplicate
    if d.exists():
        d.unlink()
        print('removed', duplicate)
