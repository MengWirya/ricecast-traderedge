# PROMPT 03 — Feature Engineering

Context: RiceCast TraderEdge. This notebook builds the price momentum and
supply pressure features that make TraderEdge different from a generic price
forecast. It reads `data/processed/master_df.csv` and outputs an updated CSV
with all features ready for Prophet.

---

## What you are building

`notebooks/02_feature_engineering.ipynb` — adds these features to master_df:

| Feature | Description | TraderEdge role |
|---------|-------------|-----------------|
| `price_mom_1m` | 1-month % price change | Short-term signal |
| `price_mom_3m` | 3-month % price change | Medium-term trend |
| `price_accel` | mom_1m minus mom_3m | Accelerating vs decelerating pressure |
| `production_dev_pct` | Already in master_df | Supply deviation from seasonal norm |
| `harvest_window` | Already in master_df | Binary harvest season flag |
| `lean_season` | Already in master_df | Binary lean season flag |
| `harvest_proximity_days` | Already in master_df | Days to next harvest |
| `rainfall_dev_pct` | Already in master_df (downweighted) | Climate context |

---

## Step 1 — Load and inspect

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv('data/processed/master_df.csv', parse_dates=['ds'])
df = df.sort_values('ds').reset_index(drop=True)
print(df.shape)
print(df.dtypes)
print(df.head(3))
```

Assert `df['y'].isna().sum() == 0` before proceeding.

---

## Step 2 — Price momentum features

```python
# 1-month and 3-month percentage change
df['price_mom_1m'] = df['y'].pct_change(periods=1)
df['price_mom_3m'] = df['y'].pct_change(periods=3)

# Acceleration: is the trend speeding up or slowing down?
# Positive accel = price moving faster than 3m trend → stronger signal
# Negative accel = price stabilising relative to trend
df['price_accel'] = df['price_mom_1m'] - df['price_mom_3m']
```

After computing, fill the first 3 NaN rows (from pct_change lag) with 0:
```python
df[['price_mom_1m','price_mom_3m','price_accel']] = \
    df[['price_mom_1m','price_mom_3m','price_accel']].fillna(0)
```

**Plot:** produce a 2-panel chart:
- Panel 1: Raw price `y` over time with `harvest_window` shaded regions
- Panel 2: `price_mom_3m` over time with a horizontal 0 line

Save the chart as `data/processed/eda_price_momentum.png`.

---

## Step 3 — Validate all features

Print a correlation matrix of all features vs `y`:

```python
feature_cols = [
    'price_mom_1m', 'price_mom_3m', 'price_accel',
    'production_dev_pct', 'harvest_window', 'lean_season',
    'harvest_proximity_days', 'rainfall_dev_pct'
]
corr = df[feature_cols + ['y']].corr()['y'].sort_values(ascending=False)
print("Feature correlations with price (y):")
print(corr.round(3))
```

Flag any feature with correlation > 0.8 (multicollinearity risk) with a
printed warning. Do not remove it — just warn.

---

## Step 4 — Seasonal decomposition plot

Use `statsmodels` to decompose the price series and save a plot:

```python
from statsmodels.tsa.seasonal import seasonal_decompose

decomp = seasonal_decompose(
    df.set_index('ds')['y'],
    model='multiplicative',
    period=12,
    extrapolate_trend='freq'
)
fig = decomp.plot()
fig.set_size_inches(10, 8)
plt.tight_layout()
plt.savefig('data/processed/eda_seasonal_decomp.png')
plt.show()
```

This visualises whether Prophet's multiplicative seasonality assumption is valid.
If the seasonal component is clearly not multiplicative, note it as a limitation
in the model card.

---

## Step 5 — Stationarity check

Run an Augmented Dickey-Fuller test on the price series:

```python
from statsmodels.tsa.stattools import adfuller

result = adfuller(df['y'].dropna())
print(f"ADF Statistic: {result[0]:.4f}")
print(f"p-value: {result[1]:.4f}")
print(f"Series is {'stationary' if result[1] < 0.05 else 'non-stationary (expected for prices)'}")
```

Non-stationary is expected and fine — Prophet handles this internally.
Just print the result for the model card.

---

## Step 6 — Supply pressure visual

Create a scatter plot that is the core motivation for TraderEdge:

```python
fig, ax = plt.subplots(figsize=(10, 5))
scatter = ax.scatter(
    df['production_dev_pct'],
    df['price_mom_3m'],
    c=df['harvest_window'],
    cmap='RdYlGn_r',
    alpha=0.7,
    s=60
)
ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
ax.axvline(0, color='gray', linestyle='--', linewidth=0.8)
ax.set_xlabel('Production deviation from seasonal mean (supply signal)')
ax.set_ylabel('3-month price momentum')
ax.set_title('Supply vs Price Momentum — East Java Rice\n'
             '(Green = harvest window, Red = lean season)')
plt.colorbar(scatter, label='harvest_window')
plt.tight_layout()
plt.savefig('data/processed/eda_supply_vs_momentum.png')
plt.show()
```

This chart is your "why TraderEdge" slide for the presentation.
Top-left quadrant = glut signal (high supply, falling prices).
Bottom-right quadrant = shortage signal (low supply, rising prices).

---

## Step 7 — Save enriched dataframe

```python
df.to_csv('data/processed/master_df.csv', index=False)
print("Saved enriched master_df.csv")
print(f"Final columns: {df.columns.tolist()}")
print(f"Final shape: {df.shape}")
```

Also update the train/holdout splits with the new features:
```python
train_df   = df[df['ds'] < '2024-01-01']
holdout_df = df[df['ds'] >= '2024-01-01']
train_df.to_csv('data/processed/train_df.csv', index=False)
holdout_df.to_csv('data/processed/holdout_df.csv', index=False)
```

---

## Acceptance criteria

- [ ] `master_df.csv` now contains: `ds`, `y`, `price_mom_1m`, `price_mom_3m`,
  `price_accel`, `production_dev_pct`, `harvest_window`, `lean_season`,
  `harvest_proximity_days`, `rainfall_dev_pct`
- [ ] No NaN values in any feature column
- [ ] Three PNG charts saved to `data/processed/`
- [ ] Correlation table printed — no features above 0.8 correlation with `y`
  (or warnings printed if there are)
- [ ] Notebook runs top-to-bottom without errors
