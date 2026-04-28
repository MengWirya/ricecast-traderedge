# PROMPT 01 — Project Setup & Environment

You are helping me build **RiceCast TraderEdge**, an AI-powered supply pressure
detector for UMKM rice traders at pasar induk (wholesale markets) in Malang,
East Java, Indonesia.

This is the **first step**: scaffold the full project structure, create all
configuration files, and set up the Python environment.

---

## Your task

Create the complete project scaffold exactly as specified below.
Do not skip any file. Generate the actual file content, not placeholders.

---

## Step 1 — Create folder structure

Create the following directory tree from scratch:

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

## Step 2 — Create `requirements-dev.txt`

This is for local development (notebooks + testing). Generate this file:

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

## Step 3 — Create `function/requirements.txt`

This is the slimmed-down requirements for the Azure Function only (no notebook
extras, no dev tools):

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

## Step 4 — Create `function/host.json`

Standard Azure Functions v2 host configuration:

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

---

## Step 5 — Create `function/local.settings.json`

Local dev only — **never commit this file**:

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

## Step 6 — Create `.env.example`

Template for environment variables (commit this, not the real `.env`):

```
# Azure Blob Storage
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
BLOB_CONTAINER_NAME=ricecast
MODEL_BLOB_NAME=prophet_model.pkl

# Dashboard → Function URL
FUNCTION_ENDPOINT=https://your-function-app.azurewebsites.net/api/forecast
```

---

## Step 7 — Create `.gitignore`

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

## Step 8 — Create `models/model_card.md`

Blank template to fill in after training:

```markdown
# RiceCast TraderEdge — Model Card

## Model details
- **Type:** Facebook Prophet (multiplicative seasonality)
- **Version:** (fill after training)
- **Trained:** (date)
- **Training data:** (date range and sources)

## Features
| Feature | Type | Prior scale | Description |
|---------|------|-------------|-------------|
| price_mom_3m | Continuous | 0.5 | 3-month price % change |
| price_accel | Continuous | 0.3 | Momentum acceleration |
| harvest_window | Binary | 0.4 | East Java harvest season |
| production_dev_pct | Continuous | 0.3 | BPS monthly production deviation |
| rainfall_dev_pct | Continuous | 0.02 | BMKG rainfall deviation (downweighted) |

## Training parameters
- seasonality_mode: multiplicative
- yearly_seasonality: True (10 Fourier terms)
- weekly_seasonality: False
- changepoint_prior_scale: 0.05
- interval_width: 0.80

## Validation results
- Training period: (fill)
- Holdout period: (fill)
- Directional accuracy: (fill)%
- Key backtest events:
  - Post-harvest glut Q2 2022: signal (X) weeks before peak
  - El Niño shortage Q3 2023: signal (X) weeks before peak

## Known limitations
- Monthly resolution only
- East Java / Malang focus — not generalisable
- Production feature uses provincial data, not regency-level
- Historical patterns may not capture structural market changes
```

---

## Step 9 — Create empty notebook files

Create these four empty `.ipynb` files in the `notebooks/` folder.
Each should be a valid empty Jupyter notebook (just the minimal JSON skeleton):

- `notebooks/01_eda.ipynb`
- `notebooks/02_feature_engineering.ipynb`
- `notebooks/03_model_training.ipynb`
- `notebooks/04_backtest_analysis.ipynb`

Minimal notebook JSON:
```json
{
 "cells": [],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": { "name": "python", "version": "3.11.0" }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

---

## Step 10 — Create Python virtual environment

Run these commands:

```bash
cd ricecast-traderedge
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

If `prophet` install fails (common on some systems), try:
```bash
pip install pystan==3.4.0
pip install prophet==1.1.5
```

---

## Done — verification checklist

After completing all steps, run:
```bash
python -c "import prophet; import pandas; import streamlit; print('All core imports OK')"
pytest --collect-only   # should show 0 tests collected (empty tests/ dir)
```

Both commands should run without errors.

Report back with the output of these two commands.
