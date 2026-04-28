# RiceCast TraderEdge — Master Project Context

> **Feed this file to your AI coding assistant FIRST, before any other file.**
> This gives the AI the full mental model of the project so every module it builds is consistent.

---

## What this project is

**RiceCast TraderEdge** is an AI-powered supply pressure detector for UMKM rice traders at pasar induk (wholesale markets) in Malang, East Java, Indonesia.

It does NOT predict exact rice prices. It outputs a **Supply Pressure Score** — a signal telling traders whether a glut or shortage is likely in the next 7–30 days — so they can make better buying and selling decisions.

**Target user:** A pedagang beras at Pasar Induk Gadang Malang who buys from farmers and sells to warung/retailers. They need to know: should I stock up now, or wait?

---

## The core output

A structured signal with four fields:

```
dominant_signal: "GLUT" | "SHORTAGE" | "NEUTRAL"
intensity:       "HIGH" | "MEDIUM" | "LOW"
trader_action:   "Bahasa Indonesia advice string"
confidence_days: 7–30 (how far ahead the signal is reliable)
```

Example output:
```json
{
  "dominant_signal": "GLUT",
  "intensity": "HIGH",
  "glut_score": 78,
  "shortage_score": 12,
  "trader_action": "Sinyal SURPLUS TINGGI: Harga kemungkinan turun dalam 2–3 minggu. Tunda pembelian stok besar. Negosiasi harga supplier lebih rendah sekarang.",
  "forecast_values": [13200, 13050, 12900, 12750],
  "ci_lower": [12400, 12100, 11800, 11500],
  "ci_upper": [14000, 14000, 14000, 13900],
  "confidence_days": 21
}
```

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Forecasting model | Facebook Prophet (Python) | Handles rice seasonality, interpretable, works on ~80 monthly data points |
| Backend | Azure Functions (Python, consumption plan) | Free tier, HTTP trigger, loads model pkl from Blob |
| Model storage | Azure Blob Storage | Stores prophet_model.pkl (~2MB) and cached CSVs |
| Frontend | Streamlit | Fast to build, easy to deploy on Azure App Service F1 free tier |
| Language | Python 3.11 | |

---

## Project folder structure

```
ricecast-traderedge/
├── notebooks/
│   ├── 01_eda.ipynb                  # Explore and understand data
│   ├── 02_feature_engineering.ipynb  # Build features, merge datasets
│   ├── 03_model_training.ipynb       # Train Prophet, export pkl
│   └── 04_backtest_analysis.ipynb    # Validate against 2022–2023 events
├── function/
│   ├── function_app.py               # Azure Function HTTP trigger (entry point)
│   ├── supply_pressure_scorer.py     # Glut/shortage scoring logic
│   ├── trader_advice.py              # NLG template engine (Bahasa Indonesia)
│   ├── requirements.txt              # prophet, pandas, azure-functions, etc.
│   └── host.json                     # Azure Function runtime config
├── dashboard/
│   ├── app.py                        # Streamlit app entry point
│   └── components/
│       ├── supply_gauge.py           # Plotly glut/shortage gauge
│       ├── forecast_chart.py         # Price history + forecast line chart
│       └── trader_action_card.py     # Signal/Reason/Action card
├── data/
│   ├── raw/                          # Downloaded CSVs (never commit to git)
│   ├── processed/                    # master_df.csv, train_df.csv, holdout_df.csv
│   └── sample/                       # 10-row sample for demo (safe to commit)
├── models/
│   ├── prophet_model.pkl             # Trained model artifact
│   └── model_card.md                 # Training metadata and accuracy notes
├── tests/
│   ├── test_supply_pressure_scorer.py
│   └── test_trader_advice.py
├── .env.example                      # Template for local environment variables
├── requirements-dev.txt              # Dev dependencies (jupyter, pytest, black)
└── README.md
```

---

## Data sources summary

| Dataset | Source | Role | How to get |
|---|---|---|---|
| WFP Indonesia Food Prices | data.humdata.org/dataset/wfp-food-prices-for-indonesia | PRIMARY price series (y) | Direct CSV download, no login |
| PIHPS Malang (Bank Indonesia) | bi.go.id/hargapangan | HIGH-quality daily Malang prices | Manual table export from web UI |
| BPS Monthly Rice Production | bps.go.id table MjUwNiMy | Supply deviation feature | Excel download from BPS table UI |
| BPS Jatim Kabupaten data | jatim.bps.go.id | Harvest calendar validation | Table download |
| BMKG Rainfall | dataonline.bmkg.go.id | Supporting regressor (downweighted) | Station CSV after free registration |

