import unittest
from unittest.mock import patch

from a2a.types import TaskState

from a2a_math_agent.server import MathAgentExecutor


class FakeContext:
    task_id = "task-1"
    context_id = "context-1"

    def get_user_input(self):
        return "What is 5 times 12?"


class FakeEventQueue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


class ExecutorStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_math_executor_reports_failed_task_status(self):
        async def failing_run(*args, **kwargs):
            raise RuntimeError("boom")

        queue = FakeEventQueue()
        with (
            patch("a2a_math_agent.server.run_agent_text", failing_run),
            patch("a2a_math_agent.server.logger.exception"),
        ):
            await MathAgentExecutor().execute(FakeContext(), queue)

        self.assertEqual(len(queue.events), 1)
        event = queue.events[0]
        self.assertEqual(event.status.state, TaskState.TASK_STATE_FAILED)
        self.assertIn("Math Agent failed: boom", event.status.message.parts[0].text)


if __name__ == "__main__":
    unittest.main()
