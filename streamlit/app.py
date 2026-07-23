"""Streamlit frontend: chat with the viz agent and render dashboards/charts.

Run from this folder (streamlit/):
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

STREAMLIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = STREAMLIT_DIR.parent
SHARED_DIR = REPO_ROOT / "shared"


def _ensure_streamlit_cwd() -> None:
    """Streamlit breaks if cwd is under archive (3)/ (parentheses in path)."""
    try:
        os.chdir(STREAMLIT_DIR)
    except OSError:
        pass


# Keep cwd on streamlit/ — never under archive (3)/
_ensure_streamlit_cwd()
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

from agent_core import DATA_DIR, MODEL, THEMES, ask_viz  # noqa: E402
from charts import chart_to_figure  # noqa: E402

_ensure_streamlit_cwd()

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
    elif st.session_state.theme.get("name") not in THEMES:
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
    muted = theme.get("muted", "#666666")
    accent = theme.get("accent", "#2563eb")
    border = theme.get("border", "#d6dde8")

    button = theme.get("button", accent)
    button_hover = theme.get("button_hover", accent)
    button_text = theme.get("button_text", "#ffffff")
    input_bg = theme.get("input_bg", card)

    st.markdown(
        f"""
<style>

html, body,
.stApp,
[data-testid="stAppViewContainer"] {{
    background:{bg} !important;
    color:{text} !important;
}}

[data-testid="stHeader"]{{
    background:{bg} !important;
}}

section[data-testid="stSidebar"],
section[data-testid="stSidebar"]>div{{
    background:{card} !important;
    border-right:1px solid {border};
}}

html, body, p, span, label, li,
h1,h2,h3,h4,h5,h6,
.stMarkdown, .stMarkdown *,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] *,
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] *,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
.stCaption, .stCaption * {{
    color:{text} !important;
}}

a {{ color:{accent} !important; }}

/* Inline code chips (e.g. Model name) — follow theme, not Streamlit dark chrome */
code,
[data-testid="stMarkdownContainer"] code,
.stMarkdown code {{
    background:{input_bg} !important;
    color:{accent} !important;
    border:1px solid {border} !important;
    border-radius:6px !important;
    padding:0.1rem 0.35rem !important;
}}

pre, [data-testid="stCode"] {{
    background:{input_bg} !important;
    border:1px solid {border} !important;
}}

pre code, [data-testid="stCode"] code {{
    background:transparent !important;
    border:none !important;
    color:{text} !important;
}}

[data-testid="stChatMessage"]{{
    background:{card} !important;
    border:1px solid {border};
    border-radius:14px;
    padding:.4rem;
}}

.stButton>button,
.stDownloadButton>button {{
    background:{button} !important;
    color:{button_text} !important;
    border:none !important;
    border-radius:10px;
    transition:.2s;
}}

.stButton>button:hover,
.stDownloadButton>button:hover {{
    background:{button_hover} !important;
    color:{button_text} !important;
}}

.stButton>button:focus,
.stDownloadButton>button:focus {{
    background:{button_hover} !important;
    color:{button_text} !important;
    box-shadow:none !important;
}}

[data-baseweb="select"]>div {{
    background:{input_bg} !important;
    color:{text} !important;
    border:1px solid {border} !important;
    box-shadow:none !important;
}}

[data-baseweb="select"] * {{ color:{text} !important; }}

input, textarea {{
    background:{input_bg} !important;
    color:{text} !important;
    border:1px solid {border} !important;
    box-shadow:none !important;
}}

textarea::placeholder,
input::placeholder {{ color:{muted} !important; }}

/* Chat input bar + focus ring */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] textarea {{
    background:{input_bg} !important;
    color:{text} !important;
    border:1px solid {border} !important;
    box-shadow:none !important;
}}

[data-testid="stChatInput"]:focus-within,
[data-testid="stChatInput"] > div:focus-within,
[data-testid="stChatInput"] textarea:focus {{
    border-color:{accent} !important;
    box-shadow:0 0 0 1px {accent} !important;
}}

[data-testid="stBottomBlockContainer"] {{
    background:{bg} !important;
}}

[data-testid="stDataFrame"] {{ background:{card} !important; }}
[data-testid="stDataFrame"] * {{ color:{text} !important; }}

[data-testid="stJson"] {{ background:{card} !important; }}

.streamlit-expanderHeader {{ color:{text} !important; }}
.streamlit-expanderContent {{ background:{card} !important; }}

.kpi-card {{
    background:{card};
    border:1px solid {border};
    border-radius:14px;
    padding:18px;
}}

.kpi-label {{
    color:{muted};
    font-size:.9rem;
}}

.kpi-value {{
    color:{accent};
    font-size:1.7rem;
    font-weight:700;
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
        st.caption(f"App dir: `{STREAMLIT_DIR.name}`")
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
        _ensure_streamlit_cwd()
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"Agent error: `{type(exc).__name__}: {exc}`",
                "payload": None,
            }
        )
        return
    finally:
        _ensure_streamlit_cwd()

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
    _ensure_streamlit_cwd()
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
