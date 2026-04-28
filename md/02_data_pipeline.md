# PROMPT 02 — Data Pipeline

Context: I am building **RiceCast TraderEdge**, a supply pressure detector for
UMKM rice traders in Malang, East Java. This prompt covers loading, cleaning,
and merging all datasets into a single `master_df.csv`.

Assume the project folder structure from `01_project_setup.md` already exists.

---

## What you are building

A data pipeline notebook (`notebooks/01_eda.ipynb`) that:
1. Loads all raw data sources
2. Cleans and validates each one
3. Resamples everything to monthly frequency
4. Merges into one `master_df.csv`
5. Prints a data quality report

---

## Data sources — file locations

Place the downloaded raw files in `data/raw/`. The pipeline expects these names:

| Filename | Source | What it contains |
|----------|--------|-----------------|
| `wfp_food_prices_idn.csv` | WFP/HDX humdata.org | Indonesia food prices by market, 2007–2024 |
| `pihps_malang_beras.xlsx` | PIHPS bi.go.id/hargapangan | Malang daily rice prices, manual export |
| `bps_produksi_padi_bulanan.xlsx` | bps.go.id statistics table (bulanan) | Monthly rice production by province |
| `bmkg_rainfall_jatim.csv` | BMKG dataonline.bmkg.go.id | Monthly rainfall, East Java stations |

> If a file is missing, the pipeline should log a warning and continue with
> the sources that are available. Do not crash on missing files.

---

## Step 1 — WFP / HDX price data

Write a function `load_wfp_prices(path)` that:

1. Reads the CSV
2. Prints the column names and first 5 rows for inspection
3. Filters rows where `adm1_name` contains "Jawa Timur" (case-insensitive)
4. Filters rows where `commodity` contains "Rice" (case-insensitive)
5. Keeps only columns: `date`, `market`, `commodity`, `price`, `unit`
6. Converts `date` to datetime
7. Resamples to monthly mean price (resample on `date`, take mean of `price`)
8. Renames to `ds` (datetime, month-start frequency) and `y_wfp` (price)
9. Returns a clean monthly dataframe

Expected output shape: ~200 rows × 2 columns (`ds`, `y_wfp`)

Validation check: assert that `ds` min is before 2015 and max is after 2022.

---

## Step 2 — PIHPS Malang price data

Write a function `load_pihps_malang(path)` that:

1. Reads the Excel file, skipping the first 2 header rows
2. Inspects column names — print them (they may be in Indonesian)
3. Identifies the date column and the "Beras Medium I" or "Beras Medium" price column
   - If neither exists, find the closest match and log a warning
4. Converts date column to datetime (use `dayfirst=True` for Indonesian date format)
5. Drops rows where price is null
6. Resamples to monthly mean
7. Renames to `ds` and `y_pihps`
8. Returns a clean monthly dataframe

Expected output shape: ~36–48 rows × 2 columns

If the file does not exist, return `None` and print a warning.

---

## Step 3 — BPS monthly production data

Write a function `load_bps_production(path)` that:

1. Reads the Excel, skipping first 3 header rows
2. Prints column names for inspection
3. Identifies the "Jawa Timur" column and a date/month column
4. Extracts just those two columns
5. Computes `production_dev_pct`:
   - For each month (Jan–Dec), compute the historical mean production
   - Deviation = (actual - mean) / mean
   - Positive = above-normal supply → glut risk
   - Negative = below-normal supply → shortage risk
6. Adds a `ds` column (construct from year + month, use month-start)
7. Returns dataframe with columns: `ds`, `production_gkg`, `production_dev_pct`

Expected output: ~84 rows (7 years × 12 months)

---

## Step 4 — BMKG rainfall data

Write a function `load_bmkg_rainfall(path)` that:

1. Reads the CSV
2. Prints columns for inspection
3. Identifies the date and rainfall_mm columns
4. Aggregates to monthly if data is daily (take sum for rainfall)
5. Computes `rainfall_dev_pct`:
   - For each month (Jan–Dec), compute 5-year mean rainfall
   - Deviation = (actual - mean) / mean
