# dashboard/components/trader_action_card.py
# Renders the structured Signal / Reason / Action card in Bahasa Indonesia
 
import streamlit as st
 
 
SIGNAL_CONFIG = {
    "GLUT":     {"label": "SURPLUS",      "color": "#F59E0B", "bg": "#FFFBEB", "border": "#FCD34D"},
    "SHORTAGE": {"label": "KEKURANGAN",   "color": "#EF4444", "bg": "#FEF2F2", "border": "#FCA5A5"},
    "NEUTRAL":  {"label": "NETRAL",       "color": "#10B981", "bg": "#F0FDF4", "border": "#6EE7B7"},
}
 
INTENSITY_CONFIG = {
    "HIGH":   {"label": "TINGGI",  "emoji": "🔴"},
    "MEDIUM": {"label": "SEDANG",  "emoji": "🟡"},
    "LOW":    {"label": "RENDAH",  "emoji": "🟢"},
}
 
 
def render_trader_action_card(
    dominant_signal: str,
    intensity: str,
    action_text: str,
    reason: str,
    confidence_days: int,
    price_change_pct: float,
    ci_width_pct: float,
):
    sig    = SIGNAL_CONFIG.get(dominant_signal, SIGNAL_CONFIG["NEUTRAL"])
    intens = INTENSITY_CONFIG.get(intensity, INTENSITY_CONFIG["LOW"])
 
    # ── Signal header badge ───────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            background:{sig['bg']};
            border-left:5px solid {sig['color']};
            border-radius:0 8px 8px 0;
            padding:14px 18px;
            margin-bottom:14px;
        ">
            <div style="
                font-size:11px;
                color:#6B7280;
                text-transform:uppercase;
                letter-spacing:0.08em;
                font-family:'Georgia',serif;
                margin-bottom:4px;
            ">Sinyal Pasar Induk</div>
            <div style="
                font-size:22px;
                font-weight:700;
                color:{sig['color']};
                font-family:'Georgia',serif;
                letter-spacing:0.02em;
            ">
                {intens['emoji']} {sig['label']} &mdash; {intens['label']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Three metrics ─────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        delta_color = "inverse" if dominant_signal == "GLUT" else "normal"
        st.metric(
            label="Perkiraan Perubahan Harga",
            value=f"{price_change_pct:+.1f}%",
            delta=None,
            help="Estimasi perubahan harga dalam horizon proyeksi",
        )
    with c2:
        st.metric(
            label="Horizon Sinyal",
            value=f"{confidence_days} hari",
            help="Seberapa jauh ke depan sinyal ini berlaku",
        )
    with c3:
        st.metric(
            label="Ketidakpastian (CI)",
            value=f"±{ci_width_pct:.0f}%",
            help="Lebar interval kepercayaan 80% — semakin lebar semakin tidak pasti",
        )
 
    # ── Reason ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            font-size:13px;
            color:#374151;
            margin:10px 0 8px 0;
            font-family:'Georgia',serif;
        ">
            <span style="color:#6B7280;font-size:11px;text-transform:uppercase;
                         letter-spacing:0.06em;">Penyebab terdeteksi</span><br>
            {reason}
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Action text ───────────────────────────────────────────────────────
    # Split on → and render as styled bullet points
    parts = [p.strip() for p in action_text.replace("→", "||→").split("||") if p.strip()]
    bullets_html = "".join(
        f"<div style='margin-bottom:6px'>{p}</div>"
        for p in parts
    )
 
    st.markdown(
        f"""
        <div style="
            background:#F9FAFB;
            border:1px solid #E5E7EB;
            border-radius:8px;
            padding:14px 18px;
            font-size:14px;
            color:#1F2937;
            line-height:1.75;
            font-family:'Georgia',serif;
            margin-top:4px;
        ">
            <div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                        letter-spacing:0.06em;margin-bottom:8px;">
                Rekomendasi untuk pedagang pasar induk
            </div>
            {bullets_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Disclaimer ────────────────────────────────────────────────────────
    st.caption(
        "⚠ Sinyal ini bersifat indikatif berdasarkan pola historis. "
        "Bukan prediksi harga yang pasti. Gunakan sebagai pertimbangan tambahan."
    )