import unittest
from types import SimpleNamespace

from a2a.helpers import new_text_artifact, new_text_message
from a2a.types import TaskState

from research_coordinator.a2a_tools import collect_text_response


class FakeA2AEvent:
    def __init__(self, message=None, task=None, artifact_update=None, status_update=None):
        self.message = message
        self.task = task
        self.artifact_update = artifact_update
        self.status_update = status_update

    def HasField(self, name):
        return (
            (name == "message" and self.message is not None)
            or (name == "task" and self.task is not None)
            or (name == "artifact_update" and self.artifact_update is not None)
            or (name == "status_update" and self.status_update is not None)
        )


async def _stream(*events):
    for event in events:
        yield event


class A2AClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_collects_text_messages(self):
        message = new_text_message("hello from A2A")
        response = await collect_text_response(
            _stream(FakeA2AEvent(message=message)),
            "https://agent.example",
        )

        self.assertEqual(response, "hello from A2A")

    async def test_collects_text_artifact_updates(self):
        artifact_update = SimpleNamespace(artifact=new_text_artifact("result", "hello from artifact"))
        response = await collect_text_response(
            _stream(FakeA2AEvent(artifact_update=artifact_update)),
            "https://agent.example",
        )

        self.assertEqual(response, "hello from artifact")

    async def test_collects_text_from_task_artifacts(self):
        task = SimpleNamespace(artifacts=[new_text_artifact("result", "hello from task")])
        response = await collect_text_response(
            _stream(FakeA2AEvent(task=task)),
            "https://agent.example",
        )

        self.assertEqual(response, "hello from task")

    async def test_failed_status_raises(self):
        status_update = SimpleNamespace(
            status=SimpleNamespace(state=TaskState.TASK_STATE_FAILED)
        )

        with self.assertRaisesRegex(RuntimeError, "TASK_STATE_FAILED"):
            await collect_text_response(
                _stream(FakeA2AEvent(status_update=status_update)),
                "https://agent.example",
            )

    async def test_no_text_raises(self):
        with self.assertRaisesRegex(RuntimeError, "returned no text"):
            await collect_text_response(_stream(), "https://agent.example")


if __name__ == "__main__":
    unittest.main()
