# dashboard/components/supply_gauge.py
# Plotly gauge: left = GLUT zone, right = SHORTAGE zone, center = NEUTRAL
 
import plotly.graph_objects as go
 
 
def render_supply_gauge(glut_score: int, shortage_score: int) -> go.Figure:
    # Needle: 50 = neutral, <50 = glut pressure, >50 = shortage pressure
    raw_diff = shortage_score - glut_score
    needle   = 50 + (raw_diff / 2)
    needle   = max(2, min(98, needle))
 
    dominant = (
        "SURPLUS"      if glut_score > shortage_score and max(glut_score, shortage_score) >= 40
        else "KEKURANGAN" if shortage_score > glut_score and max(glut_score, shortage_score) >= 40
        else "NETRAL"
    )
    color_map = {
        "SURPLUS":     "#F59E0B",
        "KEKURANGAN":  "#EF4444",
        "NETRAL":      "#10B981",
    }
    dominant_color = color_map[dominant]
 
    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=needle,
        title={
            "text": (
                f"<b style='font-size:20px;color:{dominant_color}'>{dominant}</b><br>"
                f"<span style='font-size:12px;color:#6B7280'>"
                f"Surplus: {glut_score} &nbsp;|&nbsp; Kekurangan: {shortage_score}</span>"
            ),
            "font": {"family": "Georgia, serif"}
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickvals": [0, 50, 100],
                "ticktext": ["SURPLUS", "NETRAL", "KEKURANGAN"],
                "tickfont": {"size": 11, "color": "#6B7280"},
            },
            "bar": {"color": dominant_color, "thickness": 0.3},
            "steps": [
                {"range": [0,  20],  "color": "#FEF3C7"},
                {"range": [20, 40],  "color": "#FEF9EE"},
                {"range": [40, 60],  "color": "#F0FDF4"},
                {"range": [60, 80],  "color": "#FEF2F2"},
                {"range": [80, 100], "color": "#FEE2E2"},
            ],
            "threshold": {
                "line": {"color": dominant_color, "width": 5},
                "thickness": 0.9,
                "value": needle,
            },
        },
    ))
 
    fig.update_layout(
        height=250,
        margin=dict(t=70, b=10, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Georgia, serif"},
    )
    return fig