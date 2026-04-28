# PROMPT 02 â€” Data Pipeline, Model Training, and Backtest

> Read `00_PROJECT_CONTEXT.md` first.
> This module covers both the data pipeline and the first model training/backtest notebook.

## Part 1 â€” Data pipeline

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

### Step 1 â€” WFP / HDX price data

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

### Step 2 â€” PIHPS Malang price data

Write `load_pihps_malang(path)`:
- Read Excel, skip first 2 rows
- Inspect and normalize column names
- Identify the date column and medium rice price column
- Convert date with `dayfirst=True`
- Drop null price rows
- Resample to monthly mean
- Rename to `ds`, `y_pihps`
- If file is missing, return `None` with warning

### Step 3 â€” BPS production data

Write `load_bps_production(path)`:
- Read Excel, skip first 3 rows
- Print columns for inspection
- Identify Jawa Timur production column and date/month column
- Compute seasonal mean by month
- Create `production_dev_pct` = (actual - mean) / mean
- Return `ds`, `production_gkg`, `production_dev_pct`

### Step 4 â€” BMKG rainfall data

Write `load_bmkg_rainfall(path)`:
- Read CSV and inspect columns
- Identify date and rainfall columns
- Resample to monthly totals if needed
- Compute `rainfall_dev_pct` by monthly seasonal mean
- Return `ds`, `rainfall_mm`, `rainfall_dev_pct`

### Step 5 â€” Harvest calendar features

Write `build_harvest_features(date_series)`:
- `harvest_window` = 1 for months [3,4,5,7,8,9]
- `lean_season` = 1 for months [10,11,12,1,2]
- `harvest_proximity_days` = days until next March 1 if not in harvest
- Return columns `ds`, `harvest_window`, `lean_season`, `harvest_proximity_days`

### Step 6 â€” Select price series

Write `select_price_series(df_wfp, df_pihps)`:
- If both present: merge on `ds`, average `y_wfp` and `y_pihps`
- If only WFP present: use `y_wfp`
- If only PIHPS present: use `y_pihps`
- Assert final series has at least 48 rows
- Return `ds`, `y`

### Step 7 â€” Build master dataframe

Write `build_master_df(price_df, bps_df, bmkg_df, harvest_df)`:
- Start from `price_df`
- Left-join `bps_df`, `bmkg_df`, `harvest_df`
- Fill missing `production_dev_pct` and `rainfall_dev_pct` with 0
- Drop rows with null `y`
- Save `data/processed/master_df.csv`
- Return final dataframe

### Step 8 â€” Data quality report

Print a formatted report showing:
- price source used
- date range
- total rows
- missing `y`
- missing feature fills
- feature summary counts
- final columns

### Step 9 â€” Train / holdout split

Save split CSVs:
- `train_df.csv` for `ds < 2024-01-01`
- `holdout_df.csv` for `ds >= 2024-01-01`

---

## Part 2 â€” Model training & backtest

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
- Q3 2023 El NiÃ±o shortage

Backtest should demonstrate lead time before the event and support the supply pressure narrative.
