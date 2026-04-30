# dashboard/components/forecast_chart.py
# Historical price + Prophet forecast with CI bands
 
import plotly.graph_objects as go
 
 
def render_forecast_chart(
    historical_dates: list,
    historical_prices: list,
    forecast_dates: list,
    forecast_values: list,
    ci_lower: list,
    ci_upper: list,
) -> go.Figure:
 
    fig = go.Figure()
 
    # CI band — fill between upper and lower
    if forecast_dates and ci_lower and ci_upper:
        fig.add_trace(go.Scatter(
            x=forecast_dates + forecast_dates[::-1],
            y=ci_upper + ci_lower[::-1],
            fill="toself",
            fillcolor="rgba(37,99,168,0.10)",
            line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip",
            name="Rentang 80% CI",
            showlegend=True,
        ))
 
    # Historical line
    fig.add_trace(go.Scatter(
        x=historical_dates,
        y=historical_prices,
        name="Harga Aktual",
        line=dict(color="#1B3A6B", width=2.5),
        mode="lines",
    ))
 
    # Forecast line
    if forecast_dates and forecast_values:
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_values,
            name="Proyeksi",
            line=dict(color="#2563A8", width=2, dash="dash"),
            mode="lines+markers",
            marker=dict(size=7, color="#2563A8"),
        ))
 
        # Vertical divider at forecast start
        fig.add_vline(
            x=forecast_dates[0],
            line_dash="dot",
            line_color="#9CA3AF",
            line_width=1.2,
        )
        fig.add_annotation(
            x=forecast_dates[0],
            y=1,
            yref="paper",
            text="Sekarang",
            showarrow=False,
            font=dict(size=10, color="#9CA3AF"),
            xanchor="left",
            xshift=4,
        )
 
    fig.update_layout(
        title=dict(
            text="Harga Beras Medium — Jawa Timur",
            font=dict(size=14, family="Georgia, serif", color="#1F2937"),
        ),
        yaxis=dict(
            tickformat=",",
            tickprefix="Rp ",
            gridcolor="#F3F4F6",
            title="IDR/kg",
            title_font=dict(size=11, color="#6B7280"),
        ),
        xaxis=dict(gridcolor="#F3F4F6"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10),
        ),
        height=300,
        margin=dict(t=60, b=40, l=70, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Georgia, serif"),
        hovermode="x unified",
    )
    return fig