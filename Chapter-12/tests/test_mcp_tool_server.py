import asyncio
import unittest

from google.adk.tools.mcp_tool import McpToolset
from starlette.testclient import TestClient

import agent_system.finance_mcp_server as legacy_mcp_tool_server
import agent_system.mcp_tool_server as mcp_tool_server
from agent_system.mcp_tool_server import (
    _fallback_quote,
    get_weather,
    normalize_location,
    normalize_symbol,
)
from agent_system.stock_a2a_agent import (
    create_stock_info_agent,
    _quote_from_tool_response,
    _structured_stock_result,
)


class McpToolServerTests(unittest.TestCase):
    def test_legacy_finance_module_reexports_shared_mcp_server(self):
        self.assertIs(legacy_mcp_tool_server.mcp, mcp_tool_server.mcp)
        self.assertIs(legacy_mcp_tool_server.main, mcp_tool_server.main)

    def test_mcp_server_exposes_health_route(self):
        with TestClient(mcp_tool_server.mcp.streamable_http_app()) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
        self.assertEqual(response.json()["service"], "mcp-tool-server")
        self.assertTrue(response.json()["mcp_url"].endswith("/mcp"))

    def test_normalize_symbol(self):
        self.assertEqual(normalize_symbol(" nvda.us "), "NVDA")

    def test_unknown_symbol_fallback_is_explicitly_unavailable(self):
        quote = _fallback_quote("XYZ", "offline")

        self.assertEqual(quote["symbol"], "XYZ")
        self.assertIsNone(quote["price"])
        self.assertEqual(quote["source"], "offline-unavailable")
        self.assertIn("XYZ", quote["market_context"])
        self.assertIn("rather than copying another symbol", quote["market_context"])

    def test_normalize_weather_location(self):
        self.assertEqual(normalize_location("  London!!! "), "London")

    def test_weather_tool_returns_mock_data(self):
        weather = asyncio.run(get_weather("London"))

        self.assertEqual(weather["location"], "London")
        self.assertEqual(weather["source"], "mock-weather")
        self.assertEqual(weather["condition"], "light rain")

    def test_stock_agent_uses_mcp_toolset(self):
        agent = create_stock_info_agent()
        self.assertIsInstance(agent.tools[0], McpToolset)
        self.assertEqual(agent.tools[0].tool_filter, ["get_stock_price"])

    def test_stock_agent_accepts_natural_language_company_requests(self):
        agent = create_stock_info_agent()
        self.assertIn("What is Google's stock price today?", agent.instruction)
        self.assertIn("Google/Alphabet -> GOOG", agent.instruction)
        self.assertIn("MCP-discovered get_stock_price", agent.instruction)

    def test_structured_stock_result_contains_generic_provenance(self):
        result = _structured_stock_result(
            "NVDA",
            {
                "symbol": "NVDA",
                "price": 214.86,
                "currency": "USD",
                "as_of": "2026-05-27 16:00",
                "source": "stooq",
                "market_context": "NVDA is trading below its open.",
            },
        )

        self.assertEqual(result["kind"], "stock_quote_result")
        self.assertEqual(result["provenance"]["kind"], "stock_quote")
        self.assertEqual(result["provenance"]["status"], "live")
        self.assertEqual(result["provenance"]["fields"]["symbol"], "NVDA")

    def test_quote_extraction_reads_mcp_structured_content(self):
        quote = _quote_from_tool_response(
            {
                "structuredContent": {
                    "symbol": "NVDA",
                    "price": 214.86,
                    "currency": "USD",
                    "source": "stooq",
                    "as_of": "2026-05-27 16:00",
                }
            }
        )

        self.assertEqual(quote["symbol"], "NVDA")


if __name__ == "__main__":
    unittest.main()
