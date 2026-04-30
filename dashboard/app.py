# dashboard/app.py
# RiceCast TraderEdge — Main Streamlit Dashboard
# Run locally: streamlit run app.py
# Deploy:      az webapp up --name ricecast-dashboard --runtime PYTHON:3.11 --sku F1
 
import streamlit as st
import requests
import pandas as pd
import os
import sys
from datetime import datetime
 
# Allow imports from components/ subfolder
sys.path.insert(0, os.path.dirname(__file__))
from components.supply_gauge       import render_supply_gauge
from components.forecast_chart     import render_forecast_chart
from components.trader_action_card import render_trader_action_card
 
# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TraderEdge — Sinyal Pasar Beras",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
 
# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Source+Sans+3:wght@300;400;500&display=swap');
 
    html, body, [class*="css"] {
        font-family: 'Source Sans 3', sans-serif;
    }
 
    h1, h2, h3, .stMetric label {
        font-family: 'Lora', Georgia, serif !important;
    }
 
    /* Top header bar */
    .main-header {
        background: linear-gradient(135deg, #1B3A6B 0%, #2563A8 100%);
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .main-header h1 {
        color: white !important;
        font-size: 26px !important;
        margin: 0 !important;
        font-family: 'Lora', serif !important;
        letter-spacing: -0.01em;
    }
    .main-header .subtitle {
        color: #BFDBFE;
        font-size: 13px;
        margin-top: 4px;
        font-family: 'Source Sans 3', sans-serif;
    }
    .main-header .timestamp {
        color: #93C5FD;
        font-size: 12px;
        text-align: right;
        font-family: 'Source Sans 3', sans-serif;
    }
 
    /* Section cards */
    .section-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }
    .section-title {
        font-family: 'Lora', serif;
        font-size: 13px;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #F3F4F6;
    }
 
    /* Metric cards */
    [data-testid="metric-container"] {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 12px 16px !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Lora', serif !important;
        font-size: 22px !important;
        color: #1B3A6B !important;
    }
 
    /* Demo warning banner */
    .demo-banner {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 13px;
        color: #92400E;
        margin-bottom: 12px;
    }
 
    /* Footer */
    .footer {
        text-align: center;
        font-size: 11px;
        color: #9CA3AF;
        padding: 20px 0 8px;
        border-top: 1px solid #F3F4F6;
        font-family: 'Source Sans 3', sans-serif;
    }
 
    /* Hide streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)
 
# ── Config ────────────────────────────────────────────────────────────────────
FUNCTION_URL = os.environ.get(
    "AZURE_FUNCTION_URL",
    "https://ricecast-traderedge-fn-e8ejapftfdhzekhx.southeastasia-01.azurewebsites.net/api/forecast",
)
 
SAMPLE_CSV = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample", "sample_12rows.csv"
)
 
 
# ── Data fetching ─────────────────────────────────────────────────────────────
 
@st.cache_data(ttl=3600)
def fetch_signal(horizon: int) -> dict:
    """Fetch supply pressure signal from Azure Function. Cached 1 hour."""
    try:
        r = requests.get(f"{FUNCTION_URL}?horizon={horizon}", timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return _demo_data()
    except Exception as e:
        st.error(f"Error mengambil data: {str(e)}")
        return _demo_data()
 
 
@st.cache_data(ttl=86400)
def load_historical() -> tuple:
    """Load historical price series for chart background."""
    try:
        df = pd.read_csv(SAMPLE_CSV, parse_dates=["ds"]).sort_values("ds")
        return (
            df["ds"].dt.strftime("%Y-%m-%d").tolist(),
            df["y"].astype(int).tolist(),
        )
    except Exception:
        # Minimal fallback so chart doesn't break
        dates  = pd.date_range("2022-01-01", periods=24, freq="MS").strftime("%Y-%m-%d").tolist()
        prices = [
            11800, 11900, 12100, 12400, 12200, 11900,
            12000, 12300, 12600, 13100, 13500, 13800,
            14200, 14500, 14100, 13900, 13700, 13500,
            13600, 13800, 14000, 14200, 14500, 14800,
        ]
        return dates, prices
 
 
def _demo_data() -> dict:
    return {
        "status": "demo",
        "dominant_signal": "SHORTAGE",
        "intensity": "MEDIUM",
        "glut_score": 18,
        "shortage_score": 55,
        "ci_width_pct": 19.2,
        "price_change_pct": 6.5,
        "action_text": (
            "[DATA DEMO] Risiko kekurangan pasokan sedang. "
            "→ Pertahankan stok di atas level normal minggu ini. "
            "→ Siapkan alternatif pemasok jika harga naik lebih dari 10%."
        ),
        "reason": "memasuki musim paceklik (pasokan biasanya menurun)",
        "confidence_days": 21,
        "forecast_dates":  ["2024-11-01", "2024-12-01", "2025-01-01"],
        "forecast_values": [13500, 13800, 14100],
        "ci_lower":        [12100, 12200, 12000],
        "ci_upper":        [14900, 15400, 16200],
        "current_price":   13500,
        "generated_at":    datetime.utcnow().isoformat(),
        "horizon_months":  3,
    }
 
 
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙ Pengaturan")
    horizon = st.slider(
        "Horizon proyeksi (bulan)",
        min_value=1, max_value=6, value=3,
        help="Berapa bulan ke depan sinyal dihitung",
    )
    if st.button("🔄 Perbarui Sinyal", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
 
    st.divider()
    st.markdown("""
    **Tentang TraderEdge**
 
    Alat bantu keputusan untuk pedagang beras di pasar induk Malang, Jawa Timur.
 
    Model: Prophet (Meta) dilatih pada data harga bulanan WFP/BPS 2018–2024.
 
    *Sinyal bersifat indikatif — bukan prediksi harga pasti.*
    """)
 
# ── Fetch data ────────────────────────────────────────────────────────────────
with st.spinner("Mengambil sinyal terbaru dari server..."):
    data = fetch_signal(horizon)
 
is_demo = data.get("status") == "demo"
 
# ── Header ────────────────────────────────────────────────────────────────────
generated_at = data.get("generated_at", "")
timestamp_str = ""
if generated_at:
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        timestamp_str = dt.strftime("%d %B %Y, %H:%M UTC")
    except Exception:
        timestamp_str = generated_at[:16]
 
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>🌾 TraderEdge</h1>
        <div class="subtitle">Sinyal Risiko Pasokan Beras — Pasar Induk Malang, Jawa Timur</div>
    </div>
    <div class="timestamp">
        Diperbarui<br><b>{timestamp_str}</b>
    </div>
</div>
""", unsafe_allow_html=True)
 
# Demo banner
if is_demo:
    st.markdown(
        '<div class="demo-banner">⚠ Menampilkan data demo — '
        'tidak dapat terhubung ke server Azure.</div>',
        unsafe_allow_html=True,
    )
 
# ── Row 1: Gauge + Chart ──────────────────────────────────────────────────────
col_gauge, col_chart = st.columns([1, 1.8], gap="medium")
 
with col_gauge:
    st.markdown('<div class="section-title">Tekanan Pasokan</div>', unsafe_allow_html=True)
    gauge_fig = render_supply_gauge(
        glut_score=data.get("glut_score", 0),
        shortage_score=data.get("shortage_score", 0),
    )
    st.plotly_chart(gauge_fig, use_container_width=True)
 
    # Current price pill
    current_price = data.get("current_price", 0)
    if current_price:
        st.markdown(
            f"""
            <div style="
                text-align:center;
                background:#EFF6FF;
                border:1px solid #BFDBFE;
                border-radius:8px;
                padding:8px;
                font-family:'Lora',serif;
                color:#1B3A6B;
                font-size:14px;
                font-weight:600;
            ">
                Harga Terkini &nbsp;·&nbsp; Rp {current_price:,}/kg
            </div>
            """,
            unsafe_allow_html=True,
        )
 
with col_chart:
    st.markdown('<div class="section-title">Harga &amp; Proyeksi</div>', unsafe_allow_html=True)
    hist_dates, hist_prices = load_historical()
    chart_fig = render_forecast_chart(
        historical_dates=hist_dates,
        historical_prices=hist_prices,
        forecast_dates=data.get("forecast_dates", []),
        forecast_values=data.get("forecast_values", []),
        ci_lower=data.get("ci_lower", []),
        ci_upper=data.get("ci_upper", []),
    )
    st.plotly_chart(chart_fig, use_container_width=True)
 
# ── Row 2: Action card ────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="section-title">Rekomendasi Pedagang</div>', unsafe_allow_html=True)
 
render_trader_action_card(
    dominant_signal  = data.get("dominant_signal", "NEUTRAL"),
    intensity        = data.get("intensity", "LOW"),
    action_text      = data.get("action_text", "—"),
    reason           = data.get("reason", "—"),
    confidence_days  = data.get("confidence_days", 21),
    price_change_pct = data.get("price_change_pct", 0.0),
    ci_width_pct     = data.get("ci_width_pct", 0.0),
)
 
# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='footer'>"
    "RiceCast TraderEdge &nbsp;·&nbsp; Prototype &nbsp;·&nbsp; "
    "Data: WFP/HDX, BPS Jawa Timur, PIHPS Bank Indonesia &nbsp;·&nbsp; "
    "Model: Facebook Prophet &nbsp;·&nbsp; "
    "Hosting: Microsoft Azure"
    "</div>",
    unsafe_allow_html=True,
)