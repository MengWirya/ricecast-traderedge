# PROMPT 05 — Supply Pressure Scorer & Trader Advice Engine

Context: RiceCast TraderEdge. This prompt builds the two Python modules
that sit between the Prophet forecast and the user-facing output:

1. `function/supply_pressure_scorer.py` — converts Prophet forecast into a
   glut/shortage score (0–100)
2. `function/trader_advice.py` — generates Bahasa Indonesia advice text
   based on score + dominant signal

These are pure Python files, not notebooks.

---

## File 1: `function/supply_pressure_scorer.py`

Build this module completely. It must be fully unit-testable with no
external dependencies beyond pandas and numpy.

```python
"""
supply_pressure_scorer.py

Converts a Prophet forecast dataframe into a supply pressure assessment
for UMKM rice traders at pasar induk level.

No LLM calls. No external APIs. Pure Python + pandas + numpy.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


# ── Score thresholds ──────────────────────────────────────────────────────

INTENSITY_THRESHOLDS = {
    'HIGH':   70,   # score >= 70 → HIGH
    'MEDIUM': 40,   # score >= 40 → MEDIUM
    # else        → LOW
}


def score_to_intensity(score: float) -> str:
    """Convert 0–100 score to LOW / MEDIUM / HIGH."""
    if score >= INTENSITY_THRESHOLDS['HIGH']:
        return 'HIGH'
    elif score >= INTENSITY_THRESHOLDS['MEDIUM']:
        return 'MEDIUM'
    return 'LOW'


# ── Glut signal ───────────────────────────────────────────────────────────

def _compute_glut_score(
    price_change_pct: float,
    harvest_window_sum: int,
    production_dev_mean: float,
    ci_width_pct: float,
) -> float:
    """
    Glut = supply surplus → price falls.
    Score rises when: price falling + harvest approaching + above-normal production.
    Range: 0–100.
    """
    score = 0.0

    # Price direction component (primary)
    if price_change_pct < 0:
        score += min(50, abs(price_change_pct) * 300)

    # Harvest proximity component
    if harvest_window_sum >= 2:
        score += 20
    elif harvest_window_sum == 1:
        score += 10

    # Production deviation component
    if production_dev_mean > 0.10:   # > 10% above seasonal norm
        score += 20
    elif production_dev_mean > 0.05:
        score += 10

    # Uncertainty modifier: wide CI → reduce confidence slightly
    if ci_width_pct > 0.20:
        score *= 0.85

    return min(100.0, score)


# ── Shortage signal ───────────────────────────────────────────────────────

def _compute_shortage_score(
    price_change_pct: float,
    lean_season_sum: int,
    production_dev_mean: float,
    rainfall_dev_mean: float,
    ci_width_pct: float,
) -> float:
    """
    Shortage = supply deficit → price rises.
    Score rises when: price rising + lean season + below-normal production
                      + rainfall deficit.
    Range: 0–100.
    """
    score = 0.0

    # Price direction component (primary)
    if price_change_pct > 0:
        score += min(50, abs(price_change_pct) * 300)

    # Lean season proximity
    if lean_season_sum >= 2:
        score += 20
    elif lean_season_sum == 1:
        score += 10

    # Below-normal production
    if production_dev_mean < -0.10:
        score += 20
    elif production_dev_mean < -0.05:
        score += 10

    # Rainfall deficit (supporting signal, downweighted)
    if rainfall_dev_mean < -0.25:
        score += 10
    elif rainfall_dev_mean < -0.10:
        score += 5

    # Uncertainty modifier
    if ci_width_pct > 0.20:
        score *= 0.85

    return min(100.0, score)


# ── Main function ─────────────────────────────────────────────────────────

def compute_supply_pressure(
    forecast_df: pd.DataFrame,
    current_price: float,
    horizon_days: int = 30,
) -> Dict:
    """
    Main entry point. Takes Prophet forecast dataframe and returns
    a supply pressure assessment dict.

    Args:
        forecast_df:   Prophet .predict() output, including regressor columns.
                       Must contain: yhat, yhat_lower, yhat_upper,
                       harvest_window, lean_season, production_dev_pct,
                       rainfall_dev_pct
        current_price: Most recent actual price (IDR/kg)
        horizon_days:  Forecast horizon in days (default 30)

    Returns:
        Dict with keys:
            glut_score:          float 0–100
            shortage_score:      float 0–100
            dominant_signal:     'GLUT' | 'SHORTAGE' | 'NEUTRAL'
            intensity:           'LOW' | 'MEDIUM' | 'HIGH'
            price_change_pct:    float (expected % change)
            ci_width_pct:        float (CI width as % of price)
            driving_features:    dict of which features contributed most
    """
    # Use only the forward-looking portion of the forecast
    future_fc = forecast_df[forecast_df.index >= len(forecast_df) - (horizon_days // 30)]
    if len(future_fc) == 0:
        future_fc = forecast_df.tail(1)

    # Derived scalars
    yhat_mean        = future_fc['yhat'].mean()
    yhat_lower_mean  = future_fc['yhat_lower'].mean()
    yhat_upper_mean  = future_fc['yhat_upper'].mean()
    price_change_pct = (yhat_mean - current_price) / current_price
    ci_width_pct     = (yhat_upper_mean - yhat_lower_mean) / current_price

    harvest_window_sum   = future_fc.get('harvest_window', pd.Series([0])).sum()
    lean_season_sum      = future_fc.get('lean_season', pd.Series([0])).sum()
    production_dev_mean  = future_fc.get('production_dev_pct', pd.Series([0.0])).mean()
    rainfall_dev_mean    = future_fc.get('rainfall_dev_pct', pd.Series([0.0])).mean()

    # Compute signals
    glut_score = _compute_glut_score(
        price_change_pct, harvest_window_sum,
        production_dev_mean, ci_width_pct
    )
    shortage_score = _compute_shortage_score(
        price_change_pct, lean_season_sum,
        production_dev_mean, rainfall_dev_mean, ci_width_pct
    )

    # Determine dominant signal
    if glut_score > shortage_score and glut_score >= INTENSITY_THRESHOLDS['MEDIUM']:
        dominant_signal = 'GLUT'
        active_score    = glut_score
    elif shortage_score > glut_score and shortage_score >= INTENSITY_THRESHOLDS['MEDIUM']:
        dominant_signal = 'SHORTAGE'
        active_score    = shortage_score
    else:
        dominant_signal = 'NEUTRAL'
        active_score    = max(glut_score, shortage_score)

    intensity = score_to_intensity(active_score)

    # Identify top driving feature
    feature_contributions = {
        'price_momentum':     abs(price_change_pct) * 300,
        'harvest_timing':     harvest_window_sum * 10,
        'production_signal':  abs(production_dev_mean) * 100,
        'rainfall_deficit':   max(0, -rainfall_dev_mean) * 30,
    }
    top_feature = max(feature_contributions, key=feature_contributions.get)

    return {
        'glut_score':        round(glut_score),
        'shortage_score':    round(shortage_score),
        'dominant_signal':   dominant_signal,
        'intensity':         intensity,
        'price_change_pct':  round(price_change_pct * 100, 1),
        'ci_width_pct':      round(ci_width_pct * 100, 1),
        'yhat_mean':         round(yhat_mean),
        'top_driving_feature': top_feature,
        'driving_features':  {k: round(v) for k, v in feature_contributions.items()},
    }
```

