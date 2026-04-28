# PROMPT 04 — Model Training & Backtest

Context: RiceCast TraderEdge. This is the core ML notebook. It trains the
Prophet model, runs the backtest against two known supply imbalance events,
and exports the trained model as a pkl file.

**This is the most important notebook. The backtest is the hero of the demo.**

---

## Step 1 — Load data

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import joblib
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from sklearn.metrics import mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

train_df   = pd.read_csv('data/processed/train_df.csv', parse_dates=['ds'])
holdout_df = pd.read_csv('data/processed/holdout_df.csv', parse_dates=['ds'])

print(f"Training rows: {len(train_df)} ({train_df['ds'].min()} to {train_df['ds'].max()})")
print(f"Holdout rows:  {len(holdout_df)} ({holdout_df['ds'].min()} to {holdout_df['ds'].max()})")
```

---

## Step 2 — Define and fit Prophet model

Use EXACTLY these parameters. Do not change them without documenting why:

```python
m = Prophet(
    seasonality_mode='multiplicative',
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    changepoint_prior_scale=0.05,       # conservative — prevents overfitting
    seasonality_prior_scale=10.0,
    interval_width=0.80,                # 80% CI — honest, not overclaiming
    n_changepoints=25,
)

# Add Fourier terms for dual harvest cycle (main + secondary harvest)
m.add_seasonality(name='harvest_cycle', period=365.25/2, fourier_order=5)

# Primary features (higher prior = more influence allowed)
m.add_regressor('price_mom_3m',       prior_scale=0.5, standardize=True)
m.add_regressor('price_accel',        prior_scale=0.3, standardize=True)
m.add_regressor('production_dev_pct', prior_scale=0.3, standardize=True)
m.add_regressor('harvest_window',     prior_scale=0.4, standardize=False)

# Supporting features (lower prior = less influence)
m.add_regressor('lean_season',              prior_scale=0.2, standardize=False)
m.add_regressor('harvest_proximity_days',   prior_scale=0.1, standardize=True)
m.add_regressor('rainfall_dev_pct',         prior_scale=0.02, standardize=True)

print("Fitting model on training data...")
m.fit(train_df)
print("Model fitted successfully.")
```

---

## Step 3 — In-sample component plot

Visualise what Prophet learned about each component:

```python
# Plot components on training data
fig = m.plot_components(m.predict(train_df))
fig.suptitle('Prophet Components — Training Data (East Java Rice)', y=1.02)
plt.tight_layout()
plt.savefig('data/processed/model_components.png', bbox_inches='tight')
plt.show()
print("Component plot saved.")
```

Inspect the yearly seasonality component. It should show a dip around March–May
(post-harvest glut) and a rise around October–February (lean season shortage).
If the pattern is inverted or flat, note it as a limitation.

---

## Step 4 — Holdout forecast

Generate forecast for the holdout period plus 3 months ahead:

```python
def build_future_df(model, periods_ahead, last_known_df):
    """Build future dataframe with feature values for forecasting."""
    future = model.make_future_dataframe(
        periods=periods_ahead,
        freq='MS',
        include_history=True
    )
    # For holdout period, merge actual feature values
    feature_cols = [
        'price_mom_3m', 'price_accel', 'production_dev_pct',
        'harvest_window', 'lean_season',
        'harvest_proximity_days', 'rainfall_dev_pct'
    ]
    all_data = pd.concat([
        last_known_df[['ds'] + feature_cols],
        holdout_df[['ds'] + feature_cols]
    ]).drop_duplicates('ds')
    future = future.merge(all_data, on='ds', how='left')
    # Fill forward for any future dates beyond holdout
    future[feature_cols] = future[feature_cols].fillna(method='ffill')
    future[feature_cols] = future[feature_cols].fillna(0)
    return future

future = build_future_df(m, periods_ahead=3, last_known_df=train_df)
forecast = m.predict(future)
print(f"Forecast generated: {len(forecast)} rows")
```

---

## Step 5 — Directional accuracy on holdout

```python
# Merge forecast with actual holdout values
eval_df = holdout_df[['ds','y']].merge(
    forecast[['ds','yhat','yhat_lower','yhat_upper']],
    on='ds', how='inner'
)

# Directional accuracy: did the model predict the right direction of change?
eval_df['actual_dir']    = np.sign(eval_df['y'].diff())
eval_df['predicted_dir'] = np.sign(eval_df['yhat'].diff())
eval_df = eval_df.dropna()

dir_accuracy = (eval_df['actual_dir'] == eval_df['predicted_dir']).mean()
mae = mean_absolute_error(eval_df['y'], eval_df['yhat'])
mape = (abs(eval_df['y'] - eval_df['yhat']) / eval_df['y']).mean()

ci_width_mean = ((eval_df['yhat_upper'] - eval_df['yhat_lower']) / eval_df['y']).mean()