6. Returns dataframe with columns: `ds`, `rainfall_mm`, `rainfall_dev_pct`

If the file does not exist, return `None` with a warning.

---

## Step 5 — Harvest calendar features

Write a function `build_harvest_features(date_range)` that:

1. Takes a list/series of dates
2. Returns a dataframe with these derived columns:

```python
# East Java rice harvest calendar (from BPS publications)
# Main harvest:      March, April, May      (bulan 3,4,5)
# Second harvest:    July, August, September (bulan 7,8,9)
# Lean season:       October–February        (bulan 10,11,12,1,2)

harvest_window    = 1 if month in [3,4,5,7,8,9] else 0
lean_season       = 1 if month in [10,11,12,1,2] else 0

# Days until next harvest window start
# If currently in harvest → 0
# If in lean season → count forward to March 1
harvest_proximity_days = ...  # continuous countdown feature
```

Return columns: `ds`, `harvest_window`, `lean_season`, `harvest_proximity_days`

---

## Step 6 — Price series decision logic

Write a function `select_price_series(df_wfp, df_pihps)` that:

1. If both are available: merge on `ds`, take mean of `y_wfp` and `y_pihps`
   as the final `y` column. Log "Using merged WFP + PIHPS price series."
2. If only WFP available: use `y_wfp` as `y`. Log warning.
3. If only PIHPS available: use `y_pihps` as `y`. Log warning.
4. Asserts that the final `y` has at least 48 rows (4 years minimum)
5. Returns dataframe with `ds` and `y` columns only

---

## Step 7 — Master merge

Write a function `build_master_df(price_df, bps_df, bmkg_df, harvest_df)` that:

1. Starts with `price_df` (ds, y) as the base
2. Left-joins `bps_df` on `ds` — keeps all price rows
3. Left-joins `bmkg_df` on `ds` if available (else skip)
4. Left-joins `harvest_df` on `ds`
5. Fills null `production_dev_pct` with 0 (neutral) — log how many were filled
6. Fills null `rainfall_dev_pct` with 0 — log how many were filled
7. Drops any rows where `y` is null
8. Prints final shape and date range
9. Saves to `data/processed/master_df.csv` with index=False
10. Returns the dataframe

---

## Step 8 — Data quality report

At the end of the notebook, print a formatted report:

```
=== DATA QUALITY REPORT ===
Price series:      [source names used]
Date range:        YYYY-MM to YYYY-MM
Total rows:        XX
Missing y:         0 (must be 0 — crash if not)
Missing prod_dev:  XX rows filled with 0
Missing rain_dev:  XX rows filled with 0

Feature summary:
  harvest_window=1:  XX rows (X.X%)
  lean_season=1:     XX rows (X.X%)
  price_mom_3m:      computed in next notebook
  production_dev_pct range: [min, max]

Columns: [list all column names]
===========================
```

---

## Step 9 — Train / holdout split

At the very end, split and save:

```python
# Training: 2018–2023 (inclusive)
# Holdout:  2024 onwards
train_df   = master_df[master_df['ds'] < '2024-01-01']
holdout_df = master_df[master_df['ds'] >= '2024-01-01']

train_df.to_csv('data/processed/train_df.csv', index=False)
holdout_df.to_csv('data/processed/holdout_df.csv', index=False)

print(f"Train rows:   {len(train_df)}")
print(f"Holdout rows: {len(holdout_df)}")
```

Assert train has at least 48 rows. Assert holdout has at least 6 rows.

---

## Acceptance criteria

The notebook is complete when:
- [ ] `data/processed/master_df.csv` exists and has no null `y` values
- [ ] `data/processed/train_df.csv` has ≥ 48 rows
- [ ] `data/processed/holdout_df.csv` has ≥ 6 rows
- [ ] The data quality report prints without errors
- [ ] The notebook runs top-to-bottom without crashes
  (missing optional files log warnings, they do not crash)