---

## File 2: `function/trader_advice.py`

Build this module completely. All text is in Bahasa Indonesia.
No LLM. Pure template strings with dynamic interpolation.

```python
"""
trader_advice.py

Rule-based NLG engine for RiceCast TraderEdge.
Generates Bahasa Indonesia advice for pasar induk UMKM traders.

Design principles:
  - No LLM calls — templates are auditable and reproducible
  - Advice is directional, not precise — never claims exact prices
  - Always includes a confidence qualifier
  - Framed for bulk buying/selling decisions at wholesale level
"""

from typing import Dict

# ── Advice templates ──────────────────────────────────────────────────────
# Keys: (dominant_signal, intensity)

ADVICE_TEMPLATES = {

    ('GLUT', 'HIGH'): (
        "⚠️ SINYAL SURPLUS TINGGI\n\n"
        "Perkiraan harga turun {price_change_pct:.1f}% dalam 30 hari ke depan. "
        "Pasokan beras diperkirakan melebihi permintaan normal.\n\n"
        "Rekomendasi untuk pedagang pasar induk:\n"
        "• Tunda pembelian stok besar. Tunggu harga menyentuh level terendah dulu.\n"
        "• Negosiasi harga beli dari pemasok sekarang — mereka juga ingin jual.\n"
        "• Prioritaskan menjual sisa stok lama sebelum harga turun lebih jauh.\n"
        "• Faktor utama: {top_feature_text}"
    ),

    ('GLUT', 'MEDIUM'): (
        "⚡ Potensi Kelebihan Pasokan (Sedang)\n\n"
        "Ada indikasi tekanan harga turun. Perubahan harga diperkirakan "
        "{price_change_pct:.1f}% — masih dalam rentang normal tapi perlu diperhatikan.\n\n"
        "Rekomendasi:\n"
        "• Beli secukupnya — hindari overstock minggu ini.\n"
        "• Pantau harga pasar 2–3 hari ke depan sebelum beli besar.\n"
        "• Faktor utama: {top_feature_text}"
    ),

    ('SHORTAGE', 'HIGH'): (
        "🔴 SINYAL KEKURANGAN PASOKAN TINGGI\n\n"
        "Tekanan kenaikan harga terdeteksi. Perkiraan harga naik {price_change_pct:.1f}% "
        "dalam 30 hari ke depan. Pasokan beras diperkirakan lebih ketat dari normal.\n\n"
        "Rekomendasi untuk pedagang pasar induk:\n"
        "• Amankan stok dari pemasok sekarang, sebelum harga naik.\n"
        "• Pertimbangkan naikkan margin jual 3–5% secara bertahap.\n"
        "• Siapkan alternatif pemasok jika supplier utama kehabisan stok.\n"
        "• Faktor utama: {top_feature_text}"
    ),

    ('SHORTAGE', 'MEDIUM'): (
        "⚡ Potensi Kekurangan Pasokan (Sedang)\n\n"
        "Ada indikasi tekanan naik harga. Perubahan harga diperkirakan "
        "{price_change_pct:.1f}%.\n\n"
        "Rekomendasi:\n"
        "• Pertahankan stok normal atau sedikit di atas normal.\n"
        "• Siapkan kontak alternatif pemasok sebagai backup.\n"
        "• Faktor utama: {top_feature_text}"
    ),

    ('NEUTRAL', 'LOW'): (
        "✅ Pasar Stabil\n\n"
        "Tidak ada sinyal ekstrem terdeteksi. Harga diperkirakan bergerak "
        "{price_change_pct:+.1f}% — dalam batas normal musiman.\n\n"
        "Rekomendasi:\n"
        "• Lanjutkan operasi pembelian/penjualan seperti biasa.\n"
        "• Tidak ada tindakan khusus diperlukan saat ini."
    ),

    # Fallback for any combination not explicitly defined
    ('_DEFAULT', '_DEFAULT'): (
        "ℹ️ Sinyal Tidak Jelas\n\n"
        "Model tidak mendeteksi tekanan dominan yang kuat. "
        "Pantau kondisi pasar secara manual."
    ),
}

# Feature name → human-readable Indonesian text
FEATURE_TEXT = {
    'price_momentum':    "momentum harga 3 bulan terakhir",
    'harvest_timing':    "siklus musim panen Jawa Timur",
    'production_signal': "deviasi produksi padi dari rata-rata musiman",
    'rainfall_deficit':  "defisit curah hujan di sentra produksi",
}


# ── Confidence qualifier based on CI width ────────────────────────────────

def _confidence_qualifier(ci_width_pct: float) -> str:
    if ci_width_pct < 10:
        return "Tingkat keyakinan: Cukup tinggi"
    elif ci_width_pct < 20:
        return "Tingkat keyakinan: Sedang — gunakan sebagai panduan, bukan kepastian"
    else:
        return "Tingkat keyakinan: Rendah — interval perkiraan lebar, pantau pasar langsung"


# ── Main function ─────────────────────────────────────────────────────────

def generate_trader_advice(pressure_result: Dict) -> Dict:
    """
    Takes output from compute_supply_pressure() and returns
    a structured advice dict for the dashboard.

    Args:
        pressure_result: dict from supply_pressure_scorer.compute_supply_pressure()

    Returns:
        Dict with keys:
            headline:     short 1-line summary (for dashboard header)
            full_advice:  full Bahasa Indonesia advice text
            confidence:   confidence qualifier string
            signal_color: hex color for UI (#color)
            gauge_value:  float for gauge chart (-100 to +100,
                          negative = glut, positive = shortage)
    """
    dominant  = pressure_result['dominant_signal']
    intensity = pressure_result['intensity']
    pct       = pressure_result['price_change_pct']
    ci        = pressure_result['ci_width_pct']
    top_feat  = pressure_result.get('top_driving_feature', 'price_momentum')

    top_feature_text = FEATURE_TEXT.get(top_feat, top_feat)

    # Get template
    key = (dominant, intensity)
    template = ADVICE_TEMPLATES.get(key, ADVICE_TEMPLATES[('_DEFAULT', '_DEFAULT')])

    # Fill template
    try:
        full_advice = template.format(
            price_change_pct=pct,
            top_feature_text=top_feature_text,
        )
    except KeyError:
        full_advice = template  # neutral template has no format keys

    # Append confidence qualifier
    full_advice += f"\n\n_{_confidence_qualifier(ci)}_"

    # Headline
    headlines = {
        ('GLUT',     'HIGH'):   "🔻 Risiko Surplus Tinggi — Tunda pembelian",
        ('GLUT',     'MEDIUM'): "↘ Potensi Surplus — Pantau harga",
        ('SHORTAGE', 'HIGH'):   "🔺 Risiko Kekurangan Tinggi — Amankan stok",
        ('SHORTAGE', 'MEDIUM'): "↗ Potensi Kekurangan — Siapkan backup",
        ('NEUTRAL',  'LOW'):    "✅ Pasar Stabil",
    }
    headline = headlines.get(key, "ℹ️ Sinyal Tidak Jelas")

    # UI color
    colors = {
        ('GLUT',     'HIGH'):   '#EF9F27',
        ('GLUT',     'MEDIUM'): '#F59E0B',
        ('SHORTAGE', 'HIGH'):   '#E24B4A',
        ('SHORTAGE', 'MEDIUM'): '#F97316',
        ('NEUTRAL',  'LOW'):    '#1D9E75',
    }
    signal_color = colors.get(key, '#6B7280')

    # Gauge value: glut = negative, shortage = positive, neutral = 0
    if dominant == 'GLUT':
        gauge_value = -pressure_result['glut_score']
    elif dominant == 'SHORTAGE':
        gauge_value = pressure_result['shortage_score']
    else:
        gauge_value = 0.0

    return {
        'headline':     headline,
        'full_advice':  full_advice,
        'confidence':   _confidence_qualifier(ci),
        'signal_color': signal_color,
        'gauge_value':  gauge_value,
        'dominant_signal': dominant,
        'intensity':    intensity,
    }
```

