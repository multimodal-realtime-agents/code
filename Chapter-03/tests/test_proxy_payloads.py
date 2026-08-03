from __future__ import annotations

import asyncio
import base64
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "proxy"))

from proxy import forward_browser_payload  # noqa: E402


class FakeLiveSession:
    def __init__(self) -> None:
        self.client_content: list[tuple[Any, bool]] = []
        self.realtime_inputs: list[dict[str, Any]] = []

    async def send_client_content(self, *, turns: Any, turn_complete: bool) -> None:
        self.client_content.append((turns, turn_complete))

    async def send_realtime_input(self, **kwargs: Any) -> None:
        self.realtime_inputs.append(kwargs)


class ProxyPayloadTests(unittest.TestCase):
    def test_forwards_audio_payload_as_realtime_audio_blob(self) -> None:
        live_session = FakeLiveSession()
        payload = {
            "type": "audio",
            "mime_type": "audio/pcm;rate=16000",
            "data": base64.b64encode(b"abc").decode("ascii"),
        }

        should_close = asyncio.run(forward_browser_payload(payload, live_session))

        self.assertFalse(should_close)
        audio = live_session.realtime_inputs[0]["audio"]
        self.assertEqual(audio.data, b"abc")
        self.assertEqual(audio.mime_type, "audio/pcm;rate=16000")

    def test_forwards_text_payload_for_smoke_tests(self) -> None:
        live_session = FakeLiveSession()

        should_close = asyncio.run(
            forward_browser_payload({"type": "text", "text": "hello"}, live_session)
        )

        self.assertFalse(should_close)
        content, turn_complete = live_session.client_content[0]
        self.assertTrue(turn_complete)
        self.assertEqual(content.role, "user")
        self.assertEqual(content.parts[0].text, "hello")

    def test_forwards_activity_markers_and_close(self) -> None:
        live_session = FakeLiveSession()

        self.assertFalse(asyncio.run(forward_browser_payload({"type": "activity_start"}, live_session)))
        self.assertFalse(asyncio.run(forward_browser_payload({"type": "activity_end"}, live_session)))
        self.assertTrue(asyncio.run(forward_browser_payload({"type": "close"}, live_session)))
        self.assertIn("activity_start", live_session.realtime_inputs[0])
        self.assertIn("activity_end", live_session.realtime_inputs[1])


if __name__ == "__main__":
    unittest.main()
