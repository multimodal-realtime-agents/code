import unittest

from google.protobuf.json_format import MessageToDict

from a2a_handshake.langgraph_greeter.server import build_agent_card as greeter_card
from a2a_math_agent.server import build_agent_card as math_card
from specialist_agents.query_generator.server import build_agent_card as query_card
from specialist_agents.researcher.server import build_agent_card as researcher_card


class AgentCardTests(unittest.TestCase):
    def test_cards_advertise_jsonrpc_interface(self):
        cases = [
            (greeter_card("https://greeter.example"), "https://greeter.example/a2a/jsonrpc"),
            (math_card("https://math.example"), "https://math.example/a2a/jsonrpc"),
            (query_card("https://query.example"), "https://query.example/a2a/jsonrpc"),
            (researcher_card("https://research.example"), "https://research.example/a2a/jsonrpc"),
        ]

        for card, expected_url in cases:
            with self.subTest(card=card.name):
                self.assertEqual(card.supported_interfaces[0].protocol_binding, "JSONRPC")
                self.assertEqual(card.supported_interfaces[0].url, expected_url)
                self.assertTrue(card.skills)

    def test_serialized_cards_use_wire_field_names(self):
        card_json = MessageToDict(greeter_card("https://greeter.example"))

        self.assertIn("supportedInterfaces", card_json)
        self.assertNotIn("supported_interfaces", card_json)

    def test_math_card_advertises_arithmetic_tools(self):
        skill_ids = {skill.id for skill in math_card("https://math.example").skills}

        self.assertEqual(skill_ids, {"add", "subtract", "multiply", "divide"})


if __name__ == "__main__":
    unittest.main()
