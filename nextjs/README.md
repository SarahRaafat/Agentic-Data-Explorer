# Next.js + FastAPI frontend

Uses `../shared/agent_core.py` automatically (`AGENT_ROOT` override supported).

From the **repo root**:

## API

```powershell
.\.venv\Scripts\activate
pip install -r shared/requirements.txt
pip install -r nextjs/api/requirements.txt
cd nextjs
uvicorn api.main:app --reload --port 8000
```

## Web

```powershell
cd nextjs/web
npm install
npm run dev
```

Open http://localhost:3000 — API must be on http://localhost:8000.
