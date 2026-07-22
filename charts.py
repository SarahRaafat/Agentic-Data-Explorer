"""Plotly helpers for chart / dashboard specs from agent_core."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from agent_core import THEMES


def chart_to_figure(spec: dict, theme: dict | None = None) -> go.Figure:
    """Convert a create_visualization payload into a Plotly figure."""
    theme = theme or THEMES["dark"]
    chart_type = spec.get("chart_type", "bar")
    title = spec.get("title") or "Chart"
    labels = [str(x) for x in spec.get("labels", [])]
    values = [float(v) for v in spec.get("values", [])]
    x_label = spec.get("x_label") or ""
    y_label = spec.get("y_label") or ""
    template = theme.get("plotly_template", "plotly_white")
    accent = theme.get("accent", "#2563eb")

    df = pd.DataFrame({"label": labels, "value": values})

    if chart_type == "line":
        fig = px.line(
            df, x="label", y="value", title=title, markers=True, template=template
        )
        fig.update_traces(line_color=accent)
    elif chart_type == "area":
        fig = px.area(df, x="label", y="value", title=title, template=template)
    elif chart_type == "pie":
        fig = px.pie(df, names="label", values="value", title=title, template=template)
    elif chart_type == "scatter":
        fig = px.scatter(df, x="label", y="value", title=title, template=template)
        fig.update_traces(marker_color=accent)
    elif chart_type == "horizontal_bar":
        fig = px.bar(
            df,
            x="value",
            y="label",
            orientation="h",
            title=title,
            template=template,
            color_discrete_sequence=[accent],
        )
    else:
        fig = px.bar(
            df,
            x="label",
            y="value",
            title=title,
            template=template,
            color_discrete_sequence=[accent],
        )

    fig.update_layout(
        xaxis_title=x_label or None,
        yaxis_title=y_label or None,
        margin=dict(l=40, r=20, t=60, b=40),
        height=420,
        paper_bgcolor=theme.get("card", "#ffffff"),
        plot_bgcolor=theme.get("card", "#ffffff"),
        font_color=theme.get("text", "#1a1a1a"),
    )
    if chart_type not in {"pie", "horizontal_bar"}:
        fig.update_xaxes(tickangle=-35)
    return fig
