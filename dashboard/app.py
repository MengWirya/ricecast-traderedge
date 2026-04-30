# dashboard/app.py
# RiceCast TraderEdge — Main Streamlit Dashboard
# Run locally: streamlit run app.py
import streamlit as st
import requests
import pandas as pd
import os, sys
from datetime import datetime
 
sys.path.insert(0, os.path.dirname(__file__))
from components.forecast_chart import render_forecast_chart
 
# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TraderEdge — Sinyal Pasar Beras",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="collapsed",
)
 
# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: var(--font-sans), sans-serif;
}
 
/* ─ Decision card ────────────────────────────────────────────────────────── */
.decision-card {
    border-radius: 14px;
    padding: 28px 28px 24px;
    text-align: center;
    margin-bottom: 16px;
}
.decision-card .eyebrow {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: .10em;
    text-transform: uppercase;
    margin-bottom: 10px;
    opacity: .75;
}
.decision-card .action {
    font-size: 38px;
    font-weight: 500;
    letter-spacing: -.02em;
    line-height: 1.1;
    margin-bottom: 10px;
}
.decision-card .consequence {
    font-size: 14px;
    line-height: 1.55;
    opacity: .8;
}
 
/* ─ Why bullets ──────────────────────────────────────────────────────────── */
.why-section {
    background: var(--color-background-secondary);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 14px;
}
.why-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--color-text-tertiary);
    margin-bottom: 10px;
}
.why-bullet {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 14px;
    color: var(--color-text-secondary);
    line-height: 1.55;
    margin-bottom: 7px;
}
.why-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 6px;
}
 
/* ─ Context strip ────────────────────────────────────────────────────────── */
.context-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 14px;
}
.context-cell {
    background: var(--color-background-secondary);
    border-radius: 10px;
    padding: 10px 12px;
    text-align: center;
}
.context-cell .ctx-label {
    font-size: 10px;
    color: var(--color-text-tertiary);
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 4px;
}
.context-cell .ctx-value {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.2;
}
 
/* ─ Header ───────────────────────────────────────────────────────────────── */
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 0.5px solid var(--color-border-tertiary);
}
.app-title {
    font-size: 18px;
    font-weight: 500;
    color: var(--color-text-primary);
}
.app-sub {
    font-size: 12px;
    color: var(--color-text-tertiary);
    margin-top: 2px;
}
.app-ts {
    font-size: 11px;
    color: var(--color-text-tertiary);
    text-align: right;
}
 
/* ─ Price badge ──────────────────────────────────────────────────────────── */
.price-badge {
    display: inline-block;
    background: var(--color-background-info);
    color: var(--color-text-info);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 14px;
}
 
/* ─ Demo banner ──────────────────────────────────────────────────────────── */
.demo-banner {
    background: var(--color-background-warning);
    border: 0.5px solid var(--color-border-warning);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    color: var(--color-text-warning);
    margin-bottom: 12px;
}
 
/* ─ Footer ───────────────────────────────────────────────────────────────── */
.footer {
    font-size: 11px;
    color: var(--color-text-tertiary);
    text-align: center;
    padding: 16px 0 4px;
    border-top: 0.5px solid var(--color-border-tertiary);
    line-height: 1.8;
}
 
/* Hide Streamlit chrome */
#MainMenu, footer, .stDeployButton { visibility: hidden; }
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
 
 
# ── Data ──────────────────────────────────────────────────────────────────────
 
