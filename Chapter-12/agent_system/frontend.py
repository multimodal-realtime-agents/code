"""Frontend service for the browser-facing live agent UI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings


logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app = FastAPI(title="Live Agent Workspace Frontend")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config.json")
async def runtime_config() -> JSONResponse:
    return JSONResponse(
        {"live_ws_url": settings.live_ws_url},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "live_ws_url": settings.live_ws_url}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Frontend serving Live Agent Workspace on %s:%s", settings.frontend_host, settings.frontend_port)
    uvicorn.run(app, host=settings.frontend_host, port=settings.frontend_port)
