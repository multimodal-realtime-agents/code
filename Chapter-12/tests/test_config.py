import unittest
from unittest.mock import patch

from agent_system.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_local_defaults_bind_to_loopback_addresses(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = load_settings()

        self.assertEqual(settings.backend_host, "127.0.0.1")
        self.assertEqual(settings.frontend_host, "127.0.0.1")
        self.assertEqual(settings.mcp_host, "127.0.0.1")
        self.assertEqual(settings.backend_port, 8000)
        self.assertEqual(settings.frontend_port, 8080)

    def test_cloud_run_port_sets_current_backend_port_and_container_host(self):
        with patch.dict(
            "os.environ",
            {"AGENT_SYSTEM_SERVICE": "backend", "PORT": "9090"},
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.backend_host, "0.0.0.0")
        self.assertEqual(settings.backend_port, 9090)
        self.assertEqual(settings.frontend_port, 8080)
        self.assertEqual(settings.mcp_port, 8010)

    def test_cloud_run_port_sets_current_frontend_port_and_live_ws_override(self):
        with patch.dict(
            "os.environ",
            {
                "AGENT_SYSTEM_SERVICE": "frontend",
                "PORT": "9091",
                "AGENT_SYSTEM_LIVE_WS_URL": "wss://backend.example/live",
            },
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.frontend_host, "0.0.0.0")
        self.assertEqual(settings.frontend_port, 9091)
        self.assertEqual(settings.backend_port, 8000)
        self.assertEqual(settings.live_ws_url, "wss://backend.example/live")

    def test_cloud_run_port_sets_current_specialist_ports(self):
        cases = [
            ("mcp", "mcp_port"),
            ("stock-a2a", "a2a_port"),
            ("weather-a2a", "weather_a2a_port"),
        ]
        for service_name, field_name in cases:
            with self.subTest(service_name=service_name):
                with patch.dict(
                    "os.environ",
                    {"AGENT_SYSTEM_SERVICE": service_name, "PORT": "9092"},
                    clear=True,
                ):
                    settings = load_settings()

                self.assertEqual(getattr(settings, field_name), 9092)
                self.assertEqual(settings.mcp_host, "0.0.0.0")
                self.assertEqual(settings.a2a_host, "0.0.0.0")
                self.assertEqual(settings.weather_a2a_host, "0.0.0.0")

    def test_explicit_host_and_port_overrides_still_win(self):
        with patch.dict(
            "os.environ",
            {
                "AGENT_SYSTEM_SERVICE": "backend",
                "PORT": "9090",
                "AGENT_SYSTEM_BACKEND_HOST": "127.0.0.1",
                "AGENT_SYSTEM_BACKEND_PORT": "9000",
            },
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.backend_host, "127.0.0.1")
        self.assertEqual(settings.backend_port, 9000)


if __name__ == "__main__":
    unittest.main()
