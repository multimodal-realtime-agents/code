import base64
import sys
import unittest
from pathlib import Path


PROXY_DIR = Path(__file__).resolve().parents[1] / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

from proxy import forward_browser_payload  # noqa: E402


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

    async def test_activity_and_close_payloads(self):
        session = FakeLiveSession()

        self.assertFalse(await forward_browser_payload({"type": "activity_start"}, session))
        self.assertFalse(await forward_browser_payload({"type": "activity_end"}, session))
        self.assertTrue(await forward_browser_payload({"type": "close"}, session))

        self.assertIn("activity_start", session.realtime_messages[0])
        self.assertIn("activity_end", session.realtime_messages[1])


if __name__ == "__main__":
    unittest.main()
