---
title: Agentic Data Explorer
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Agentic Data Explorer

PII-safe LangChain / LangGraph agent over Instacart Market Basket CSVs, with
**two frontends** sharing one agent core.

## Deploy (shareable link)

**Streamlit Community Cloud** (GitHub login): see **[DEPLOY_STREAMLIT_CLOUD.md](DEPLOY_STREAMLIT_CLOUD.md)**  
Main file: `streamlit/app.py` → public `https://….streamlit.app` URL.

Optional Hugging Face Spaces (Docker): **[DEPLOY_HF_SPACES.md](DEPLOY_HF_SPACES.md)**

## Layout

```
Agentic_data_explorer/
  shared/                 # common to both UIs
    agent_core.py         # agents, tools, PII middleware, themes
    archive (3)/          # CSVs (local / Space LFS — not in GitHub)
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
  Dockerfile              # HF Spaces / local Docker
  DEPLOY_HF_SPACES.md
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

CSVs are **not** in the GitHub repo. Download Instacart Market Basket Analysis from
[Kaggle](https://www.kaggle.com/c/instacart-market-basket-analysis/data) and put
these in `shared/archive (3)/`:

`aisles.csv`, `departments.csv`, `products.csv`, `orders.csv`,
`order_products__prior.csv`, `order_products__train.csv`

For Hugging Face Spaces, push them with **Git LFS** (see [DEPLOY_HF_SPACES.md](DEPLOY_HF_SPACES.md)).

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

- Never commit `shared/.env` or (on GitHub) `shared/archive (3)/*.csv`.
- Both UIs use `shared/agent_core.py`.
- Streamlit resolves `shared/` via `Path(__file__)` (works under Docker / Spaces regardless of process CWD).
- More Next.js detail: [`nextjs/README.md`](nextjs/README.md).