---

## File 3: `tests/test_supply_pressure_scorer.py`

```python
"""Unit tests for supply_pressure_scorer.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'function'))

import pandas as pd
import numpy as np
import pytest
from supply_pressure_scorer import compute_supply_pressure, score_to_intensity


def make_forecast(price_change_pct, harvest_window=0, lean_season=0,
                  production_dev=0.0, rainfall_dev=0.0, ci_width_abs=500):
    """Helper: build minimal forecast_df for testing."""
    base_price = 12000
    yhat = base_price * (1 + price_change_pct)
    rows = []
    for i in range(3):
        rows.append({
            'yhat': yhat,
            'yhat_lower': yhat - ci_width_abs,
            'yhat_upper': yhat + ci_width_abs,
            'harvest_window': harvest_window,
            'lean_season': lean_season,
            'production_dev_pct': production_dev,
            'rainfall_dev_pct': rainfall_dev,
        })
    return pd.DataFrame(rows)


def test_clear_glut_signal():
    """Falling price + harvest approaching → GLUT HIGH."""
    fc = make_forecast(price_change_pct=-0.20, harvest_window=1, production_dev=0.15)
    result = compute_supply_pressure(fc, current_price=12000)
    assert result['dominant_signal'] == 'GLUT'
    assert result['intensity'] in ('MEDIUM', 'HIGH')


def test_clear_shortage_signal():
    """Rising price + lean season → SHORTAGE HIGH."""
    fc = make_forecast(price_change_pct=0.20, lean_season=1, production_dev=-0.15)
    result = compute_supply_pressure(fc, current_price=12000)
    assert result['dominant_signal'] == 'SHORTAGE'
    assert result['intensity'] in ('MEDIUM', 'HIGH')


def test_neutral_stable_market():
    """Flat price, no seasonality pressure → NEUTRAL LOW."""
    fc = make_forecast(price_change_pct=0.01)
    result = compute_supply_pressure(fc, current_price=12000)
    assert result['dominant_signal'] == 'NEUTRAL'
    assert result['intensity'] == 'LOW'


def test_score_thresholds():
    assert score_to_intensity(75) == 'HIGH'
    assert score_to_intensity(50) == 'MEDIUM'
    assert score_to_intensity(20) == 'LOW'


def test_output_keys():
    fc = make_forecast(price_change_pct=0.10)
    result = compute_supply_pressure(fc, current_price=12000)
    required = {'glut_score','shortage_score','dominant_signal',
                'intensity','price_change_pct','ci_width_pct'}
    assert required.issubset(result.keys())
```

