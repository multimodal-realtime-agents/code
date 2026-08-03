import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import server  # noqa: E402
from server import health_payload, index_path, runtime_config_payload  # noqa: E402


class FrontendServiceTests(unittest.TestCase):
    def test_index_path_points_to_chapter_4_ui(self):
        body = index_path().read_text(encoding="utf-8")

        self.assertIn("Chapter 4 direct Live API app", body)
        self.assertIn('/static/app.js', body)

    def test_config_json_payload_returns_live_ws_url(self):
        self.assertEqual(runtime_config_payload(), {"live_ws_url": server.settings.live_ws_url})

    def test_health_payload_reports_model_and_endpoint(self):
        payload = health_payload()

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["live_model"], server.settings.live_model)
        self.assertEqual(payload["live_ws_url"], server.settings.live_ws_url)


if __name__ == "__main__":
    unittest.main()
