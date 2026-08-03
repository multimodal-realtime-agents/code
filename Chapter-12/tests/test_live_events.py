import base64
import unittest

from agent_system.live_events import event_to_browser_messages


class LiveEventParserTests(unittest.TestCase):
    def test_multiple_parts_are_all_forwarded(self):
        event = {
            "content": {
                "role": "model",
                "parts": [
                    {"text": "The price is "},
                    {
                        "inlineData": {
                            "data": base64.b64encode(b"audio").decode("ascii"),
                            "mimeType": "audio/pcm;rate=24000",
                        }
                    },
                    {"text": "available now."},
                ],
            },
            "outputTranscription": {"text": "The price is available now."},
            "partial": False,
            "turnComplete": True,
        }

        messages = event_to_browser_messages(event)
        texts = [m["text"] for m in messages if m["type"] == "text"]
        audio = [m for m in messages if m["type"] == "audio"]
        transcripts = [m for m in messages if m["type"] == "output_transcript"]

        self.assertEqual(texts, ["The price is ", "available now."])
        self.assertEqual(len(audio), 1)
        self.assertEqual(transcripts[0]["text"], "The price is available now.")
        self.assertEqual(messages[-1]["type"], "turn_complete")

    def test_unrecognized_binary_event_is_not_forwarded(self):
        event = {
            "liveSessionResumptionUpdate": {
                "newHandle": b"\x00\x01",
                "resumable": True,
            }
        }

        self.assertEqual(event_to_browser_messages(event), [])

    def test_audio_bytes_are_base64_encoded(self):
        event = {
            "content": {
                "parts": [
                    {
                        "inlineData": {
                            "data": b"audio",
                            "mimeType": "audio/pcm;rate=24000",
                        }
                    }
                ]
            }
        }

        messages = event_to_browser_messages(event)

        self.assertEqual(messages[0]["type"], "audio")
        self.assertEqual(messages[0]["data"], base64.b64encode(b"audio").decode("ascii"))

    def test_function_response_with_structured_result_emits_provenance(self):
        event = {
            "content": {
                "parts": [
                    {
                        "functionResponse": {
                            "name": "delegate_task_to_specialist",
                            "response": {
                                "result": {
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
                            },
                        }
                    }
                ]
            }
        }

        messages = event_to_browser_messages(event)
        provenance = [m for m in messages if m["type"] == "provenance"]

        self.assertEqual(len(provenance), 1)
        self.assertEqual(provenance[0]["title"], "NVDA quote")
        self.assertEqual(provenance[0]["fields"]["symbol"], "NVDA")


if __name__ == "__main__":
    unittest.main()
