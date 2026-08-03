from types import SimpleNamespace
import unittest

from fastapi.testclient import TestClient

import agent_system.stock_a2a_agent as stock_a2a_agent
import agent_system.weather_a2a_agent as weather_a2a_agent


class StockA2AAgentTests(unittest.TestCase):
    def test_agent_card_advertises_configured_public_url(self):
        original_settings = stock_a2a_agent.settings
        stock_a2a_agent.settings = SimpleNamespace(a2a_url="https://stock-specialist.example")
        try:
            card = stock_a2a_agent.build_agent_card()
        finally:
            stock_a2a_agent.settings = original_settings

        self.assertEqual(
            card.supported_interfaces[0].url,
            "https://stock-specialist.example/a2a/jsonrpc",
        )

    def test_weather_agent_card_advertises_configured_public_url(self):
        original_settings = weather_a2a_agent.settings
        weather_a2a_agent.settings = SimpleNamespace(weather_a2a_url="https://weather-specialist.example")
        try:
            card = weather_a2a_agent.build_agent_card()
        finally:
            weather_a2a_agent.settings = original_settings

        self.assertEqual(
            card.supported_interfaces[0].url,
            "https://weather-specialist.example/a2a/jsonrpc",
        )

    def test_stock_health_exposes_runtime_urls(self):
        original_settings = stock_a2a_agent.settings
        stock_a2a_agent.settings = SimpleNamespace(
            a2a_url="https://stock-specialist.example",
            mcp_url="https://mcp-tools.example/mcp",
        )
        try:
            response = TestClient(stock_a2a_agent.create_app()).get("/health")
        finally:
            stock_a2a_agent.settings = original_settings

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "service": "stock-a2a",
                "a2a_url": "https://stock-specialist.example",
                "mcp_url": "https://mcp-tools.example/mcp",
            },
        )

    def test_weather_health_exposes_runtime_urls(self):
        original_settings = weather_a2a_agent.settings
        weather_a2a_agent.settings = SimpleNamespace(
            weather_a2a_url="https://weather-specialist.example",
            mcp_url="https://mcp-tools.example/mcp",
        )
        try:
            response = TestClient(weather_a2a_agent.create_app()).get("/health")
        finally:
            weather_a2a_agent.settings = original_settings

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "service": "weather-a2a",
                "weather_a2a_url": "https://weather-specialist.example",
                "mcp_url": "https://mcp-tools.example/mcp",
            },
        )


if __name__ == "__main__":
    unittest.main()
