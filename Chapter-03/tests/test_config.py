from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "proxy"))

from config import load_settings  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_google_api_key_takes_precedence(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google", "GEMINI_API_KEY": "gemini"}, clear=False):
            self.assertEqual(load_settings().api_key, "google")

    def test_chapter3_defaults_use_canonical_live_model(self) -> None:
        with patch.dict(os.environ, {"CHAPTER3_LIVE_MODEL": "", "CHAPTER3_FALLBACK_LIVE_MODEL": ""}, clear=False):
            settings = load_settings()
        self.assertEqual(settings.live_model, "gemini-3.1-flash-live-preview")
        self.assertEqual(settings.fallback_live_model, "gemini-2.5-flash-native-audio-preview-12-2025")

    def test_runtime_urls_follow_port_overrides(self) -> None:
        env = {
            "CHAPTER3_PROXY_HOST": "127.0.0.1",
            "CHAPTER3_PROXY_PORT": "8099",
            "CHAPTER3_FRONTEND_HOST": "127.0.0.1",
            "CHAPTER3_FRONTEND_PORT": "8011",
            "CHAPTER3_LIVE_WS_URL": "",
            "CHAPTER3_ALLOWED_ORIGINS": "",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = load_settings()

        self.assertEqual(settings.live_ws_url, "ws://127.0.0.1:8099/live")
        self.assertIn("http://127.0.0.1:8011", settings.allowed_origins)


if __name__ == "__main__":
    unittest.main()
