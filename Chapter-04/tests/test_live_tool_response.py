import asyncio
import contextlib
import json
import sys
import unittest
from pathlib import Path


PROXY_DIR = Path(__file__).resolve().parents[1] / "backend" / "proxy"
sys.path.insert(0, str(PROXY_DIR))

from proxy import forward_live_to_browser  # noqa: E402


class FakeFunctionCall:
    id = "call-1"
    name = "get_weather"
    args = {"location": "London"}


class FakeToolCall:
    function_calls = [FakeFunctionCall()]


class FakeLiveResponse:
    tool_call = FakeToolCall()

    def model_dump(self, **_kwargs):
        return {
            "toolCall": {
                "functionCalls": [
                    {"id": "call-1", "name": "get_weather", "args": {"location": "London"}}
                ]
            }
        }


class FakeLiveSession:
    def __init__(self):
        self.function_responses = None
        self.receive_calls = 0
        self.block = asyncio.Event()

    async def receive(self):
        self.receive_calls += 1
        if self.receive_calls == 1:
            yield FakeLiveResponse()
            return
        await self.block.wait()
        if False:
            yield None

    async def send_tool_response(self, *, function_responses):
        self.function_responses = function_responses


class FakeBrowserWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, payload):
        self.messages.append(json.loads(payload))


class FakeContentResponse:
    def __init__(self, text):
        self.text = text

    def model_dump(self, **_kwargs):
        return {
            "serverContent": {
                "modelTurn": {"parts": [{"text": self.text}]},
                "turnComplete": True,
            }
        }


class FakeMultiTurnLiveSession:
    def __init__(self):
        self.receive_calls = 0
        self.block = asyncio.Event()

    async def receive(self):
        self.receive_calls += 1
        if self.receive_calls == 1:
            yield FakeContentResponse("first turn")
            return
        if self.receive_calls == 2:
            yield FakeContentResponse("second turn")
            return
        await self.block.wait()
        if False:
            yield None


class LiveToolResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_call_executes_and_returns_sdk_function_response(self):
        browser_ws = FakeBrowserWebSocket()
        live_session = FakeLiveSession()

        task = asyncio.create_task(forward_live_to_browser(browser_ws, live_session))
        await wait_for(lambda: live_session.function_responses is not None)

        browser_types = [message["type"] for message in browser_ws.messages]
        self.assertEqual(browser_types, ["function_call", "function_response", "provenance"])
        self.assertEqual(browser_ws.messages[2]["source"], "mock-weather")

        responses = live_session.function_responses
        self.assertIsNotNone(responses)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].id, "call-1")
        self.assertEqual(responses[0].name, "get_weather")
        self.assertEqual(responses[0].response["result"]["provenance"]["kind"], "weather_report")
        self.assertFalse(task.done())
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_live_receive_loop_stays_open_across_turns(self):
        browser_ws = FakeBrowserWebSocket()
        live_session = FakeMultiTurnLiveSession()

        task = asyncio.create_task(forward_live_to_browser(browser_ws, live_session))
        await wait_for(lambda: len([m for m in browser_ws.messages if m["type"] == "turn_complete"]) == 2)

        texts = [message["text"] for message in browser_ws.messages if message["type"] == "text"]
        self.assertEqual(texts, ["first turn", "second turn"])
        self.assertGreaterEqual(live_session.receive_calls, 3)
        self.assertFalse(task.done())
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def wait_for(predicate, timeout=1.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached before timeout")


if __name__ == "__main__":
    unittest.main()
