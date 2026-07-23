"""FastAPI wrapper around shared/agent_core.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# nextjs/ -> repo root -> shared/
WEB_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WEB_ROOT.parent
DEFAULT_AGENT_ROOT = (REPO_ROOT / "shared").resolve()
AGENT_ROOT = Path(os.environ.get("AGENT_ROOT", str(DEFAULT_AGENT_ROOT))).resolve()

if not AGENT_ROOT.exists():
    raise RuntimeError(f"AGENT_ROOT not found: {AGENT_ROOT}")

# agent_core loads .env and resolves DATA_DIR relative to its file location.
# Stay in nextjs/ for the server process — never chdir into archive (3)/
# (parentheses break some tooling). shared/ is only on sys.path.
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agent_core import (  # noqa: E402
    DATA_DIR,
    EXPORT_DIR,
    MODEL,
    THEMES,
    ask_viz,
    change_theme,
)

app = FastAPI(title="Agentic Data Explorer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


class ThemeRequest(BaseModel):
    theme: str = Field(..., pattern="^(light|dark)$")


def _json_safe(obj: Any) -> Any:
    """Drop non-JSON pieces (e.g. raw LangChain messages) from ask_viz output."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items() if k != "raw"}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if hasattr(obj, "model_dump"):
        return _json_safe(obj.model_dump())
    if hasattr(obj, "dict"):
        return _json_safe(obj.dict())
    return str(obj)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent_root": str(AGENT_ROOT)}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    files: list[str] = []
    if DATA_DIR.exists():
        files = sorted(p.name for p in DATA_DIR.glob("*.csv"))
    return {
        "model": MODEL,
        "dataset": DATA_DIR.name,
        "dataset_exists": DATA_DIR.exists(),
        "files": files,
        "themes": {name: dict(tokens) for name, tokens in THEMES.items()},
        "agent_root": str(AGENT_ROOT),
    }


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict[str, Any]:
    try:
        result = ask_viz(body.question.strip())
    except Exception as exc:  # noqa: BLE001 — surface agent errors to UI
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _json_safe(result)


@app.post("/api/theme")
def set_theme(body: ThemeRequest) -> dict[str, Any]:
    try:
        # change_theme is a LangChain @tool — invoke via .invoke / __call__
        if hasattr(change_theme, "invoke"):
            payload = change_theme.invoke({"theme": body.theme})
        else:
            payload = change_theme(body.theme)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _json_safe(payload)


@app.get("/api/exports/{filename}")
def download_export(filename: str) -> FileResponse:
    # Prevent path traversal
    safe = Path(filename).name
    path = (EXPORT_DIR / safe).resolve()
    if not str(path).startswith(str(EXPORT_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, filename=safe)
