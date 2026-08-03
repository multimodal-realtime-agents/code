from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "backend" / "server.py"


def load_frontend_server_module():
    spec = importlib.util.spec_from_file_location("chapter3_frontend_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Chapter 3 frontend server module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FrontendServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_frontend_server_module()

    def test_index_path_exists(self) -> None:
        self.assertTrue(self.server.index_path().exists())

    def test_runtime_config_exposes_live_websocket_url(self) -> None:
        payload = self.server.runtime_config_payload()
        self.assertIn("live_ws_url", payload)
        self.assertTrue(payload["live_ws_url"].startswith(("ws://", "wss://")))

    def test_health_payload_reports_current_model(self) -> None:
        payload = self.server.health_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["live_model"], self.server.settings.live_model)


if __name__ == "__main__":
    unittest.main()
