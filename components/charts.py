"""Plotly chart helpers."""

import plotly.graph_objects as go


def allocation_pie(labels: list[str], values: list[float], height: int = 350) -> go.Figure:
    """Donut chart for asset/portfolio allocation."""
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(
        height=height,
        showlegend=True,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


def allocation_bar(
    labels: list[str], values: list[float], color: str = "steelblue",
    title: str = "", y_label: str = "Value", height: int = 400,
) -> go.Figure:
    """Bar chart for portfolio allocation."""
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=color)])
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title=y_label,
        height=height,
        showlegend=False,
    )
    return fig
