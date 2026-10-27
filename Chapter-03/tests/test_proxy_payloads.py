from __future__ import annotations

import asyncio
import base64
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "proxy"))

from proxy import create_live_config, forward_browser_payload  # noqa: E402


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

    def test_microphone_start_keeps_automatic_vad_in_control(self) -> None:
        live_session = FakeLiveSession()

        self.assertFalse(asyncio.run(forward_browser_payload({"type": "activity_start"}, live_session)))
        self.assertEqual(live_session.realtime_inputs, [])
        self.assertEqual(live_session.client_content, [])

    def test_microphone_end_flushes_audio_without_closing_session(self) -> None:
        live_session = FakeLiveSession()

        self.assertFalse(asyncio.run(forward_browser_payload({"type": "activity_end"}, live_session)))
        self.assertEqual(live_session.realtime_inputs, [{"audio_stream_end": True}])

    def test_audio_resumes_in_same_session_after_microphone_restart(self) -> None:
        live_session = FakeLiveSession()

        for frame in (b"first", b"second"):
            for payload in (
                {"type": "activity_start"},
                {"type": "audio", "data": base64.b64encode(frame).decode("ascii")},
                {"type": "activity_end"},
            ):
                self.assertFalse(asyncio.run(forward_browser_payload(payload, live_session)))

        self.assertEqual(
            [message.get("audio_stream_end") for message in live_session.realtime_inputs],
            [None, True, None, True],
        )
        self.assertEqual(
            [message["audio"].data for message in live_session.realtime_inputs if "audio" in message],
            [b"first", b"second"],
        )

    def test_close_requests_session_shutdown_without_sending_input(self) -> None:
        live_session = FakeLiveSession()

        self.assertTrue(asyncio.run(forward_browser_payload({"type": "close"}, live_session)))
        self.assertEqual(live_session.realtime_inputs, [])
        self.assertEqual(live_session.client_content, [])

    def test_live_config_keeps_automatic_vad_enabled(self) -> None:
        config = create_live_config().model_dump(exclude_none=True, by_alias=True, mode="json")
        detection = config.get("realtimeInputConfig", {}).get("automaticActivityDetection", {})

        self.assertFalse(detection.get("disabled", False))


if __name__ == "__main__":
    unittest.main()
