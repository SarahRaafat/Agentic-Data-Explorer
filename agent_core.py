"""PII-safe Instacart explorer + visualization agents.

Shared by project.ipynb and the Streamlit frontend (app.py).

Tools available to the viz agent:
  list_data_files, run_python, filter_dataframe,
  recommend_chart, create_visualization (alias: create_chart),
  generate_insights, explain_visualization,
  generate_dashboard_layout, build_dashboard,
  change_theme, export_report, ask_visualization_critic
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage
from langchain.tools import tool
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel, Field

SPECIAL_TASK_DIR = Path(__file__).resolve().parent
DATA_DIR = (SPECIAL_TASK_DIR / "archive (3)").resolve()
EXPORT_DIR = (SPECIAL_TASK_DIR / "exports").resolve()
EXPORT_DIR.mkdir(exist_ok=True)

load_dotenv(SPECIAL_TASK_DIR / ".env")
load_dotenv(SPECIAL_TASK_DIR.parent / ".env")

MODEL = "anthropic:claude-haiku-4-5"

PII_COLUMNS = frozenset({"user_id"})
FORBIDDEN_CODE_TOKENS = (
    "user_id",
    "customer_id",
    "email",
    "phone",
    "ssn",
    "passport",
    "address",
)
PII_OUTPUT_PATTERNS = (
    (re.compile(r"user_id\s*[:=]\s*\d+", re.I), "user_id=[REDACTED]"),
    (re.compile(r"\b\d{4,}\s+unique customers\b", re.I), "[REDACTED: customer count]"),
    (re.compile(r"unique customers[^\n.]*", re.I), "[REDACTED: per-customer stat]"),
    (re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b"), "[REDACTED: email]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED: phone]"),
)

TIME_HINTS = (
    "hour",
    "day",
    "week",
    "month",
    "year",
    "date",
    "time",
    "dow",
    "order_hour",
    "order_dow",
)

THEMES: dict[str, dict[str, str]] = {
    "light": {
        "name": "light",
        "bg": "#f7f8fa",
        "card": "#ffffff",
        "text": "#1a1a1a",
        "accent": "#2563eb",
        "plotly_template": "plotly_white",
    },
    "dark": {
        "name": "dark",
        "bg": "#0f1419",
        "card": "#1a2332",
        "text": "#e7ecf3",
        "accent": "#60a5fa",
        "plotly_template": "plotly_dark",
    },
    "corporate": {
        "name": "corporate",
        "bg": "#f0f4f8",
        "card": "#ffffff",
        "text": "#0b1f33",
        "accent": "#0f4c81",
        "plotly_template": "plotly_white",
    },
    "minimal": {
        "name": "minimal",
        "bg": "#fafafa",
        "card": "#ffffff",
        "text": "#222222",
        "accent": "#444444",
        "plotly_template": "simple_white",
    },
}

# In-memory stores for filtered frames + last viz session artifacts
_DATAFRAMES: dict[str, pd.DataFrame] = {}
_SESSION: dict[str, Any] = {
    "theme": THEMES["dark"].copy(),
    "last_dashboard": None,
    "last_charts": [],
    "last_insights": [],
    "last_layout": None,
}


def redact_text(text: str) -> str:
    redacted = text
    for pattern, replacement in PII_OUTPUT_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def validate_code(code: str) -> str | None:
    lower = code.lower()
    if "pd.read_csv" in lower or "pandas.read_csv" in lower:
        return (
            "Blocked by PII policy: use safe_read_csv() instead of pd.read_csv() "
            "so user_id and other PII columns are dropped automatically."
        )
    for token in FORBIDDEN_CODE_TOKENS:
        if token in lower:
            return (
                f"Blocked by PII policy: code must not reference '{token}'. "
                "Use aggregate product/order stats only — never individual customers."
            )
    return None


def safe_read_csv(path, **kwargs):
    """Load a CSV and automatically drop known PII columns."""
    df = pd.read_csv(path, **kwargs)
    drop = [c for c in df.columns if c in PII_COLUMNS]
    if drop:
        df = df.drop(columns=drop)
    return df


def _looks_like_time(labels: list[str], x_label: str = "") -> bool:
    blob = " ".join([x_label, *labels[:5]]).lower()
    if any(h in blob for h in TIME_HINTS):
        return True
    # sequential integers 0..n often mean hour/dow
    try:
        nums = [int(float(x)) for x in labels]
        if nums == list(range(min(nums), min(nums) + len(nums))):
            return True
    except (TypeError, ValueError):
        pass
    return False


def _recommend_chart_logic(
    labels: list[str],
    values: list[float],
    x_label: str = "",
    y_label: str = "",
    prefer_proportion: bool = False,
) -> dict[str, Any]:
    n = len(labels)
    if n == 0:
        return {
            "recommended_chart": "bar",
            "reason": "Empty data; defaulting to bar.",
            "confidence": 0.2,
        }
    if prefer_proportion or (
        y_label and any(k in y_label.lower() for k in ("share", "pct", "percent", "proportion"))
    ):
        if n <= 8:
            return {
                "recommended_chart": "pie",
                "reason": "Few categories with proportion-like measure → pie.",
                "confidence": 0.85,
            }
        return {
            "recommended_chart": "bar",
            "reason": f"{n} categories is too many for a readable pie → bar.",
            "confidence": 0.9,
        }
    if _looks_like_time(labels, x_label):
        return {
            "recommended_chart": "line",
            "reason": "Labels look temporal (time/hour/day) → line chart.",
            "confidence": 0.9,
        }
    if n > 12:
        return {
            "recommended_chart": "bar",
            "reason": f"{n} categories → horizontal-friendly bar ranking.",
            "confidence": 0.85,
        }
    return {
        "recommended_chart": "bar",
        "reason": "Categorical labels with numeric values → bar chart.",
        "confidence": 0.8,
    }


class ChartSpec(BaseModel):
    """Frontend-ready chart specification."""

    chart_type: Literal["line", "bar", "pie", "scatter", "area", "horizontal_bar"]
    title: str
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    x_label: str = ""
    y_label: str = ""


class Critique(BaseModel):
    """Structured review from the visualization critic."""

    approved: bool
    issues: list[str] = Field(default_factory=list)
    suggested_chart_type: str | None = None
    reason: str


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def list_data_files() -> list[dict]:
    """List CSV files in the dataset folder with size in MB."""
    return [
        {"file": p.name, "size_mb": round(p.stat().st_size / 1_048_576, 2)}
        for p in sorted(DATA_DIR.glob("*.csv"))
    ]


@tool
def run_python(code: str) -> str:
    """Write and execute Python code to explore the dataset.
    DATA_DIR is a Path to the archive (3) folder. pandas is available as pd.
    Use safe_read_csv() for CSV loads — it drops PII columns such as user_id.
    Filtered frames are available as FILTERED[name] if you called filter_dataframe.
    Never access user_id or other identifiers. Always print() results."""
    blocked = validate_code(code)
    if blocked:
        return blocked

    stdout = io.StringIO()
    namespace = {
        "DATA_DIR": DATA_DIR,
        "Path": Path,
        "pd": pd,
        "safe_read_csv": safe_read_csv,
        "json": json,
        "FILTERED": _DATAFRAMES,
    }
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {"__builtins__": __builtins__}, namespace)
        output = redact_text(stdout.getvalue().strip())
        return output if output else "Code ran successfully (no printed output)."
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"


@tool
def filter_dataframe(
    source_file: str,
    filters: dict[str, Any],
    output_name: str = "filtered",
    nrows: int | None = 200_000,
) -> dict:
    """Load a CSV with safe_read_csv and keep only matching rows.

    filters: column → value or list of values (equality / isin).
    Example: source_file='products.csv', filters={'department_id': 4},
             output_name='produce_products'
    Stores the result as FILTERED[output_name] for later run_python use.
    """
    path = DATA_DIR / source_file
    if not path.exists():
        return {"error": f"File not found: {source_file}"}
    if any(str(k).lower() in FORBIDDEN_CODE_TOKENS for k in filters):
        return {"error": "Blocked by PII policy: filter keys must not reference identifiers."}

    kwargs: dict[str, Any] = {}
    if nrows is not None:
        kwargs["nrows"] = nrows
    df = safe_read_csv(path, **kwargs)
    before = len(df)
    for col, value in filters.items():
        if col not in df.columns:
            return {"error": f"Column '{col}' not in {list(df.columns)}"}
        if isinstance(value, list):
            df = df[df[col].isin(value)]
        else:
            df = df[df[col] == value]
    after = len(df)
    _DATAFRAMES[output_name] = df.reset_index(drop=True)
    preview = df.head(5).to_dict(orient="records")
    return {
        "output_name": output_name,
        "rows_before": before,
        "rows_after": after,
        "columns": list(df.columns),
        "preview": preview,
        "hint": f"Use FILTERED['{output_name}'] inside run_python.",
    }


@tool
def recommend_chart(
    labels: list[str],
    values: list[float],
    x_label: str = "",
    y_label: str = "",
    prefer_proportion: bool = False,
) -> dict:
    """Recommend the best chart type for label/value data (visualization expert).

    Call this before create_visualization when unsure which chart to use.
    """
    if len(labels) != len(values):
        return {"error": "labels and values must be the same length."}
    return _recommend_chart_logic(labels, values, x_label, y_label, prefer_proportion)


def _build_visualization(
    labels: list[str],
    values: list[float],
    title: str,
    chart_type: str | None = None,
    x_label: str = "",
    y_label: str = "",
) -> dict:
    if len(labels) != len(values):
        return {
            "error": (
                f"labels ({len(labels)}) and values ({len(values)}) "
                "must have the same length."
            )
        }
    if not labels:
        return {"error": "labels/values must not be empty."}

    labels_s = [str(x) for x in labels]
    values_f = [float(v) for v in values]
    chosen = chart_type
    recommendation = None
    if not chosen:
        recommendation = _recommend_chart_logic(labels_s, values_f, x_label, y_label)
        chosen = recommendation["recommended_chart"]

    allowed = {"line", "bar", "pie", "scatter", "area", "horizontal_bar"}
    if chosen not in allowed:
        return {"error": f"Unsupported chart_type '{chosen}'. Use one of {sorted(allowed)}."}

    if chosen == "pie" and len(labels_s) > 10:
        recommendation = {
            "recommended_chart": "bar",
            "reason": "Auto-switched: pie with >10 slices is hard to read.",
            "confidence": 1.0,
        }
        chosen = "bar"

    spec = ChartSpec(
        chart_type=chosen,  # type: ignore[arg-type]
        title=title,
        labels=labels_s,
        values=values_f,
        x_label=x_label or "",
        y_label=y_label or "",
    )
    payload = spec.model_dump()
    payload["tool"] = "create_visualization"
    if recommendation:
        payload["recommendation"] = recommendation
    _SESSION["last_charts"] = _SESSION.get("last_charts", []) + [payload]
    return payload


@tool
def create_visualization(
    labels: list[str],
    values: list[float],
    title: str,
    chart_type: str | None = None,
    x_label: str = "",
    y_label: str = "",
) -> dict:
    """Turn analyzed label/value data into a frontend chart spec.

    Separates analysis from presentation: pass real aggregates from run_python.
    If chart_type is omitted, recommend_chart logic is used automatically.
    chart_type: line | bar | pie | scatter | area | horizontal_bar
    """
    return _build_visualization(
        labels=labels,
        values=values,
        title=title,
        chart_type=chart_type,
        x_label=x_label,
        y_label=y_label,
    )


@tool
def create_chart(
    chart_type: Literal["line", "bar", "pie", "scatter", "area", "horizontal_bar"],
    title: str,
    labels: list[str],
    values: list[float],
    x_label: str = "",
    y_label: str = "",
) -> dict:
    """Alias for create_visualization with an explicit chart_type."""
    return _build_visualization(
        labels=labels,
        values=values,
        title=title,
        chart_type=chart_type,
        x_label=x_label,
        y_label=y_label,
    )


@tool
def generate_insights(
    labels: list[str],
    values: list[float],
    title: str = "",
    unit: str = "",
) -> dict:
    """Convert chart data into short bullet insights (what the numbers mean)."""
    if not labels or len(labels) != len(values):
        return {"error": "Need non-empty labels/values of equal length."}

    pairs = sorted(
        zip([str(l) for l in labels], [float(v) for v in values]),
        key=lambda x: x[1],
        reverse=True,
    )
    total = sum(v for _, v in pairs) or 1.0
    top_l, top_v = pairs[0]
    bot_l, bot_v = pairs[-1]
    top_share = 100.0 * top_v / total
    insights = [
        f"{top_l} is the largest ({top_v:,.0f}{(' ' + unit) if unit else ''}), "
        f"about {top_share:.1f}% of the total.",
        f"{bot_l} is the smallest ({bot_v:,.0f}{(' ' + unit) if unit else ''}).",
    ]
    if len(pairs) >= 3:
        top2 = pairs[0][1] + pairs[1][1]
        insights.append(
            f"{pairs[0][0]} and {pairs[1][0]} together account for "
            f"{100.0 * top2 / total:.1f}% of the total."
        )
    if title:
        insights.insert(0, f"Insight summary for “{title}”.")

    payload = {"tool": "generate_insights", "insights": insights, "title": title}
    _SESSION["last_insights"] = insights
    return payload


@tool
def explain_visualization(
    chart_type: str,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> dict:
    """Explain how to read/interpret the chart (not what the data concludes)."""
    explanations = {
        "bar": (
            "Each bar is a category. Taller (or longer, if horizontal) bars mean "
            "larger values. Compare bar lengths to rank categories."
        ),
        "horizontal_bar": (
            "Each horizontal bar is a category. Longer bars mean larger values — "
            "useful when category names are long."
        ),
        "line": (
            "Points are connected in order along the x-axis (often time). "
            "An upward slope means values increased; a downward slope means they fell."
        ),
        "area": (
            "Like a line chart, but the filled area emphasizes magnitude over time. "
            "Higher fill means larger values at that point."
        ),
        "pie": (
            "Each slice is a share of the whole. Larger slices are bigger proportions. "
            "Use pie charts only when there are few categories."
        ),
        "scatter": (
            "Each point is an observation. Look for clusters, trends, or outliers "
            "across the two axes."
        ),
    }
    base = explanations.get(
        chart_type,
        "Read the axis labels and compare relative sizes of the visual marks.",
    )
    parts = [base]
    if x_label or y_label:
        parts.append(
            f"Axes: x = {x_label or '(categories)'}, y = {y_label or '(values)'}."
        )
    if title:
        parts.append(f"This chart is titled “{title}”.")
    return {
        "tool": "explain_visualization",
        "chart_type": chart_type,
        "explanation": " ".join(parts),
    }


@tool
def generate_dashboard_layout(
    include_sidebar: bool = True,
    include_kpis: bool = True,
    include_charts: bool = True,
    include_table: bool = True,
    include_insights: bool = True,
) -> dict:
    """Decide where dashboard components appear (structure only, no charts)."""
    layout = {
        "tool": "generate_dashboard_layout",
        "regions": [],
    }
    if include_sidebar:
        layout["regions"].append(
            {
                "id": "sidebar",
                "position": "left",
                "components": ["dataset_selector", "filters", "theme"],
            }
        )
    if include_kpis:
        layout["regions"].append(
            {
                "id": "kpis",
                "position": "top",
                "components": ["kpi_cards"],
            }
        )
    if include_charts:
        layout["regions"].append(
            {
                "id": "main",
                "position": "center",
                "components": ["main_chart", "secondary_charts"],
            }
        )
    if include_insights:
        layout["regions"].append(
            {
                "id": "insights",
                "position": "right",
                "components": ["insight_bullets"],
            }
        )
    if include_table:
        layout["regions"].append(
            {
                "id": "table",
                "position": "bottom",
                "components": ["data_table"],
            }
        )
    _SESSION["last_layout"] = layout
    return layout


@tool
def build_dashboard(
    title: str,
    kpis: list[dict[str, Any]] | None = None,
    charts: list[dict[str, Any]] | None = None,
    table: dict[str, Any] | None = None,
    insights: list[str] | None = None,
    layout: dict[str, Any] | None = None,
) -> dict:
    """Assemble a full dashboard payload for the frontend.

    kpis: list of {label, value} e.g. [{"label":"Total Orders","value":3421083}]
    charts: list of create_visualization specs (or {chart_type,title,labels,values})
    table: optional {columns: [...], rows: [[...], ...]} or {records: [...]}
    insights: bullet strings from generate_insights
    layout: from generate_dashboard_layout (optional)
    """
    chart_list = charts or list(_SESSION.get("last_charts") or [])
    insight_list = insights or list(_SESSION.get("last_insights") or [])
    layout_obj = layout or _SESSION.get("last_layout") or generate_dashboard_layout.invoke({})

    dashboard = {
        "tool": "build_dashboard",
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "theme": _SESSION["theme"]["name"],
        "kpis": kpis or [],
        "charts": chart_list,
        "table": table,
        "insights": insight_list,
        "layout": layout_obj,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _SESSION["last_dashboard"] = dashboard
    _SESSION["last_charts"] = chart_list
    return dashboard


@tool
def change_theme(
    theme: Literal["light", "dark", "corporate", "minimal"] = "light",
) -> dict:
    """Change dashboard appearance (colors/template) without changing data."""
    if theme not in THEMES:
        return {"error": f"Unknown theme '{theme}'. Choose from {list(THEMES)}."}
    _SESSION["theme"] = THEMES[theme].copy()
    if _SESSION.get("last_dashboard"):
        _SESSION["last_dashboard"]["theme"] = theme
    return {
        "tool": "change_theme",
        "theme": THEMES[theme],
        "message": f"Theme set to '{theme}'.",
    }


@tool
def export_report(
    format: Literal["csv", "excel", "json", "markdown", "pdf"] = "markdown",
    title: str = "Instacart report",
) -> dict:
    """Export the last dashboard / charts to a downloadable file under exports/.

    Formats: csv, excel, json, markdown, pdf (text-based PDF-style report).
    """
    EXPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\-]+", "_", title).strip("_") or "report"
    dashboard = _SESSION.get("last_dashboard")
    charts = (dashboard or {}).get("charts") or _SESSION.get("last_charts") or []
    insights = (dashboard or {}).get("insights") or _SESSION.get("last_insights") or []

    if format == "json":
        path = EXPORT_DIR / f"{safe_title}_{stamp}.json"
        payload = dashboard or {"charts": charts, "insights": insights, "title": title}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"tool": "export_report", "format": format, "path": str(path)}

    if format == "csv":
        if not charts:
            return {"error": "No chart data to export. Build a chart/dashboard first."}
        path = EXPORT_DIR / f"{safe_title}_{stamp}.csv"
        rows = []
        for c in charts:
            for lab, val in zip(c.get("labels", []), c.get("values", [])):
                rows.append(
                    {
                        "chart_title": c.get("title", ""),
                        "chart_type": c.get("chart_type", ""),
                        "label": lab,
                        "value": val,
                    }
                )
        pd.DataFrame(rows).to_csv(path, index=False)
        return {"tool": "export_report", "format": format, "path": str(path)}

    if format == "excel":
        if not charts:
            return {"error": "No chart data to export. Build a chart/dashboard first."}
        path = EXPORT_DIR / f"{safe_title}_{stamp}.xlsx"
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for i, c in enumerate(charts):
                    sheet = (c.get("title") or f"chart_{i+1}")[:31]
                    pd.DataFrame(
                        {"label": c.get("labels", []), "value": c.get("values", [])}
                    ).to_excel(writer, sheet_name=sheet or f"chart_{i+1}", index=False)
                if insights:
                    pd.DataFrame({"insight": insights}).to_excel(
                        writer, sheet_name="insights", index=False
                    )
        except ImportError:
            return {
                "error": "openpyxl not installed. Run: pip install openpyxl",
            }
        return {"tool": "export_report", "format": format, "path": str(path)}

    # markdown / pdf (text report)
    lines = [f"# {title}", "", f"Generated: {stamp}", ""]
    if dashboard and dashboard.get("kpis"):
        lines.append("## KPIs")
        for kpi in dashboard["kpis"]:
            lines.append(f"- **{kpi.get('label')}**: {kpi.get('value')}")
        lines.append("")
    if insights:
        lines.append("## Insights")
        for bullet in insights:
            lines.append(f"- {bullet}")
        lines.append("")
    if charts:
        lines.append("## Charts")
        for c in charts:
            lines.append(f"### {c.get('title')} ({c.get('chart_type')})")
            for lab, val in zip(c.get("labels", []), c.get("values", [])):
                lines.append(f"- {lab}: {val}")
            lines.append("")

    text = "\n".join(lines)
    if format == "markdown":
        path = EXPORT_DIR / f"{safe_title}_{stamp}.md"
        path.write_text(text, encoding="utf-8")
        return {"tool": "export_report", "format": format, "path": str(path)}

    # pdf: write a .txt/.pdf-compatible plain report (no heavy PDF lib required)
    path = EXPORT_DIR / f"{safe_title}_{stamp}.pdf.txt"
    path.write_text(text, encoding="utf-8")
    return {
        "tool": "export_report",
        "format": "pdf",
        "path": str(path),
        "note": "Plain-text PDF-style report (open or rename). Install a PDF lib later for binary PDFs.",
    }


@tool
def ask_visualization_critic(
    chart_type: str,
    title: str,
    labels: list[str],
    values: list[float],
) -> dict:
    """Second-agent review: critique chart choice and suggest improvements.

    Call after create_visualization. If not approved, regenerate with the suggestion.
    """
    n = len(labels)
    heuristic_issues: list[str] = []
    suggested = None

    if chart_type == "pie" and n > 8:
        heuristic_issues.append(
            f"Pie chart has {n} categories; slices will be hard to compare."
        )
        suggested = "horizontal_bar" if n > 12 else "bar"
    if chart_type in {"line", "area"} and not _looks_like_time(labels):
        heuristic_issues.append(
            "Line/area charts work best with ordered/temporal x values."
        )
        suggested = suggested or "bar"
    if n > 20 and chart_type == "bar":
        heuristic_issues.append(
            "Many categories — consider top-N filter or horizontal_bar."
        )
        suggested = suggested or "horizontal_bar"
    if n <= 2 and chart_type == "pie":
        heuristic_issues.append("Only a few slices; a bar chart may be clearer.")

    # LLM critic (structured) — falls back to heuristics if call fails
    critique: dict[str, Any]
    try:
        critic = get_llm().with_structured_output(Critique)
        prompt = (
            "You are a visualization critic. Review this chart choice for clarity.\n"
            f"chart_type={chart_type}, title={title}, n_categories={n}\n"
            f"labels_sample={labels[:12]}, values_sample={values[:12]}\n"
            "Approve only if the chart type fits the data. "
            "If pie has many categories, reject it."
        )
        result: Critique = critic.invoke(prompt)
        critique = result.model_dump()
        # Merge heuristics
        for issue in heuristic_issues:
            if issue not in critique["issues"]:
                critique["issues"].append(issue)
        if suggested and not critique.get("suggested_chart_type"):
            critique["suggested_chart_type"] = suggested
        if heuristic_issues and critique.get("approved") and suggested:
            critique["approved"] = False
            critique["reason"] = (
                critique.get("reason", "")
                + " Heuristic rules also flagged readability issues."
            ).strip()
    except Exception as exc:
        critique = {
            "approved": len(heuristic_issues) == 0,
            "issues": heuristic_issues,
            "suggested_chart_type": suggested,
            "reason": (
                "Heuristic-only review "
                f"(LLM critic unavailable: {type(exc).__name__})."
            ),
        }

    return {"tool": "ask_visualization_critic", "critique": critique}


class PIIMiddleware(AgentMiddleware):
    """Redact PII from tool outputs before they re-enter the model context."""

    def wrap_model_call(self, request, handler):
        blocks = list(request.system_message.content_blocks)
        blocks.append(
            {
                "type": "text",
                "text": (
                    "\n## PII policy (strict)\n"
                    "- Never read, print, count, or infer from user_id or other identifiers.\n"
                    "- Use safe_read_csv(); do not use pd.read_csv on orders.csv directly.\n"
                    "- Report product, department, aisle, and order-level aggregates only.\n"
                    "- Do not report unique customer counts or per-customer behavior."
                ),
            }
        )
        request = request.override(system_message=SystemMessage(content=blocks))
        response = handler(request)

        for msg in getattr(response, "messages", []) or []:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                msg.content = redact_text(msg.content)
        return response


EXPLORER_INSTRUCTIONS = """You are a PII-safe data exploration agent for the Instacart-style
dataset in archive (3)/.

