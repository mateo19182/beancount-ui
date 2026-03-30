"""Plotly chart helpers."""

import plotly.graph_objects as go


def allocation_pie(
    labels: list[str], values: list[float], height: int = 350
) -> go.Figure:
    """Donut chart for asset/portfolio allocation."""
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(
        height=height,
        showlegend=True,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


def income_pie(labels: list[str], values: list[float], height: int = 300) -> go.Figure:
    """Donut chart for income breakdown by source."""
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker=dict(
                    colors=["#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#d1fae5"]
                ),
            )
        ]
    )
    fig.update_layout(
        height=height,
        showlegend=True,
        margin=dict(l=0, r=0, t=20, b=0),
        title=dict(text="Income by Source", x=0.5, xanchor="center"),
        hovermode="closest",
    )
    return fig


def expense_pie(labels: list[str], values: list[float], height: int = 300) -> go.Figure:
    """Donut chart for expense breakdown by category."""
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker=dict(
                    colors=[
                        "#ef4444",
                        "#f87171",
                        "#fca5a5",
                        "#fecaca",
                        "#fee2e2",
                        "#fef2f2",
                    ]
                ),
            )
        ]
    )
    fig.update_layout(
        height=height,
        showlegend=True,
        margin=dict(l=0, r=0, t=20, b=0),
        title=dict(text="Expenses by Category", x=0.5, xanchor="center"),
        hovermode="closest",
    )
    return fig


def category_bar(
    labels: list[str],
    values: list[float],
    color: str = "steelblue",
    title: str = "",
    y_label: str = "Value",
    height: int = 350,
) -> go.Figure:
    """Bar chart for category breakdown (income or expenses)."""
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=color,
                text=[f"{v:,.0f}" for v in values],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title=y_label,
        height=height,
        showlegend=False,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    fig.update_traces(textfont_size=12)
    return fig


def allocation_bar(
    labels: list[str],
    values: list[float],
    color: str = "steelblue",
    title: str = "",
    y_label: str = "Value",
    height: int = 400,
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
