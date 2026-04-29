# Model Card — prophet_model.pkl

## Model overview
- Type: Facebook Prophet (time-series forecasting)
- Task: Supply pressure signal for rice traders, Pasar Induk Malang, Jawa Timur
- Seasonality mode: **additive** (selected based on EDA — seasonal factor range 0.041)
- Interval width: 80% confidence interval

## Training data
- Period: 2016-10-01 → 2023-12-01
- Rows: 52 monthly observations
- Source: WFP/HDX Indonesia Food Prices (Jawa Timur rice series)

## Features
| Feature | Prior scale | Role |
|---|---|---|
| production_dev_pct | 0.5 | Primary supply signal (IEEE 2018-2023 + BPS 2025-2026) |
| price_mom_3m | 0.5 | 3-month price momentum |
| price_accel | 0.3 | Momentum acceleration |
| harvest_window | 0.4 | East Java harvest season binary |
| rainfall_dev_pct | 0.02 | Supporting only (downweighted) |

## Validation results
- Directional accuracy (holdout): 70.8%
- MAE: Rp 10,810/kg
- MAPE: 76.0%

## Backtest results
- Post-Panen Glut Q2 2022: lead time = 0 weeks
- El Niño Shortage Q3 2023: lead time = 0 weeks

## Known limitations
1. Monthly data resolution — sub-monthly timing cannot be detected
2. 2024 production data is gap-filled using 5-year harvest weight average
3. Rainfall feature is annual → monthly distributed (not station-level daily)
4. Confidence intervals span ±10-25% of price level — directional signal only
5. Model calibrated to Jawa Timur — do not apply to other provinces without retraining
6. Seasonality mode changed to additive (EDA finding: seasonal factor range 0.041 < 0.05)

## Output interpretation
Post-processed to GLUT/SHORTAGE/NEUTRAL signal + HIGH/MEDIUM/LOW intensity.
Do NOT expose raw yhat as a precise price prediction.
Designed for pasar induk wholesale traders in Malang area only.

## Files
- prophet_model.pkl — serialized model (joblib)
- forecast_plot.png — full forecast visualization
- components_plot.png — trend + seasonality decomposition
- backtest_chart.png — hero backtest visualization
