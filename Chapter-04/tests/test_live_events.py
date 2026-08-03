import base64
import sys
import unittest
from pathlib import Path


PROXY_DIR = Path(__file__).resolve().parents[1] / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

from live_events import (  # noqa: E402
    function_response_to_browser_messages,
    server_message_to_browser_messages,
)


class LiveEventShapingTests(unittest.TestCase):
    def test_server_content_multiple_parts_are_forwarded(self):
        event = {
            "serverContent": {
                "modelTurn": {
                    "parts": [
                        {"text": "The price is "},
                        {
                            "inlineData": {
                                "data": base64.b64encode(b"audio").decode("ascii"),
                                "mimeType": "audio/pcm;rate=24000",
                            }
                        },
                        {"text": "available now."},
                    ]
                },
                "outputTranscription": {"text": "The price is available now."},
                "turnComplete": True,
            }
        }

        messages = server_message_to_browser_messages(event)

        self.assertEqual([m["text"] for m in messages if m["type"] == "text"], ["The price is ", "available now."])
        self.assertEqual(len([m for m in messages if m["type"] == "audio"]), 1)
        self.assertEqual([m for m in messages if m["type"] == "output_transcript"][0]["text"], "The price is available now.")
        self.assertEqual(messages[-1]["type"], "turn_complete")

    def test_tool_call_event_is_shaped(self):
        event = {
            "toolCall": {
                "functionCalls": [
                    {"id": "call-1", "name": "get_stock_price", "args": {"symbol": "NVDA"}}
                ]
            }
        }

        messages = server_message_to_browser_messages(event)

        self.assertEqual(messages, [{"type": "function_call", "function_call": event["toolCall"]["functionCalls"][0]}])

    def test_function_response_with_structured_result_emits_provenance(self):
        result = {
            "kind": "stock_quote_result",
            "provenance": {
                "title": "NVDA quote",
                "kind": "stock_quote",
                "source": "stooq",
                "as_of": "2026-05-27 16:00",
                "status": "live",
                "warning": None,
                "fields": {
                    "symbol": "NVDA",
                    "price": 214.86,
                    "currency": "USD",
                },
            },
        }

        messages = function_response_to_browser_messages("get_stock_price", result)
        provenance = [message for message in messages if message["type"] == "provenance"]

        self.assertEqual(messages[0]["type"], "function_response")
        self.assertEqual(len(provenance), 1)
        self.assertEqual(provenance[0]["title"], "NVDA quote")
        self.assertEqual(provenance[0]["fields"]["symbol"], "NVDA")

    def test_interruption_is_forwarded(self):
        messages = server_message_to_browser_messages({"serverContent": {"interrupted": True}})

        self.assertEqual(messages, [{"type": "interrupted"}])


if __name__ == "__main__":
    unittest.main()