You explore by WRITING Python from scratch and running it with run_python.
Start with list_data_files, then inspect schemas, row counts, and samples.

PII RULES — never break these:
- Do NOT access user_id, customer_id, email, phone, or any personal identifiers.
- Always load CSVs with safe_read_csv(), not pd.read_csv(), so PII columns are dropped.
- Never report unique customer counts or individual customer behavior.
- Stick to product, department, aisle, and order-level aggregates (e.g. orders by day/hour).

Never invent numbers — every statistic must come from code you executed.
Large files: use nrows=, head(), value_counts on samples, or chunked reads.
Show your working briefly, then end with a clear summary of findings."""

VIZ_INSTRUCTIONS = """You are a PII-safe data visualization agent for the Instacart-style
dataset in archive (3)/.

Preferred workflow:
1. list_data_files / filter_dataframe when needed
2. run_python (safe_read_csv) to compute real aggregates — never invent numbers
3. recommend_chart when unsure of chart type
4. create_visualization with those labels/values
5. ask_visualization_critic — if not approved, recreate with suggested_chart_type
6. generate_insights + explain_visualization
7. For full pages: generate_dashboard_layout → build_dashboard
8. change_theme or export_report when the user asks

Tools:
- filter_dataframe: subset rows before analysis
- recommend_chart: visualization expert for chart type
- create_visualization / create_chart: turn data into a graph spec
- generate_insights: what the numbers mean
- explain_visualization: how to read the chart
- generate_dashboard_layout: page structure only
- build_dashboard: full dashboard payload for the frontend
- change_theme: light | dark | corporate | minimal
- export_report: csv | excel | json | markdown | pdf
- ask_visualization_critic: second-agent review of chart quality

