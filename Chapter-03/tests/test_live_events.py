from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "proxy"))

from live_events import server_message_to_browser_messages  # noqa: E402


class LiveEventShapingTests(unittest.TestCase):
    def test_shapes_transcripts_audio_and_turn_completion(self) -> None:
        messages = server_message_to_browser_messages(
            {
                "server_content": {
                    "input_transcription": {"text": "hello"},
                    "output_transcription": {"text": "hi there"},
                    "model_turn": {
                        "parts": [
                            {"inline_data": {"data": b"\x01\x02", "mime_type": "audio/pcm;rate=24000"}},
                            {"text": "caption"},
                        ]
                    },
                    "turn_complete": True,
                }
            }
        )

        self.assertIn({"type": "input_transcript", "text": "hello", "partial": True}, messages)
        self.assertIn({"type": "output_transcript", "text": "hi there", "partial": True}, messages)
        self.assertIn({"type": "text", "text": "caption", "partial": False}, messages)
        self.assertIn(
            {
                "type": "audio",
                "data": base64.b64encode(b"\x01\x02").decode("ascii"),
                "mime_type": "audio/pcm;rate=24000",
            },
            messages,
        )
        self.assertIn({"type": "turn_complete"}, messages)

    def test_shapes_camel_case_live_fields_and_interruption(self) -> None:
        messages = server_message_to_browser_messages(
            {
                "serverContent": {
                    "modelTurn": {"parts": [{"inlineData": {"data": "abcd"}}]},
                    "interrupted": True,
                    "turnComplete": True,
                },
                "goAway": {},
            }
        )

        self.assertIn({"type": "audio", "data": "abcd", "mime_type": "audio/pcm;rate=24000"}, messages)
        self.assertIn({"type": "interrupted"}, messages)
        self.assertIn({"type": "turn_complete"}, messages)
        self.assertIn({"type": "go_away"}, messages)


if __name__ == "__main__":
    unittest.main()
