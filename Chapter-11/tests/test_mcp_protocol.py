import asyncio
import sys
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parent.parent


class McpProtocolTests(unittest.TestCase):
    def test_stdio_server_advertises_and_calls_tools(self):
        async def run_check():
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(ROOT / "stock_server.py")],
            )
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    tool_names = {tool.name for tool in tools.tools}
                    self.assertIn("get_stock_price", tool_names)
                    self.assertIn("get_stock_chart", tool_names)

                    resources = await session.list_resource_templates()
                    templates = {
                        template.uriTemplate
                        for template in resources.resourceTemplates
                    }
                    self.assertIn("stock://{ticker}/info", templates)

                    quote = await session.call_tool(
                        "get_stock_price",
                        {"ticker": "AAPL"},
                    )
                    self.assertFalse(quote.isError)
                    self.assertEqual(quote.structuredContent["symbol"], "AAPL")
                    self.assertEqual(
                        quote.structuredContent["source"],
                        "deterministic-sample",
                    )

                    chart = await session.call_tool(
                        "get_stock_chart",
                        {"ticker": "AAPL"},
                    )
                    self.assertFalse(chart.isError)
                    self.assertEqual(chart.content[0].type, "image")
                    self.assertEqual(chart.content[0].mimeType, "image/png")

        asyncio.run(run_check())


if __name__ == "__main__":
    unittest.main()
