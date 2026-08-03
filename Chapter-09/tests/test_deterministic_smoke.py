import unittest
from types import SimpleNamespace
from unittest.mock import patch

from chapter9_support import adk_runtime, config, gemini_text


class DeterministicSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_math_agent_path(self):
        with patch.object(adk_runtime, "settings", SimpleNamespace(deterministic_smoke=True)):
            result = await adk_runtime.run_agent_text(
                object(),
                "What is 5 times 12?",
                app_name="chapter_9_math_agent",
            )

        self.assertEqual(result, "60")

    def test_deterministic_query_generation(self):
        with patch.object(gemini_text, "settings", SimpleNamespace(deterministic_smoke=True)):
            result = gemini_text.generate_text(
                "Generate exactly three concise web search queries for this research topic.\n\n"
                "Topic: A2A protocol"
            )

        self.assertEqual(len(result.splitlines()), 3)
        self.assertIn("A2A protocol overview", result)

    def test_deterministic_smoke_satisfies_credential_gate(self):
        with patch.object(config, "settings", SimpleNamespace(deterministic_smoke=True)):
            self.assertTrue(config.has_google_credentials())


if __name__ == "__main__":
    unittest.main()