**Confirmed:** World Bank dataset explicitly covers JAWA TIMUR as a sub-national area (microdata.worldbank.org/index.php/catalog/6166).

---

## Prophet model specification

```python
from prophet import Prophet

m = Prophet(
    seasonality_mode='multiplicative',   # Rice prices scale seasonally
    yearly_seasonality=True,
    weekly_seasonality=False,            # Monthly data, no weekly pattern
    changepoint_prior_scale=0.05,        # Conservative — avoid overfitting
    interval_width=0.80                  # 80% CI — honest uncertainty
)

# Regressors and their prior scales:
m.add_regressor('production_dev_pct', prior_scale=0.5, standardize=True)   # Primary supply signal
m.add_regressor('price_mom_3m',       prior_scale=0.5, standardize=True)   # 3-month price momentum
m.add_regressor('price_accel',        prior_scale=0.3, standardize=True)   # Momentum acceleration
m.add_regressor('harvest_window',     prior_scale=0.4, standardize=False)  # Binary harvest dummy
m.add_regressor('rainfall_dev_pct',   prior_scale=0.02, standardize=True)  # Supporting only
```

**Training split:** 2018–2023 (train), 2024–2025 (holdout/backtest)
**Target variable:** Monthly mean rice price (IDR/kg), Beras Medium, Jawa Timur

---

## Supply pressure scoring logic

```python
def compute_supply_pressure(forecast_df, current_price):
    price_change_pct = (forecast_df['yhat'].iloc[-1] - current_price) / current_price
    harvest_near     = forecast_df['harvest_window'].sum() >= 2
    lean_near        = forecast_df['lean_season'].sum() >= 2

    # Glut: price falling + harvest approaching = oversupply risk
    glut_score = max(0, -price_change_pct * 300) + (25 if harvest_near else 0)
    glut_score = min(100, glut_score)

    # Shortage: price rising + lean season approaching = undersupply risk
    shortage_score = max(0, price_change_pct * 300) + (20 if lean_near else 0)
    shortage_score = min(100, shortage_score)

    dominant = 'GLUT' if glut_score > shortage_score else \
               'SHORTAGE' if shortage_score > glut_score else 'NEUTRAL'
    intensity = 'HIGH' if max(glut_score, shortage_score) >= 70 else \
                'MEDIUM' if max(glut_score, shortage_score) >= 40 else 'LOW'
    return dominant, intensity, glut_score, shortage_score
```

---

## Key constraints to respect in all code

1. **No managed Azure ML endpoints** — model is a pkl file loaded by Azure Functions directly
2. **No Azure OpenAI** — all alert text is rule-based templates, not LLM-generated
3. **No live scraping during demo** — all data is pre-downloaded and cached
4. **No exact price forecasts shown to users** — output is risk category + directional signal
5. **Bahasa Indonesia** for all user-facing text in the dashboard
6. **Wide confidence intervals must be shown** — never hide uncertainty

---

## Environment variables needed

```bash
# .env (local dev) — never commit this file
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
BLOB_CONTAINER_NAME=ricecast
MODEL_BLOB_NAME=prophet_model.pkl
AZURE_FUNCTION_URL=https://your-function.azurewebsites.net/api/forecast
```

---

## Backtest events to validate against

| Event | Period | Type | What to show |
|---|---|---|---|
| Post-harvest glut | Q2 2022 (Apr–Jun) | GLUT | Did glut_score > 60 before April 2022? |
| El Niño shortage | Q3 2023 (Jul–Oct) | SHORTAGE | Did shortage_score > 60 before July 2023? |

The backtest hero metric: **lead time in weeks** before the price extreme.

---

## What "done" looks like

- [ ] Notebook 01: All datasets loaded, no null errors, Jawa Timur confirmed in price data
- [ ] Notebook 02: master_df.csv written with all 5 features + ds + y columns
- [ ] Notebook 03: prophet_model.pkl saved, directional accuracy > 55% on holdout
- [ ] Notebook 04: Backtest charts show signal before Q2-2022 and Q3-2023 events
- [ ] Function: HTTP call returns valid JSON with all required fields
- [ ] Dashboard: Gauge, chart, and action card all render without errors
- [ ] End-to-end: Dashboard → Function → Model → Dashboard shows correct output
