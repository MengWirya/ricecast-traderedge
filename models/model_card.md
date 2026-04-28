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
| production_dev_pct | Continuous | 0.3 | Supply deviation from seasonal norm |
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
