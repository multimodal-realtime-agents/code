import base64
import sys
import unittest
from pathlib import Path


PROXY_DIR = Path(__file__).resolve().parents[1] / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

from proxy import create_live_config, forward_browser_payload  # noqa: E402


class FakeLiveSession:
    def __init__(self):
        self.content_messages = []
        self.realtime_messages = []

    async def send_client_content(self, *, turns, turn_complete=True):
        self.content_messages.append((turns, turn_complete))

    async def send_realtime_input(self, **kwargs):
        self.realtime_messages.append(kwargs)


class BrowserPayloadForwardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_payload_forwards_content_turn(self):
        session = FakeLiveSession()

        should_close = await forward_browser_payload({"type": "text", "text": "Hello"}, session)

        self.assertFalse(should_close)
        content, turn_complete = session.content_messages[0]
        self.assertTrue(turn_complete)
        self.assertEqual(content.parts[0].text, "Hello")

    async def test_audio_payload_forwards_realtime_audio_blob(self):
        session = FakeLiveSession()
        payload = {
            "type": "audio",
            "mime_type": "audio/pcm;rate=16000",
            "data": base64.b64encode(b"pcm").decode("ascii"),
        }

        await forward_browser_payload(payload, session)

        blob = session.realtime_messages[0]["audio"]
        self.assertEqual(blob.data, b"pcm")
        self.assertEqual(blob.mime_type, "audio/pcm;rate=16000")

    async def test_image_payload_accepts_data_url(self):
        session = FakeLiveSession()
        payload = {
            "type": "image",
            "mime_type": "image/jpeg",
            "data": "data:image/jpeg;base64," + base64.b64encode(b"jpeg").decode("ascii"),
        }

        await forward_browser_payload(payload, session)

        self.assertNotIn("media", session.realtime_messages[0])
        blob = session.realtime_messages[0]["video"]
        self.assertEqual(blob.data, b"jpeg")
        self.assertEqual(blob.mime_type, "image/jpeg")

    async def test_microphone_start_keeps_automatic_vad_in_control(self):
        session = FakeLiveSession()

        self.assertFalse(await forward_browser_payload({"type": "activity_start"}, session))
        self.assertEqual(session.realtime_messages, [])
        self.assertEqual(session.content_messages, [])

    async def test_microphone_end_flushes_audio_without_closing_session(self):
        session = FakeLiveSession()

        self.assertFalse(await forward_browser_payload({"type": "activity_end"}, session))
        self.assertEqual(session.realtime_messages, [{"audio_stream_end": True}])

    async def test_audio_resumes_in_same_session_after_microphone_restart(self):
        session = FakeLiveSession()

        for frame in (b"first", b"second"):
            for payload in (
                {"type": "activity_start"},
                {"type": "audio", "data": base64.b64encode(frame).decode("ascii")},
                {"type": "activity_end"},
            ):
                self.assertFalse(await forward_browser_payload(payload, session))

        self.assertEqual(
            [message.get("audio_stream_end") for message in session.realtime_messages],
            [None, True, None, True],
        )
        self.assertEqual(
            [message["audio"].data for message in session.realtime_messages if "audio" in message],
            [b"first", b"second"],
        )

    async def test_close_requests_session_shutdown_without_sending_input(self):
        session = FakeLiveSession()

        self.assertTrue(await forward_browser_payload({"type": "close"}, session))
        self.assertEqual(session.realtime_messages, [])
        self.assertEqual(session.content_messages, [])

    def test_live_config_keeps_automatic_vad_enabled(self):
        config = create_live_config().model_dump(exclude_none=True, by_alias=True, mode="json")
        detection = config.get("realtimeInputConfig", {}).get("automaticActivityDetection", {})

        self.assertFalse(detection.get("disabled", False))


if __name__ == "__main__":
    unittest.main()
