# PROMPT 01 â€” Project Setup, Context, and Data Pipeline Overview

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

## Step 1 â€” Create folder structure

Create the following directory tree:

```
ricecast-traderedge/
â”œâ”€â”€ notebooks/
â”œâ”€â”€ function/
â”œâ”€â”€ dashboard/
â”‚   â””â”€â”€ components/
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/
â”‚   â”œâ”€â”€ processed/
â”‚   â””â”€â”€ sample/
â”œâ”€â”€ models/
â””â”€â”€ tests/
```

---

## Step 2 â€” requirements-dev.txt

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

## Step 3 â€” function/requirements.txt

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

## Step 4 â€” Azure Functions config

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

## Step 5 â€” .env.example

Create `.env.example`:

```
# Azure Blob Storage
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
BLOB_CONTAINER_NAME=ricecast
MODEL_BLOB_NAME=prophet_model.pkl

# Dashboard â†’ Function URL
FUNCTION_ENDPOINT=https://your-function-app.azurewebsites.net/api/forecast
```

---

## Step 6 â€” .gitignore

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

# Data â€” raw files never committed (too large, may contain sensitive info)
data/raw/
data/processed/

# Model artifact â€” large binary
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

## Step 7 â€” models/model_card.md template

Create `models/model_card.md`:

```markdown
# RiceCast TraderEdge â€” Model Card

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
- `confidence_days`: 7â€“30
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
- `glut_score` â€” price decline + harvest proximity
- `shortage_score` â€” price rise + lean season
- `dominant_signal` â€” the higher score if above threshold, else `NEUTRAL`
- `intensity` â€” `HIGH` / `MEDIUM` / `LOW`

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
