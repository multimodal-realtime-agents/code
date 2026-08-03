import base64
from types import SimpleNamespace
import unittest

import agent_system.backend as backend
from agent_system.backend import _forward_browser_payload


class FakeLiveRequestQueue:
    def __init__(self):
        self.realtime = []
        self.content = []
        self.activity = []

    def send_realtime(self, blob):
        self.realtime.append(blob)

    def send_content(self, content):
        self.content.append(content)

    def send_activity_start(self):
        self.activity.append("start")

    def send_activity_end(self):
        self.activity.append("end")


class BackendPayloadTests(unittest.TestCase):
    def test_image_payload_is_forwarded_as_realtime_blob(self):
        queue = FakeLiveRequestQueue()
        data = base64.b64encode(b"jpeg-frame").decode("ascii")

        should_close = _forward_browser_payload(
            {"type": "image", "data": data, "mime_type": "image/jpeg"},
            queue,
        )

        self.assertFalse(should_close)
        self.assertEqual(len(queue.realtime), 1)
        self.assertEqual(queue.realtime[0].data, b"jpeg-frame")
        self.assertEqual(queue.realtime[0].mime_type, "image/jpeg")

    def test_image_payload_accepts_data_url(self):
        queue = FakeLiveRequestQueue()
        data = base64.b64encode(b"png-frame").decode("ascii")

        _forward_browser_payload(
            {"type": "image", "data": f"data:image/png;base64,{data}", "mime_type": "image/png"},
            queue,
        )

        self.assertEqual(queue.realtime[0].data, b"png-frame")
        self.assertEqual(queue.realtime[0].mime_type, "image/png")

    def test_close_payload_returns_true(self):
        queue = FakeLiveRequestQueue()

        self.assertTrue(_forward_browser_payload({"type": "close"}, queue))


class BackendServiceBoundaryTests(unittest.TestCase):
    def test_backend_no_longer_serves_static_ui(self):
        self.assertNotIn("/", {route.path for route in backend.app.routes})
        self.assertIn("/health", {route.path for route in backend.app.routes})
        self.assertIn("/live", {route.path for route in backend.app.routes})

    def test_origin_validation_allows_configured_frontend_origin(self):
        original_settings = backend.settings
        backend.settings = SimpleNamespace(allowed_origins=("http://127.0.0.1:8080",))
        try:
            self.assertTrue(backend._origin_allowed("http://127.0.0.1:8080"))
            self.assertFalse(backend._origin_allowed("http://evil.example"))
            self.assertTrue(backend._origin_allowed(None))
        finally:
            backend.settings = original_settings


if __name__ == "__main__":
    unittest.main()
