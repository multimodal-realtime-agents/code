import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROXY_DIR = Path(__file__).resolve().parents[1] / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

import tool_handler  # noqa: E402


class ToolHandlerTests(unittest.IsolatedAsyncioTestCase):
    def test_function_declarations_expose_chapter_12_tool_surface(self):
        declarations = {declaration["name"]: declaration for declaration in tool_handler.function_declarations()}

        self.assertIn("get_stock_price", declarations)
        self.assertIn("get_weather", declarations)
        self.assertEqual(declarations["get_stock_price"]["parameters"]["required"], ["symbol"])
        self.assertEqual(declarations["get_weather"]["parameters"]["required"], ["location"])

    async def test_stock_tool_returns_structured_fallback_provenance(self):
        async def failing_quote(symbol):
            raise RuntimeError("offline")

        with patch.object(tool_handler, "fetch_stooq_quote", failing_quote):
            result = await tool_handler.get_stock_price("nvda.us")

        self.assertEqual(result["kind"], "stock_quote_result")
        self.assertEqual(result["provenance"]["kind"], "stock_quote")
        self.assertEqual(result["provenance"]["fields"]["symbol"], "NVDA")
        self.assertEqual(result["provenance"]["status"], "fallback")
        self.assertIn("warning", result["answer_context"])

    async def test_weather_tool_returns_structured_mock_provenance(self):
        result = await tool_handler.get_weather("London")

        self.assertEqual(result["kind"], "weather_report_result")
        self.assertEqual(result["provenance"]["kind"], "weather_report")
        self.assertEqual(result["provenance"]["fields"]["location"], "London")
        self.assertEqual(result["provenance"]["status"], "mock")

    async def test_unknown_tool_is_structured_error(self):
        result = await tool_handler.execute_tool("unknown", {})

        self.assertEqual(result["kind"], "tool_error")
        self.assertEqual(result["status"], "error")

    async def test_swapped_tool_result_gets_generic_provenance(self):
        async def raw_tool(topic):
            return {"summary": f"demo result for {topic}", "source": "raw-tool"}

        tool = tool_handler.ToolSpec(
            name="raw_tool",
            description="A minimal swapped-in tool.",
            parameters={"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
            handler=raw_tool,
        )

        with patch.dict(tool_handler.TOOLS, {"raw_tool": tool}):
            result = await tool_handler.execute_tool("raw_tool", {"topic": "charts"})

        self.assertEqual(result["kind"], "tool_result")
        self.assertEqual(result["provenance"]["kind"], "tool_result")
        self.assertEqual(result["provenance"]["source"], "raw-tool")
        self.assertEqual(result["provenance"]["status"], "ok")
        self.assertEqual(result["provenance"]["fields"], {"summary": "demo result for charts"})


if __name__ == "__main__":
    unittest.main()
