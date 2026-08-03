import types
import unittest
from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset

import analyst_agent


class AnalystAgentTests(unittest.TestCase):
    def test_create_stock_connection_params_uses_stdio_server_parameters(self):
        server_path = Path("/tmp/chapter-11-stock-server.py")
        connection_params = analyst_agent.create_stock_connection_params(
            server_path=server_path,
            python_executable="/usr/bin/python3",
        )

        params = connection_params.server_params
        self.assertEqual(params.command, "/usr/bin/python3")
        self.assertEqual(params.args, [str(server_path)])
        self.assertEqual(connection_params.timeout, 10.0)

    def test_create_stock_toolset_returns_mcp_toolset(self):
        toolset = analyst_agent.create_stock_toolset(python_executable="/usr/bin/python3")

        self.assertIsInstance(toolset, McpToolset)

    def test_create_analyst_agent_contains_only_mcp_finance_toolset(self):
        toolset = analyst_agent.create_stock_toolset(python_executable="/usr/bin/python3")
        agent = analyst_agent.create_analyst_agent(model="gemini-3.5-flash", mcp_toolset=toolset)

        self.assertEqual(agent.name, "financial_analyst")
        self.assertEqual(agent.model, "gemini-3.5-flash")
        self.assertEqual(agent.tools, [toolset])
        self.assertIn("MCP-discovered tools", agent.instruction)
        self.assertIn("do not include raw base64 data", agent.instruction)
        self.assertIn("Do not provide investment advice", agent.instruction)

    def test_event_text_concatenates_text_parts(self):
        event = types.SimpleNamespace(
            content=types.SimpleNamespace(
                parts=[
                    types.SimpleNamespace(text="The "),
                    types.SimpleNamespace(text="price"),
                    types.SimpleNamespace(inline_data=b"ignored"),
                ]
            )
        )

        self.assertEqual(analyst_agent.event_text(event), "The price")

    def test_function_call_names_reads_adk_style_events(self):
        event = types.SimpleNamespace(
            get_function_calls=lambda: [
                types.SimpleNamespace(name="get_stock_price"),
                types.SimpleNamespace(name=None),
            ]
        )

        self.assertEqual(analyst_agent.function_call_names(event), ["get_stock_price"])

    def test_function_response_images_reads_mcp_image_payloads(self):
        event = {
            "content": {
                "parts": [
                    {
                        "functionResponse": {
                            "name": "get_stock_chart",
                            "response": {
                                "content": [
                                    {
                                        "type": "image",
                                        "mimeType": "image/png",
                                        "data": "abc123",
                                    }
                                ]
                            },
                        }
                    }
                ]
            }
        }

        self.assertEqual(
            analyst_agent.function_response_images(event),
            [{"mimeType": "image/png", "data": "abc123"}],
        )


if __name__ == "__main__":
    unittest.main()
