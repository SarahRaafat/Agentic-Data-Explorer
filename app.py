"""Streamlit frontend: chat with the viz agent and render dashboards/charts.

Run from this folder:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

SPECIAL_TASK_DIR = Path(__file__).resolve().parent
# Keep cwd on project root — never under archive (3)/ (parentheses break Streamlit paths)
os.chdir(SPECIAL_TASK_DIR)
if str(SPECIAL_TASK_DIR) not in sys.path:
    sys.path.insert(0, str(SPECIAL_TASK_DIR))

from agent_core import DATA_DIR, MODEL, THEMES, ask_viz  # noqa: E402
from charts import chart_to_figure  # noqa: E402

st.set_page_config(
    page_title="Instacart Viz Agent",
    page_icon="📊",
    layout="wide",
)

EXAMPLE_PROMPTS = [
    "Show a line chart of orders by hour of day, then explain and generate insights",
    "Bar chart of top 10 departments by product count — ask the critic to review it",
    "Build a dashboard for this grocery dataset with KPIs and charts",
    "Filter to produce-related analysis if possible, then visualize product counts",
    "Switch to dark mode and export the last dashboard as markdown",
]


def uniq(prefix: str = "el") -> str:
    """Unique Streamlit element key for this script run."""
    n = int(st.session_state.get("_uid", 0))
    st.session_state._uid = n + 1
    return f"{prefix}_{n}"


def init_state() -> None:
    st.session_state._uid = 0
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "theme" not in st.session_state:
        st.session_state.theme = THEMES["dark"].copy()
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
    # Drop legacy message shapes that break the new renderer
    cleaned = []
    for msg in st.session_state.messages:
        if not isinstance(msg, dict) or "role" not in msg:
            continue
        if msg["role"] == "assistant" and "payload" not in msg and "charts" in msg:
            msg = {
                "role": "assistant",
                "content": msg.get("content", ""),
                "payload": {
                    "answer": msg.get("content", ""),
                    "charts": msg.get("charts") or [],
                    "dashboards": [],
                    "insights": [],
                    "explanations": [],
                    "critiques": [],
                    "exports": [],
                    "theme": None,
                },
            }
        cleaned.append(msg)
    st.session_state.messages = cleaned


def apply_theme_css(theme: dict) -> None:
    bg = theme.get("bg", "#f7f8fa")
    card = theme.get("card", "#ffffff")
    text = theme.get("text", "#1a1a1a")
    accent = theme.get("accent", "#2563eb")
    muted = text
    st.markdown(
        f"""
        <style>
        .stApp,
        .stApp [data-testid="stAppViewContainer"],
        .stApp [data-testid="stHeader"],
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div {{
            background-color: {bg} !important;
            color: {text} !important;
        }}

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp p, .stApp span, .stApp label, .stApp li,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stMarkdownContainer"] *,
        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stWidgetLabel"] *,
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] *,
        .stApp [data-testid="stChatMessageContent"],
        .stApp [data-testid="stChatMessageContent"] *,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {{
            color: {text} !important;
        }}

        .stApp a {{ color: {accent} !important; }}

        div[data-testid="stChatMessage"] {{
            background: {card} !important;
            border: 1px solid {accent}33;
            border-radius: 12px;
            padding: 0.25rem 0.5rem;
            color: {text} !important;
        }}

        .stApp [data-baseweb="select"] > div,
        .stApp input, .stApp textarea {{
            background-color: {card} !important;
            color: {text} !important;
        }}

        .kpi-card {{
            background: {card};
            border: 1px solid {accent}33;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.5rem;
            color: {text};
        }}
        .kpi-label {{
            font-size: 0.85rem;
            color: {muted};
            opacity: 0.8;
        }}
        .kpi-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {accent};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Instacart Viz Agent")
        st.caption(
            "10 presentation tools: visualize, recommend, dashboard, layout, "
            "insights, explain, filter, export, theme, critic."
        )
        st.markdown(f"**Model:** `{MODEL}`")
        st.markdown(f"**Dataset:** `{DATA_DIR.name}`")
        st.caption(f"App dir: `{SPECIAL_TASK_DIR.name}`")
        if DATA_DIR.exists():
            files = sorted(p.name for p in DATA_DIR.glob("*.csv"))
            st.success(f"{len(files)} CSV files found")
            with st.expander("Files"):
                for name in files:
                    st.text(name)
        else:
            st.error(f"Dataset folder missing:\n{DATA_DIR}")

        st.divider()
        theme_name = st.selectbox(
            "Theme",
            options=list(THEMES.keys()),
            index=list(THEMES.keys()).index(
                st.session_state.theme.get("name", "dark")
            ),
            key="theme_select",
        )
        if theme_name != st.session_state.theme.get("name"):
            st.session_state.theme = THEMES[theme_name].copy()
            st.rerun()

        st.divider()
        st.subheader("Try an example")
        for i, prompt in enumerate(EXAMPLE_PROMPTS):
            if st.button(prompt, use_container_width=True, key=f"example_btn_{i}"):
                st.session_state.pending_question = prompt
                st.rerun()

        st.divider()
        if st.button("Clear chat", use_container_width=True, key="clear_chat_btn"):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()


def render_kpis(kpis: list[dict]) -> None:
    if not kpis:
        return
    theme = st.session_state.theme
    text = theme.get("text", "#1a1a1a")
    accent = theme.get("accent", "#2563eb")
    cols = st.columns(min(4, max(len(kpis), 1)))
    for i, kpi in enumerate(kpis):
        with cols[i % len(cols)]:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-label" style="color:{text};opacity:0.8;">
                    {kpi.get("label", "KPI")}
                  </div>
                  <div class="kpi-value" style="color:{accent};">
                    {kpi.get("value", "—")}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_table(table: dict | None) -> None:
    if not table:
        return
    st.subheader("Data table")
    if "records" in table:
        st.dataframe(pd.DataFrame(table["records"]), use_container_width=True)
    elif "columns" in table and "rows" in table:
        st.dataframe(
            pd.DataFrame(table["rows"], columns=table["columns"]),
            use_container_width=True,
        )
    else:
        st.json(table)


