import unittest

from a2a.types import AgentCard, AgentSkill

import agent_system.host_agent as host_agent
from agent_system.host_agent import SpecialistDirectory
from agent_system.specialist_registry import DiscoveredSpecialist


def _specialist(name="Stock Specialist"):
    card = AgentCard(
        name=name,
        description="Turns natural-language stock price requests into MCP-backed quote lookups.",
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="stock_quote",
                name="Stock quote",
                description="Accepts natural-language company or ticker requests.",
                tags=["stocks", "quotes"],
            )
        ],
    )
    return DiscoveredSpecialist(
        name=card.name,
        base_url="http://127.0.0.1:8020",
        card=card,
    )


class HostAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_delegate_tool_lazily_rediscovers_missing_specialist(self):
        specialist = _specialist()
        discover_calls = 0
        delegated = {}

        async def discover():
            nonlocal discover_calls
            discover_calls += 1
            return {specialist.name: specialist}

        async def ask_specialist(request, base_url):
            delegated["request"] = request
            delegated["base_url"] = base_url
            return {
                "kind": "stock_quote_result",
                "provenance": {
                    "title": "NVDA quote",
                    "kind": "stock_quote",
                    "source": "offline-unavailable",
                    "as_of": "unavailable",
                    "status": "unavailable",
                    "warning": "offline",
                    "fields": {"symbol": "NVDA", "price": None, "currency": "USD"},
                },
            }

        directory = SpecialistDirectory({}, discover=discover)
        delegate_tool = host_agent._make_delegate_tool(directory)
        original_ask_specialist = host_agent.ask_specialist
        host_agent.ask_specialist = ask_specialist
        try:
            answer = await delegate_tool("Stock Specialist", "NVDA")
        finally:
            host_agent.ask_specialist = original_ask_specialist

        self.assertEqual(answer["provenance"]["fields"]["symbol"], "NVDA")
        self.assertEqual(discover_calls, 1)
        self.assertEqual(delegated["request"], "NVDA")
        self.assertEqual(delegated["base_url"], "http://127.0.0.1:8020")


if __name__ == "__main__":
    unittest.main()
