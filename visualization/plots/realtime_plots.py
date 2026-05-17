"""Fonctions de visualisation réutilisables pour le dashboard."""
import numpy as np
import plotly.graph_objects as go
import pandas as pd


def gauge_soc(soc: float, soc_std: float = 0.0) -> go.Figure:
    color = "#00d4aa" if soc > 0.5 else ("#ffd700" if soc > 0.2 else "#ff4444")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=soc * 100,
        delta={"reference": 100, "suffix": "%"},
        title={"text": "SOC", "font": {"size": 18, "color": "white"}},
        number={"suffix": "%", "font": {"size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white"},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 20],  "color": "#3d0000"},
                {"range": [20, 50], "color": "#3d2600"},
                {"range": [50, 100],"color": "#003d1a"},
            ],
            "threshold": {"line": {"color": "red", "width": 3}, "value": 20},
        },
    ))
    fig.update_layout(paper_bgcolor="#1e2130", font_color="white",
                      height=220, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def gauge_soh(soh: float) -> go.Figure:
    color = "#00d4aa" if soh > 0.85 else ("#ffd700" if soh > 0.80 else "#ff4444")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=soh * 100,
        title={"text": "SOH", "font": {"size": 18, "color": "white"}},
        number={"suffix": "%", "font": {"size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white"},
            "bar": {"color": color},
            "threshold": {"line": {"color": "red", "width": 3}, "value": 80},
        },
    ))
    fig.update_layout(paper_bgcolor="#1e2130", font_color="white",
                      height=220, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def pack_heatmap(socs: np.ndarray, temps: np.ndarray, ns: int, np_: int) -> go.Figure:
    sg = np.array(socs).reshape(ns, np_) * 100
    tg = np.array(temps).reshape(ns, np_)
    fig = go.Figure()
    fig.add_trace(go.Heatmap(z=sg, colorscale="RdYlGn", zmin=0, zmax=100,
                              name="SOC", showscale=True))
    fig.update_layout(template="plotly_dark", height=300,
                      title="SOC par cellule (%)",
                      paper_bgcolor="#0e1117", plot_bgcolor="#1e2130")
    return fig


def history_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    t = df["timestamp"] / 60
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df["soc"]*100,
        name="SOC (%)", line=dict(color="#00d4aa", width=2)))
    fig.add_trace(go.Scatter(x=t, y=df["T_max"],
        name="T max (°C)", line=dict(color="#ff6b6b", width=1.5),
        yaxis="y2"))
    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Temps (min)",
        yaxis=dict(title="SOC (%)", range=[0, 105]),
        yaxis2=dict(title="T (°C)", overlaying="y", side="right"),
        paper_bgcolor="#0e1117", plot_bgcolor="#1e2130",
        legend=dict(bgcolor="#1e2130"),
        height=300,
    )
    return fig