print(f"\n=== HOLDOUT EVALUATION ===")
print(f"Directional accuracy: {dir_accuracy:.1%}")
print(f"MAE:                  {mae:.0f} IDR/kg")
print(f"MAPE:                 {mape:.1%}")
print(f"Mean CI width:        {ci_width_mean:.1%} of price")
print(f"==========================")
print(f"\nNote: For TraderEdge, directional accuracy is the key metric.")
print(f"Wide CI is expected and is shown honestly in the dashboard.")
```

---

## Step 6 — THE HERO: Backtest on known events

This is the most important section. Run backtests on two documented events.

### Event 1: Post-harvest glut Q2 2022

```python
# Define event window
event1 = {
    'label': 'Post-Panen Glut Q2 2022',
    'signal_search_start': '2022-02-01',
    'event_start': '2022-04-01',
    'event_peak':  '2022-05-01',   # expected price dip (glut = price falls)
    'type': 'GLUT'
}

# Get forecast values for this window
e1_fc = forecast[
    (forecast['ds'] >= event1['signal_search_start']) &
    (forecast['ds'] <= event1['event_peak'])
][['ds','yhat','yhat_lower','yhat_upper']]

# Find first month where model predicted downward pressure
# (price below 3-month average)
rolling_mean = forecast['yhat'].rolling(3).mean()
forecast['below_trend'] = forecast['yhat'] < rolling_mean

first_signal = forecast[
    (forecast['ds'] >= event1['signal_search_start']) &
    (forecast['below_trend'] == True)
]['ds'].min()

print(f"\n{event1['label']}:")
print(f"  First downward signal: {first_signal}")
print(f"  Event peak (actual):   {event1['event_peak']}")
if pd.notna(first_signal):
    lead_weeks = (pd.to_datetime(event1['event_peak']) - first_signal).days // 7
    print(f"  Lead time: {lead_weeks} weeks")
else:
    print("  No clear signal detected in this window.")
```

### Event 2: El Niño shortage Q3 2023

```python
event2 = {
    'label': 'El Niño Shortage Q3 2023',
    'signal_search_start': '2023-05-01',
    'event_start': '2023-07-01',
    'event_peak':  '2023-09-01',   # expected price spike (shortage = price rises)
    'type': 'SHORTAGE'
}

e2_fc = forecast[
    (forecast['ds'] >= event2['signal_search_start']) &
    (forecast['ds'] <= event2['event_peak'])
][['ds','yhat','yhat_lower','yhat_upper']]

# Find first month where model predicted upward pressure
forecast['above_trend'] = forecast['yhat'] > rolling_mean

first_signal_2 = forecast[
    (forecast['ds'] >= event2['signal_search_start']) &
    (forecast['above_trend'] == True)
]['ds'].min()

print(f"\n{event2['label']}:")
print(f"  First upward signal:   {first_signal_2}")
print(f"  Event peak (actual):   {event2['event_peak']}")
if pd.notna(first_signal_2):
    lead_weeks_2 = (pd.to_datetime(event2['event_peak']) - first_signal_2).days // 7
    print(f"  Lead time: {lead_weeks_2} weeks")
```

### Backtest chart (the presentation slide)

```python
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

