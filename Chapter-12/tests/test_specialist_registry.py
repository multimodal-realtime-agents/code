import unittest

from a2a.types import AgentCard, AgentSkill

from agent_system.specialist_registry import DiscoveredSpecialist, build_specialist_instruction


class SpecialistRegistryTests(unittest.TestCase):
    def test_build_specialist_instruction_includes_card_skills(self):
        card = AgentCard(
            name="Stock Specialist",
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
        instruction = build_specialist_instruction(
            {
                card.name: DiscoveredSpecialist(
                    name=card.name,
                    base_url="http://127.0.0.1:8020",
                    card=card,
                )
            }
        )

        self.assertIn("Stock Specialist", instruction)
        self.assertIn("natural-language", instruction)
        self.assertIn("stocks, quotes", instruction)


if __name__ == "__main__":
    unittest.main()