def render_dashboard(dashboard: dict, theme: dict) -> None:
    st.subheader(dashboard.get("title") or "Dashboard")
    render_kpis(dashboard.get("kpis") or [])

    for spec in dashboard.get("charts") or []:
        fig = chart_to_figure(spec, theme)
        st.plotly_chart(fig, use_container_width=True, key=uniq("dash_chart"))

    insights = dashboard.get("insights") or []
    if insights:
        st.markdown("**Insights**")
        for bullet in insights:
            st.markdown(f"- {bullet}")

    render_table(dashboard.get("table"))

    with st.expander("Dashboard layout / JSON"):
        st.json(
            {
                "layout": dashboard.get("layout"),
                "theme": dashboard.get("theme"),
                "id": dashboard.get("id"),
            }
        )


def render_exports(exports: list[dict]) -> None:
    if not exports:
        return
    st.markdown("**Exports**")
    for exp in exports:
        path = Path(exp.get("path", ""))
        if path.exists():
            st.download_button(
                label=f"Download {path.name}",
                data=path.read_bytes(),
                file_name=path.name,
                mime="application/octet-stream",
                key=uniq("download"),
            )
        else:
            st.caption(f"Export recorded: {exp}")


def render_assistant_payload(out: dict) -> None:
    theme = st.session_state.theme
    st.markdown(out.get("answer") or "_No text response._")

    explanations = out.get("explanations") or []
    if explanations:
        with st.expander("How to read the chart"):
            for text in explanations:
                st.write(text)

    insights = out.get("insights") or []
    if insights:
        st.markdown("**Insights**")
        for bullet in insights:
            st.markdown(f"- {bullet}")

    critiques = out.get("critiques") or []
    if critiques:
        with st.expander("Visualization critic"):
            for c in critiques:
                status = "Approved" if c.get("approved") else "Needs changes"
                st.markdown(f"**{status}** — {c.get('reason', '')}")
                for issue in c.get("issues") or []:
                    st.markdown(f"- {issue}")
                if c.get("suggested_chart_type"):
                    st.caption(f"Suggested chart: `{c['suggested_chart_type']}`")

    dashboards = out.get("dashboards") or []
    for dash in dashboards:
        render_dashboard(dash, theme)

    charts = out.get("charts") or []
    dash_titles = {
        c.get("title") for d in dashboards for c in (d.get("charts") or [])
    }
    standalone = (
        [c for c in charts if c.get("title") not in dash_titles]
        if dashboards
        else charts
    )
    if not dashboards and not standalone:
        st.info(
            "No chart/dashboard was produced. Try asking for a chart or "
            "'build a dashboard'."
        )
    for spec in standalone:
        fig = chart_to_figure(spec, theme)
        st.plotly_chart(fig, use_container_width=True, key=uniq("chart"))
        with st.expander(f"Chart JSON — {spec.get('title', 'chart')}"):
            st.json(spec)

    render_exports(out.get("exports") or [])


def render_message(msg: dict) -> None:
    role = msg.get("role", "assistant")
    with st.chat_message(role):
        if role == "user":
            st.markdown(msg.get("content", ""))
            return
        payload = msg.get("payload")
        if payload:
            render_assistant_payload(payload)
        else:
            st.markdown(msg.get("content", ""))


def run_agent(question: str) -> None:
    """Call the viz agent and store the result (no live chart render here)."""
    st.session_state.messages.append({"role": "user", "content": question})

    current = st.session_state.theme.get("name", "light")
    themed_q = question
    if "theme" not in question.lower() and "dark mode" not in question.lower():
        themed_q = (
            f"{question}\n\n(Current UI theme preference: {current}. "
            "Call change_theme only if the user asked to change it.)"
        )

    try:
        with st.spinner("Agent is analyzing, visualizing, and reviewing…"):
            out = ask_viz(themed_q)
    except Exception as exc:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"Agent error: `{type(exc).__name__}: {exc}`",
                "payload": None,
            }
        )
        return

    agent_theme = out.get("theme")
    if isinstance(agent_theme, dict) and agent_theme.get("name"):
        merged = {
            **THEMES.get(agent_theme["name"], THEMES["light"]),
            **agent_theme,
        }
        st.session_state.theme = merged

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": out.get("answer") or "",
            "payload": {
                "answer": out.get("answer"),
                "charts": out.get("charts") or [],
                "dashboards": out.get("dashboards") or [],
                "insights": out.get("insights") or [],
                "explanations": out.get("explanations") or [],
                "critiques": out.get("critiques") or [],
                "exports": out.get("exports") or [],
                "theme": out.get("theme"),
            },
        }
    )


def main() -> None:
    init_state()
    apply_theme_css(st.session_state.theme)
    render_sidebar()

    st.title("Instacart data visualization")
    st.write(
        "Agentic frontend: **filter → recommend → visualize → critic → "
        "insights → dashboard → export / theme**."
    )

    # Process queued question before rendering history
    pending = st.session_state.pending_question
    if pending:
        st.session_state.pending_question = None
        run_agent(pending)
        st.rerun()

    for msg in st.session_state.messages:
        render_message(msg)

    question = st.chat_input(
        "e.g. Build a dashboard of departments and orders by hour"
    )
    if question:
        st.session_state.pending_question = question
        st.rerun()


if __name__ == "__main__":
    main()
