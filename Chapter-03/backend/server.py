"""Small static frontend server for the Chapter 3 browser app."""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
PROXY_DIR = ROOT / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

from config import settings  # noqa: E402


class FrontendRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook.
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._send_file(index_path(), "text/html; charset=utf-8")
            return
        if path == "/config.json":
            self._send_json(runtime_config_payload())
            return
        if path == "/health":
            self._send_json(health_payload())
            return
        super().do_GET()

    def _send_file(self, path: Path, content_type: str) -> None:
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def index_path() -> Path:
    return FRONTEND_DIR / "index.html"


def runtime_config_payload() -> dict[str, str]:
    return {"live_ws_url": settings.live_ws_url}


def health_payload() -> dict[str, object]:
    return {
        "ok": True,
        "live_model": settings.live_model,
        "fallback_live_model": settings.fallback_live_model,
        "live_ws_url": settings.live_ws_url,
    }


if __name__ == "__main__":
    server = HTTPServer((settings.frontend_host, settings.frontend_port), FrontendRequestHandler)
    print(f"Chapter 3 frontend server starting at http://{settings.frontend_host}:{settings.frontend_port}")
    print(f"Live WebSocket URL: {settings.live_ws_url}")
    server.serve_forever()
