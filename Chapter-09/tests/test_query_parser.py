import unittest

from specialist_agents.query_generator.query_parser import parse_queries


class QueryParserTests(unittest.TestCase):
    def test_parse_numbered_queries(self):
        text = """
        1. agent2agent protocol specification
        2. A2A agent card examples
        3. A2A JSON-RPC task lifecycle
        """

        self.assertEqual(
            parse_queries(text),
            [
                "agent2agent protocol specification",
                "A2A agent card examples",
                "A2A JSON-RPC task lifecycle",
            ],
        )

    def test_parse_bulleted_queries_with_limit(self):
        text = """
        - first query
        - second query
        - third query
        - fourth query
        """

        self.assertEqual(parse_queries(text), ["first query", "second query", "third query"])


if __name__ == "__main__":
    unittest.main()