for i, (event, first_sig, ax) in enumerate([
    (event1, first_signal, axes[0]),
    (event2, first_signal_2, axes[1])
]):
    # Filter to relevant window
    window_start = pd.to_datetime(event['signal_search_start']) - pd.DateOffset(months=3)
    window_end   = pd.to_datetime(event['event_peak']) + pd.DateOffset(months=2)

    fc_window = forecast[(forecast['ds'] >= window_start) & (forecast['ds'] <= window_end)]
    actual_window = pd.concat([train_df, holdout_df])
    actual_window = actual_window[
        (actual_window['ds'] >= window_start) & (actual_window['ds'] <= window_end)
    ]

    # Plot CI band
    ax.fill_between(fc_window['ds'], fc_window['yhat_lower'], fc_window['yhat_upper'],
                    alpha=0.2, color='steelblue', label='80% CI')
    # Plot forecast
    ax.plot(fc_window['ds'], fc_window['yhat'], color='steelblue',
            linewidth=2, label='Prophet forecast')
    # Plot actuals
    ax.plot(actual_window['ds'], actual_window['y'], 'ko-',
            markersize=4, linewidth=1.5, label='Actual price')

    # Mark signal date
    if pd.notna(first_sig):
        ax.axvline(first_sig, color='orange', linestyle='--', linewidth=2,
                   label=f'Signal detected: {first_sig.strftime("%b %Y")}')

    # Mark event peak
    ax.axvline(pd.to_datetime(event['event_peak']), color='red', linestyle='-',
               linewidth=2, alpha=0.7, label=f'Event peak: {event["event_peak"]}')

    ax.set_title(f'{event["label"]} — Backtest')
    ax.set_ylabel('Price (IDR/kg)')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('data/processed/backtest_hero_chart.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nBacktest chart saved: data/processed/backtest_hero_chart.png")
print("This is your hero slide. Use it in the presentation.")
```

---

## Step 7 — Trader P&L simulation

Simulate what happens if a trader follows the signal vs ignores it:

```python
def simulate_trader_pnl(forecast_df, actual_df, event, signal_date,
                         stock_kg=1000, storage_cost_per_kg_month=50):
    """
    Simple P&L simulation:
    - Trader WITH signal: buys/holds based on signal recommendation
    - Trader WITHOUT signal: follows business-as-usual (buys at regular intervals)
    """
    event_start = pd.to_datetime(event['event_start'])
    event_peak  = pd.to_datetime(event['event_peak'])

    prices = actual_df.set_index('ds')['y']

    if event['type'] == 'SHORTAGE':
        # Signal says: buy now before price rises
        price_at_signal  = prices.get(signal_date, prices.iloc[-1])
        price_at_peak    = prices.get(event_peak, prices.iloc[-1])
        price_at_start   = prices.get(event_start, prices.iloc[-1])

        pnl_with_signal    = (price_at_peak - price_at_signal) * stock_kg
        pnl_without_signal = (price_at_peak - price_at_start) * stock_kg
        advantage = pnl_with_signal - pnl_without_signal
        print(f"\n{event['label']} — Trader P&L Simulation (Shortage)")
        print(f"  Buy price (with signal):    {price_at_signal:,.0f} IDR/kg")
        print(f"  Buy price (without signal): {price_at_start:,.0f} IDR/kg")
        print(f"  Sell price at peak:         {price_at_peak:,.0f} IDR/kg")
        print(f"  P&L with signal:    {pnl_with_signal:+,.0f} IDR")
        print(f"  P&L without signal: {pnl_without_signal:+,.0f} IDR")
        print(f"  Signal advantage:   {advantage:+,.0f} IDR on {stock_kg}kg")
    else:
        # GLUT: Signal says: sell now before price falls
        price_at_signal  = prices.get(signal_date, prices.iloc[-1])
        price_at_peak    = prices.get(event_peak, prices.iloc[-1])
        price_at_start   = prices.get(event_start, prices.iloc[-1])

        pnl_with_signal    = (price_at_signal - price_at_peak) * stock_kg
        pnl_without_signal = (price_at_start - price_at_peak) * stock_kg
        advantage = pnl_with_signal - pnl_without_signal
        print(f"\n{event['label']} — Trader P&L Simulation (Glut)")
        print(f"  Sell price (with signal):    {price_at_signal:,.0f} IDR/kg")
        print(f"  Sell price (without signal): {price_at_start:,.0f} IDR/kg")
        print(f"  Price floor at glut peak:    {price_at_peak:,.0f} IDR/kg")
        print(f"  P&L with signal:    {pnl_with_signal:+,.0f} IDR")
        print(f"  P&L without signal: {pnl_without_signal:+,.0f} IDR")
        print(f"  Signal advantage:   {advantage:+,.0f} IDR on {stock_kg}kg")

all_df = pd.concat([train_df, holdout_df])
if pd.notna(first_signal):
    simulate_trader_pnl(forecast, all_df, event1, first_signal)
if pd.notna(first_signal_2):
    simulate_trader_pnl(forecast, all_df, event2, first_signal_2)
```

---

## Step 8 — Export model

```python
import os
os.makedirs('models', exist_ok=True)

joblib.dump(m, 'models/prophet_model.pkl')
print(f"Model saved: models/prophet_model.pkl")
print(f"File size: {os.path.getsize('models/prophet_model.pkl') / 1024:.1f} KB")

# Verify round-trip
m_loaded = joblib.load('models/prophet_model.pkl')
test_pred = m_loaded.predict(train_df.head(3))
assert len(test_pred) == 3, "Round-trip test failed"
print("Round-trip serialisation test: PASSED")
```

---

## Step 9 — Update model_card.md

Append the actual results to `models/model_card.md`:

```python
model_card_update = f"""
## Actual training results (fill in after running)
- Directional accuracy: {dir_accuracy:.1%}
- MAE: {mae:.0f} IDR/kg
- MAPE: {mape:.1%}
- Mean CI width: {ci_width_mean:.1%}
- Backtest event 1 lead time: {lead_weeks if pd.notna(first_signal) else 'not detected'} weeks
- Backtest event 2 lead time: {lead_weeks_2 if pd.notna(first_signal_2) else 'not detected'} weeks
"""
with open('models/model_card.md', 'a') as f:
    f.write(model_card_update)
print("model_card.md updated.")
```

---

## Acceptance criteria

- [ ] Model fits without errors
- [ ] Holdout directional accuracy ≥ 50% (better than coin flip)
  — if below 50%, do NOT hide it, add a note to model_card.md
- [ ] `data/processed/backtest_hero_chart.png` saved and shows two event windows
- [ ] `models/prophet_model.pkl` exists and passes round-trip test
- [ ] P&L simulation printed for at least one event
- [ ] `model_card.md` updated with actual results