PII RULES — never break these:
- Do NOT access user_id, customer_id, email, phone, or any personal identifiers.
- Always load CSVs with safe_read_csv(), not pd.read_csv().
- Never report unique customer counts or individual customer behavior.
- Stick to product, department, aisle, and order-level aggregates.

Large files: use nrows=, samples, or chunked reads when needed.
Prefer at most ~8 categories on pie charts; top-N for long-tail rankings."""


VIZ_TOOLS = [
    list_data_files,
    run_python,
    filter_dataframe,
    recommend_chart,
    create_visualization,
    create_chart,
    generate_insights,
    explain_visualization,
    generate_dashboard_layout,
    build_dashboard,
    change_theme,
    export_report,
    ask_visualization_critic,
]

_llm = None
_explorer = None
_viz_agent = None


def get_llm(model: str | None = None):
    global _llm
    if _llm is None or (model and model != MODEL):
        _llm = init_chat_model(model or MODEL)
    return _llm


def get_explorer(model: str | None = None):
    global _explorer
    if _explorer is None:
        _explorer = create_agent(
            model=get_llm(model),
            system_prompt=EXPLORER_INSTRUCTIONS,
            tools=[list_data_files, run_python],
            middleware=[PIIMiddleware()],
        )
    return _explorer


def get_viz_agent(model: str | None = None):
    global _viz_agent
    # Rebuild if tools list grew (dev reload safety)
    if _viz_agent is None:
        _viz_agent = create_agent(
            model=get_llm(model),
            system_prompt=VIZ_INSTRUCTIONS,
            tools=VIZ_TOOLS,
            middleware=[PIIMiddleware()],
        )
    return _viz_agent


def reset_viz_agent() -> None:
    """Force recreate after code changes (e.g. in notebooks)."""
    global _viz_agent
    _viz_agent = None


def _parse_tool_content(content: Any) -> Any:
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        # some runtimes wrap tool output
        for item in content:
            parsed = _parse_tool_content(item)
            if isinstance(parsed, dict):
                return parsed
        return None
    if not isinstance(content, str):
        return None
    text = content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _iter_tool_payloads(result: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for msg in result.get("messages", []):
        if not isinstance(msg, ToolMessage):
            continue
        name = getattr(msg, "name", None) or ""
        payload = _parse_tool_content(msg.content)
        if isinstance(payload, dict):
            out.append((name, payload))
    return out


def extract_charts(result: dict) -> list[dict]:
    """Pull chart specs from create_visualization / create_chart / dashboards."""
    charts: list[dict] = []
    seen = set()
    for name, payload in _iter_tool_payloads(result):
        candidates = []
        if name in {"create_visualization", "create_chart"} or (
            "chart_type" in payload and "labels" in payload and "values" in payload
        ):
            candidates = [payload]
        if name == "build_dashboard" or payload.get("tool") == "build_dashboard":
            candidates = list(payload.get("charts") or [])
        for spec in candidates:
            if "error" in spec:
                continue
            if not (
                "chart_type" in spec and "labels" in spec and "values" in spec
            ):
                continue
            key = (
                spec.get("title"),
                spec.get("chart_type"),
                tuple(spec.get("labels") or []),
            )
            if key in seen:
                continue
            seen.add(key)
            charts.append(spec)
    return charts


def extract_dashboards(result: dict) -> list[dict]:
    dashboards = []
    for name, payload in _iter_tool_payloads(result):
        if name == "build_dashboard" or payload.get("tool") == "build_dashboard":
            if "error" not in payload:
                dashboards.append(payload)
    return dashboards


def extract_exports(result: dict) -> list[dict]:
    exports = []
    for name, payload in _iter_tool_payloads(result):
        if name == "export_report" or payload.get("tool") == "export_report":
            if "path" in payload:
                exports.append(payload)
    return exports


def extract_theme(result: dict) -> dict | None:
    for name, payload in _iter_tool_payloads(result):
        if name == "change_theme" or payload.get("tool") == "change_theme":
            if "theme" in payload and "error" not in payload:
                return payload["theme"]
    return None


def extract_insights(result: dict) -> list[str]:
    insights: list[str] = []
    for name, payload in _iter_tool_payloads(result):
        if name == "generate_insights" or payload.get("tool") == "generate_insights":
            insights.extend(payload.get("insights") or [])
        if name == "build_dashboard" or payload.get("tool") == "build_dashboard":
            insights.extend(payload.get("insights") or [])
    # dedupe preserving order
    seen = set()
    ordered = []
    for item in insights:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def extract_explanations(result: dict) -> list[str]:
    texts = []
    for name, payload in _iter_tool_payloads(result):
        if name == "explain_visualization" or payload.get("tool") == "explain_visualization":
            if payload.get("explanation"):
                texts.append(payload["explanation"])
    return texts


def extract_critiques(result: dict) -> list[dict]:
    critiques = []
    for name, payload in _iter_tool_payloads(result):
        if name == "ask_visualization_critic" or payload.get("tool") == "ask_visualization_critic":
            if "critique" in payload:
                critiques.append(payload["critique"])
    return critiques


def final_text(result: dict) -> str:
    """Last AI message text, PII-redacted."""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                content = "\n".join(parts)
            if isinstance(content, str) and content.strip():
                return redact_text(content)
    return ""


def ask_viz(question: str, model: str | None = None) -> dict[str, Any]:
    """Run the visualization agent and return answer + UI artifacts."""
    # Clear per-request chart buffer so dashboards don't accumulate forever
    _SESSION["last_charts"] = []
    agent = get_viz_agent(model)
    result = agent.invoke({"messages": [HumanMessage(question)]})
    theme = extract_theme(result)
    if theme and isinstance(theme, dict) and "name" in theme:
        _SESSION["theme"] = {**THEMES.get(theme["name"], THEMES["light"]), **theme}
    return {
        "answer": final_text(result),
        "charts": extract_charts(result),
        "dashboards": extract_dashboards(result),
        "insights": extract_insights(result),
        "explanations": extract_explanations(result),
        "critiques": extract_critiques(result),
        "exports": extract_exports(result),
        "theme": theme,  # only set when change_theme was called; else None
        "raw": result,
    }


def ask_explorer(question: str, model: str | None = None) -> dict[str, Any]:
    """Run the exploration agent and return the final answer text."""
    agent = get_explorer(model)
    result = agent.invoke({"messages": [HumanMessage(question)]})
    return {
        "answer": final_text(result),
        "raw": result,
    }


def get_session() -> dict[str, Any]:
    return _SESSION
