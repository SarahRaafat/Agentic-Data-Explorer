# Agentic Data Explorer

PII-safe LangChain / LangGraph agent over the Instacart Market Basket CSVs, plus a Streamlit UI for charts, dashboards, themes, and exports.

## Features

- Explore grocery order data with a Python-capable agent (`safe_read_csv` drops PII such as `user_id`)
- Build charts and dashboards (Plotly) from real aggregates
- Theme switcher, insights, chart critic, and report export (CSV / Excel / JSON / Markdown)

## Project layout

```
Agentic_data_explorer/
  archive (3)/          # dataset CSVs (download locally — not in git)
  agent_core.py         # explorer + viz agents, tools, PII middleware
  charts.py             # ChartSpec → Plotly figures
  app.py                # Streamlit frontend
  exports/              # files from export_report()
  project.ipynb         # notebook demos
  requirements.txt
  .env.example
```

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- Instacart Market Basket Analysis CSVs (see below)

## Setup

```bash
# 1. Clone
git clone https://github.com/SarahRaafat/Agentic-Data-Explorer.git
cd Agentic-Data-Explorer

# 2. Virtual env + deps
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt

# 3. API key
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
# Edit .env and set ANTHROPIC_API_KEY=...
```

## Dataset

The CSVs are **not** committed (some files are >100 MB and exceed GitHub limits).

1. Download **Instacart Market Basket Analysis** from [Kaggle](https://www.kaggle.com/c/instacart-market-basket-analysis/data) (or your course archive).
2. Place these files inside `archive (3)/`:

| File | Notes |
|------|--------|
| `aisles.csv` | |
| `departments.csv` | |
| `products.csv` | |
| `orders.csv` | large |
| `order_products__prior.csv` | very large |
| `order_products__train.csv` | |

Folder name must stay `archive (3)` (that is what the code expects).

## Run the Streamlit app

```bash
streamlit run app.py
```

Open http://localhost:8501

## Notebook

```bash
jupyter lab project.ipynb
```

## Visualization tools

| Tool | Role |
|------|------|
| `create_visualization` | Turn analyzed labels/values into a chart spec |
| `recommend_chart` | Pick best chart type (line/bar/pie/…) |
| `build_dashboard` | Assemble KPIs + charts + table + insights |
| `generate_dashboard_layout` | Page structure only |
| `generate_insights` | Bullet takeaways from the numbers |
| `explain_visualization` | How to read the chart |
| `filter_dataframe` | Subset CSV rows before analysis |
| `export_report` | csv / excel / json / markdown / pdf-style |
| `change_theme` | light / dark / corporate / minimal |
| `ask_visualization_critic` | Second-agent review of chart quality |

Also available: `list_data_files`, `run_python`, and `create_chart` (alias).

## Example prompts

- Show a line chart of orders by hour of day, then explain and generate insights
- Bar chart of top 10 departments by product count — ask the critic to review it
- Build a dashboard for this grocery dataset with KPIs and charts
- Switch to dark mode and export the last dashboard as markdown

## Notes

- Never commit `.env` — it is gitignored.
- Do not commit `archive (3)/*.csv` — too large for GitHub; keep them local only.
