import unittest

from google.adk.tools.mcp_tool import McpToolset

from agent_system.weather_a2a_agent import (
    _structured_weather_result,
    _weather_from_tool_response,
    create_weather_info_agent,
)


class WeatherToolTests(unittest.TestCase):
    def test_weather_agent_uses_mcp_toolset(self):
        agent = create_weather_info_agent()

        self.assertIsInstance(agent.tools[0], McpToolset)
        self.assertEqual(agent.tools[0].tool_filter, ["get_weather"])

    def test_weather_agent_declares_mock_data(self):
        agent = create_weather_info_agent()

        self.assertIn("What is the weather in London?", agent.instruction)
        self.assertIn("MCP-discovered get_weather", agent.instruction)
        self.assertIn("deterministic mock weather data", agent.instruction)

    def test_structured_weather_result_contains_generic_provenance(self):
        result = _structured_weather_result(
            "What is the weather in London?",
            {
                "location": "London",
                "condition": "light rain",
                "temperature_c": 12,
                "temperature_f": 54,
                "humidity_percent": 78,
                "wind_kph": 16,
                "as_of": "sample",
                "source": "mock-weather",
                "weather_context": "Mock context.",
            },
        )

        self.assertEqual(result["kind"], "weather_report_result")
        self.assertEqual(result["provenance"]["kind"], "weather_report")
        self.assertEqual(result["provenance"]["status"], "mock")
        self.assertEqual(result["provenance"]["fields"]["location"], "London")

    def test_weather_extraction_reads_mcp_structured_content(self):
        weather = _weather_from_tool_response(
            {
                "structuredContent": {
                    "location": "London",
                    "condition": "light rain",
                    "temperature_c": 12,
                    "source": "mock-weather",
                    "as_of": "sample",
                }
            }
        )

        self.assertEqual(weather["location"], "London")


if __name__ == "__main__":
    unittest.main()
