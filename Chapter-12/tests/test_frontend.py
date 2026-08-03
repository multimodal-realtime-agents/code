from types import SimpleNamespace
import unittest

from fastapi.testclient import TestClient

import agent_system.frontend as frontend


class FrontendServiceTests(unittest.TestCase):
    def test_config_json_returns_live_websocket_url(self):
        original_settings = frontend.settings
        frontend.settings = SimpleNamespace(live_ws_url="ws://127.0.0.1:8000/live")
        try:
            response = TestClient(frontend.app).get("/config.json")
        finally:
            frontend.settings = original_settings

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"live_ws_url": "ws://127.0.0.1:8000/live"})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_frontend_serves_static_ui(self):
        response = TestClient(frontend.app).get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Live Agent Workspace", response.text)


if __name__ == "__main__":
    unittest.main()
