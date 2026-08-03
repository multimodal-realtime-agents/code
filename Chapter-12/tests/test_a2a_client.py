import unittest

from a2a.helpers import new_data_part, new_message

from agent_system.a2a_client import _collect_specialist_result


class FakeA2AEvent:
    def __init__(self, message=None):
        self.message = message

    def HasField(self, name):
        return name == "message" and self.message is not None


async def _stream(*events):
    for event in events:
        yield event


class A2AClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_collects_structured_message_data(self):
        message = new_message(
            [
                new_data_part(
                    {
                        "kind": "stock_quote_result",
                        "provenance": {
                            "title": "NVDA quote",
                            "kind": "stock_quote",
                            "source": "stooq",
                            "status": "live",
                            "fields": {"symbol": "NVDA", "price": 214.86},
                        },
                    },
                    media_type="application/json",
                )
            ]
        )

        result = await _collect_specialist_result(_stream(FakeA2AEvent(message=message)))

        self.assertEqual(result["kind"], "stock_quote_result")
        self.assertEqual(result["provenance"]["fields"]["symbol"], "NVDA")


if __name__ == "__main__":
    unittest.main()