@st.cache_data(ttl=3600)
def fetch_signal(horizon: int) -> dict:
    try:
        r = requests.get(f"{FUNCTION_URL}?horizon={horizon}", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return _demo_data()
 
 
@st.cache_data(ttl=86400)
def load_historical() -> tuple:
    try:
        df = pd.read_csv(SAMPLE_CSV, parse_dates=["ds"]).sort_values("ds")
        return df["ds"].dt.strftime("%Y-%m-%d").tolist(), df["y"].astype(int).tolist()
    except Exception:
        dates  = pd.date_range("2022-01-01", periods=24, freq="MS").strftime("%Y-%m-%d").tolist()
        prices = [
            11800,11900,12100,12400,12200,11900,
            12000,12300,12600,13100,13500,13800,
            14200,14500,14100,13900,13700,13500,
            13600,13800,14000,14200,14500,14800,
        ]
        return dates, prices
 
 
def _demo_data() -> dict:
    return {
        "status":          "demo",
        "decision_key":    "TAHAN",
        "decision_label":  "TAHAN DULU",
        "consequence":     "Sinyal campuran — tunda pembelian besar, pantau harga 1–2 minggu",
        "decision_color":  "#92400E",
        "decision_bg":     "#FEF3C7",
        "decision_border": "#FCD34D",
        "reasons":         [
            "Data demo — sinyal tidak mencerminkan kondisi pasar nyata",
            "Hubungkan ke server Azure untuk sinyal aktual",
        ],
        "season_label":    "Panen Raya",
        "trend_label":     "→ Stabil",
        "trend_color":     "#2563EB",
        "prod_label":      "Normal",
        "confidence_label":"Rendah ⚠",
        "price_change_pct": 0.0,
        "current_price":   13500,
        "generated_at":    datetime.utcnow().isoformat(),
        "horizon_months":  3,
        "forecast_dates":  pd.date_range(datetime.now(), periods=3, freq="MS").strftime("%Y-%m-%d").tolist(),
        "forecast_values": [13500, 13600, 13700],
        "ci_lower":        [12500, 12400, 12300],
        "ci_upper":        [14500, 14800, 15100],
        "dominant_signal": "NEUTRAL",
        "intensity":       "LOW",
        "glut_score":      0,
        "shortage_score":  0,
        "ci_width_pct":    15.0,
        "action_text":     "Data demo.",
        "reason":          "Data demo.",
        "confidence_days": 21,
    }
 
 
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Pengaturan")
    horizon = st.slider("Horizon proyeksi (bulan)", 1, 6, 3)
    if st.button("Perbarui sinyal", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("""
**TraderEdge** membantu pedagang beras di pasar induk Malang memutuskan kapan waktu terbaik untuk beli, tahan, atau kurangi stok.
 
Model dilatih dari data harga WFP/BPS Jawa Timur 2018–2024.
 
*Sinyal bersifat indikatif — bukan prediksi harga pasti.*
""")
 
 
# ── Fetch ─────────────────────────────────────────────────────────────────────
with st.spinner("Mengambil sinyal..."):
    data = fetch_signal(horizon)
 
is_demo = data.get("status") == "demo"
 
# ── Header ────────────────────────────────────────────────────────────────────
ts_str = ""
try:
    dt = datetime.fromisoformat(data.get("generated_at", "").replace("Z", "+00:00"))
    ts_str = dt.strftime("%d %b %Y, %H:%M UTC")
except Exception:
    pass
 
st.markdown(f"""
<div class="app-header">
  <div>
    <div class="app-title">🌾 TraderEdge</div>
    <div class="app-sub">Pasar Induk Beras — Malang, Jawa Timur</div>
  </div>
  <div class="app-ts">Diperbarui<br><b>{ts_str}</b></div>
</div>
""", unsafe_allow_html=True)
 
if is_demo:
    st.markdown('<div class="demo-banner">⚠ Data demo — tidak dapat terhubung ke server</div>',
                unsafe_allow_html=True)
 
# ── Current price badge ───────────────────────────────────────────────────────
cp = data.get("current_price", 0)
if cp:
    st.markdown(
        f'<div style="text-align:center"><span class="price-badge">'
        f'Harga terkini &nbsp;·&nbsp; Rp {cp:,}/kg</span></div>',
        unsafe_allow_html=True
    )
 
# ── [PRIMARY] Decision card ───────────────────────────────────────────────────
color   = data.get("decision_color",  "#92400E")
bg      = data.get("decision_bg",     "#FEF3C7")
border  = data.get("decision_border", "#FCD34D")
label   = data.get("decision_label",  "TAHAN DULU")
conseq  = data.get("consequence",     "—")
 
st.markdown(f"""
<div class="decision-card" style="
    background:{bg};
    border:2px solid {border};
    color:{color};
">
  <div class="eyebrow">Keputusan minggu ini</div>
  <div class="action">{label}</div>
  <div class="consequence">{conseq}</div>
</div>
""", unsafe_allow_html=True)
 
# ── [SECONDARY] Why bullets ───────────────────────────────────────────────────
reasons = data.get("reasons", [])
if reasons:
    bullets_html = "".join([
        f'<div class="why-bullet">'
        f'<div class="why-dot" style="background:{color}"></div>'
        f'<div>{r}</div></div>'
        for r in reasons
    ])
    st.markdown(f"""
<div class="why-section">
  <div class="why-label">Mengapa sinyal ini muncul</div>
  {bullets_html}
</div>
""", unsafe_allow_html=True)
 
# ── [TERTIARY] Context strip ──────────────────────────────────────────────────
season_label    = data.get("season_label",    "—")
trend_label     = data.get("trend_label",     "—")
trend_color     = data.get("trend_color",     "var(--color-text-secondary)")
prod_label      = data.get("prod_label",      "—")
conf_label      = data.get("confidence_label","—")
 
conf_color = (
    "var(--color-text-success)"  if "Tinggi" in conf_label
    else "var(--color-text-warning)" if "Sedang" in conf_label
    else "var(--color-text-danger)"
)
 
st.markdown(f"""
<div class="context-strip">
  <div class="context-cell">
    <div class="ctx-label">Musim</div>
    <div class="ctx-value" style="color:var(--color-text-primary)">{season_label}</div>
  </div>
  <div class="context-cell">
    <div class="ctx-label">Tren harga</div>
    <div class="ctx-value" style="color:{trend_color}">{trend_label}</div>
  </div>
  <div class="context-cell">
    <div class="ctx-label">Produksi</div>
    <div class="ctx-value" style="color:var(--color-text-primary)">{prod_label}</div>
  </div>
  <div class="context-cell">
    <div class="ctx-label">Kepercayaan</div>
    <div class="ctx-value" style="color:{conf_color}">{conf_label}</div>
  </div>
</div>
""", unsafe_allow_html=True)
 
# ── [DETAIL] Chart — collapsed ────────────────────────────────────────────────
with st.expander("📈 Lihat grafik harga historis & proyeksi"):
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
    st.caption(
        f"Rentang kepercayaan 80% ditampilkan sebagai area biru. "
        f"Proyeksi dimulai {data.get('forecast_start','—')} untuk {data.get('horizon_months',3)} bulan ke depan."
    )
 
# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
  TraderEdge &nbsp;·&nbsp; Prototype<br>
  Data: WFP/HDX · BPS Jawa Timur · PIHPS Bank Indonesia<br>
  Model: Prophet (Meta) &nbsp;·&nbsp; Hosting: Microsoft Azure
</div>
""", unsafe_allow_html=True)