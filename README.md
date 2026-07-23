# Agentic Data Explorer

PII-safe LangChain / LangGraph agent over Instacart Market Basket CSVs, with
**two frontends** sharing one agent core.

## Layout

```
Agentic_data_explorer/
  shared/                 # common to both UIs
    agent_core.py         # agents, tools, PII middleware, themes
    archive (3)/          # CSVs (local only — not in git)
    exports/              # report downloads
    .env / .env.example   # ANTHROPIC_API_KEY
    requirements.txt
  streamlit/              # Streamlit UI
    app.py
    charts.py
    project.ipynb
    .streamlit/
  nextjs/                 # Next.js UI + FastAPI
    api/                  # uvicorn → ask_viz
    web/                  # App Router frontend
  README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+ (only for the Next.js UI) — must be on PATH
- An [Anthropic API key](https://console.anthropic.com/)
- Instacart CSVs in `shared/archive (3)/` (see Dataset)

## Setup (once)

From the **repo root** (`Agentic_data_explorer`):

```powershell
python -m venv .venv
.\.venv\Scripts\activate

pip install -r shared\requirements.txt
pip install -r streamlit\requirements.txt
pip install -r nextjs\api\requirements.txt

copy shared\.env.example shared\.env
# Edit shared\.env → ANTHROPIC_API_KEY=...
```

If `pip` / `uvicorn` say they cannot find `special_task`, recreate `.venv` (old launchers after a folder rename).

## Dataset

CSVs are **not** in git. Download Instacart Market Basket Analysis from
[Kaggle](https://www.kaggle.com/c/instacart-market-basket-analysis/data) and put
these in `shared/archive (3)/`:

`aisles.csv`, `departments.csv`, `products.csv`, `orders.csv`,
`order_products__prior.csv`, `order_products__train.csv`

## Run Streamlit

```powershell
cd Agentic_data_explorer
.\.venv\Scripts\activate
cd streamlit
streamlit run app.py
```

Open http://localhost:8501

Always start from the `streamlit/` folder (not from `shared/archive (3)/`).

## Run Next.js (two terminals)

**Terminal 1 — API**

```powershell
cd Agentic_data_explorer
.\.venv\Scripts\activate
cd nextjs
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — UI**

```powershell
cd Agentic_data_explorer\nextjs\web
npm install
npm run dev
```

Open http://localhost:3000 (API must be on :8000).

## Notes

- Never commit `shared/.env` or `shared/archive (3)/*.csv`.
- Both UIs use `shared/agent_core.py`.
- More Next.js detail: [`nextjs/README.md`](nextjs/README.md).
