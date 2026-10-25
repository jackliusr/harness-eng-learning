import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from loop_cli.fakes import FakeClient, fake_text_response, fake_tool_response
from loop_cli.agent import new_conversation, run_agent
from loop_cli.permissions import reset_session_approvals
from loop_cli.runtime import Runtime, set_runtime


class AgentFakeClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        reset_session_approvals()

    def tearDown(self):
        self.tmp.cleanup()

    def configure_fake(self, responses, permission_mode: str = "auto"):
        client = FakeClient(responses)
        set_runtime(
            Runtime(
                client=client,
                model="fake-model",
                workspace=self.workspace,
                memory_file=self.workspace / "memory.json",
                permission_mode=permission_mode,
            )
        )
        return client

    def run_with_output(self, messages):
        output = io.StringIO()
        with redirect_stdout(output):
            status = run_agent(messages)
        return status, output.getvalue()

    def test_tool_call_round_trip(self):
        client = self.configure_fake(
            [
                fake_tool_response(
                    "write_file",
                    {"path": "hello.txt", "content": "hello"},
                ),
                fake_text_response("Wrote the file."),
            ]
        )
        messages = new_conversation()
        messages.append({"role": "user", "content": "Write hello.txt."})

        status, output = self.run_with_output(messages)

        self.assertEqual(status, 0)
        self.assertEqual((self.workspace / "hello.txt").read_text(), "hello")
        self.assertIn("[tool_use] write_file", output)
        self.assertEqual(len(client.chat.completions.requests), 2)

        second_request = client.chat.completions.requests[1]
        self.assertEqual(second_request["messages"][-1]["role"], "tool")
        self.assertIn("Wrote 5 bytes", second_request["messages"][-1]["content"])

    def test_permission_denial_returns_tool_result(self):
        client = self.configure_fake(
            [
                fake_tool_response(
                    "write_file",
                    {"path": "src/app.py", "content": "print('no')"},
                ),
                fake_text_response("I will not write it."),
            ],
            permission_mode="ask",
        )
        messages = new_conversation()
        messages.append({"role": "user", "content": "Write src/app.py."})

        with patch("builtins.input", side_effect=["n", "not now"]):
            status, output = self.run_with_output(messages)

        self.assertEqual(status, 0)
        self.assertFalse((self.workspace / "src" / "app.py").exists())
        self.assertIn('"error_type": "permission"', output)


if __name__ == "__main__":
    unittest.main()