---

## File 4: `tests/test_trader_advice.py`

```python
"""Unit tests for trader_advice.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'function'))

from trader_advice import generate_trader_advice


def make_pressure(dominant, intensity, pct=10.0, ci=15.0):
    return {
        'dominant_signal':    dominant,
        'intensity':          intensity,
        'price_change_pct':   pct,
        'ci_width_pct':       ci,
        'glut_score':         70 if dominant == 'GLUT' else 10,
        'shortage_score':     70 if dominant == 'SHORTAGE' else 10,
        'top_driving_feature': 'price_momentum',
        'driving_features':   {},
    }


def test_shortage_high_returns_red():
    result = generate_trader_advice(make_pressure('SHORTAGE', 'HIGH', pct=18))
    assert result['signal_color'] == '#E24B4A'
    assert 'Amankan' in result['full_advice']


def test_glut_high_returns_orange():
    result = generate_trader_advice(make_pressure('GLUT', 'HIGH', pct=-18))
    assert result['signal_color'] == '#EF9F27'
    assert 'Tunda' in result['full_advice']


def test_neutral_low_returns_green():
    result = generate_trader_advice(make_pressure('NEUTRAL', 'LOW', pct=1))
    assert result['signal_color'] == '#1D9E75'


def test_gauge_value_sign():
    glut     = generate_trader_advice(make_pressure('GLUT', 'HIGH'))
    shortage = generate_trader_advice(make_pressure('SHORTAGE', 'HIGH'))
    neutral  = generate_trader_advice(make_pressure('NEUTRAL', 'LOW'))
    assert glut['gauge_value'] < 0
    assert shortage['gauge_value'] > 0
    assert neutral['gauge_value'] == 0


def test_all_templates_render():
    """All defined (signal, intensity) combos should render without error."""
    from trader_advice import ADVICE_TEMPLATES
    for (sig, intens) in ADVICE_TEMPLATES:
        if sig == '_DEFAULT':
            continue
        result = generate_trader_advice(make_pressure(sig, intens, pct=12.5))
        assert len(result['full_advice']) > 50
```

---

## Acceptance criteria

Run: `pytest tests/ -v`

- [ ] All 9 unit tests pass
- [ ] No import errors
- [ ] `generate_trader_advice` produces non-empty Bahasa Indonesia text
  for every valid (signal, intensity) combination
