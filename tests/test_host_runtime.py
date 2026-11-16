"""Strict CLI result parsing and consent tests: synthetic transcripts never count as live UAT."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tools import host_runtime as hr


class HostRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name).resolve()

    def test_no_model_call_without_explicit_consent(self):
        with patch.object(hr.subprocess, "Popen") as start:
            preview = hr.run("claude", "qa", "inspect secret TEST_KEY", self.cwd)
        self.assertEqual(preview["status"], "READY_FOR_EXPLICIT_AUTHORIZATION")
        self.assertNotIn("TEST_KEY", json.dumps(preview))
        self.assertNotIn("TEST_KEY", " ".join(preview["argv_preview"]))
        self.assertNotIn("TEST_KEY", str(preview))
        start.assert_not_called()

    def test_host_tools_require_separate_permission_approval(self):
        for host in ("workbuddy", "hermes"):
            with self.subTest(host=host):
                with patch.object(hr.subprocess, "Popen") as start:
                    result = hr.run(host, "studio", "Read a README", self.cwd,
                                    consent=True)
                self.assertEqual(result["status"], "HOST_PERMISSION_REVIEW_REQUIRED")
                start.assert_not_called()
        permitted = hr.build("workbuddy", "qa", "Review", self.cwd,
                             allow_risky_host=True)
        self.assertIn("-y", permitted["command"])
        self.assertIn("--disallowedTools", permitted["command"])

    def test_disabled_host_absent_is_not_run(self):
        with patch.object(hr.shutil, "which", return_value=None):
            status = hr.run("claude", "qa", "Inspect", self.cwd, consent=True)
        self.assertEqual(status["status"], "NOT_RUN")
        self.assertEqual(status["reason"], "HOST_CLI_NOT_FOUND")

    def test_claude_result_must_have_structured_session(self):
        text = json.dumps({"type": "result", "session_id": "sess-cl-002",
                           "is_error": False, "result": "read-only findings"})
        self.assertEqual(hr._structured(text, "claude", 0)["status"], "COMPLETED")
        self.assertEqual(hr._structured(text.replace("sess-cl-002", ""), "claude", 0)["status"],
                         "INCONCLUSIVE")
        self.assertEqual(hr._structured("I completed this task", "claude", 0)["status"],
                         "INCONCLUSIVE")

    def test_workbuddy_real_schema_parser(self):
        text = json.dumps({"type": "result", "session_id": "session123456",
                           "result": "Findings with references", "is_error": False})
        parsed = hr._structured(text, "workbuddy", 0)
        self.assertEqual(parsed["session_id"], "session123456")
        self.assertEqual(parsed["status"], "COMPLETED")

    def test_gemini_stream_parser(self):
        events = [
            {"type": "init", "session_id": "gemini-session-999"},
            {"type": "message", "role": "assistant", "content": "UX review"},
            {"type": "result", "status": "success"},
        ]
        output = "\n".join(json.dumps(x) for x in events)
        self.assertEqual(hr._structured(output, "gemini", 0)["status"], "COMPLETED")
        self.assertEqual(hr._structured(output.replace("gemini-session-999", ""), "gemini", 0)["status"],
                         "INCONCLUSIVE")

    def test_opencode_trace_requires_final_and_session(self):
        transcript = [
            {"type": "text", "part": {"text": "review findings"}},
            {"type": "step_finish", "part": {"sessionID": "ses_09a56b", "reason": "stop"}},
        ]
        text = "\n".join(json.dumps(x) for x in transcript)
        self.assertEqual(hr._structured(text, "opencode", 0)["status"], "COMPLETED")
        self.assertEqual(hr._structured(text.splitlines()[0], "opencode", 0)["status"],
                         "INCONCLUSIVE")

    def test_hermes_verified_one_shot_result(self):
        events = [
            {"type": "system", "subtype": "init", "session_id": "hermes-100"},
            {"type": "result", "session_id": "hermes-100", "text": "read-only",
             "exit_code": 0},
        ]
        self.assertEqual(hr._structured("\n".join(json.dumps(x) for x in events),
                                        "hermes", 0)["status"], "COMPLETED")
        events[-1]["exit_code"] = 1
        self.assertNotEqual(hr._structured("\n".join(json.dumps(x) for x in events),
                                            "hermes", 1)["status"], "COMPLETED")

    def test_mock_subprocess_live_result_is_local_unit_evidence_only(self):
        process = MagicMock()
        process.communicate.return_value = (json.dumps({
            "type": "result", "session_id": "session1234",
            "result": "result", "is_error": False,
        }), "")
        process.returncode = 0
        with patch.object(hr.shutil, "which", return_value="/bin/claude"), \
             patch.object(hr.subprocess, "Popen", return_value=process) as launch:
            data = hr.run("claude", "qa", "Read this repository", self.cwd,
                          consent=True)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["native_subagent"], "NOT_VERIFIED")
        self.assertEqual(data["sandbox"], "HOST_POLICY_ONLY")
        self.assertFalse(launch.call_args.kwargs.get("shell", False))
        self.assertIn("--permission-mode", launch.call_args.args[0])
        self.assertNotIn("Read this repository", " ".join(launch.call_args.args[0]))
        self.assertIn("Read this repository", process.communicate.call_args.kwargs["input"])

    def test_invalid_timeout_and_unsafe_workspace(self):
        with self.assertRaises(ValueError):
            hr.run("claude", "qa", "hi", self.cwd, timeout=5)
        with self.assertRaises(ValueError):
            hr.build("not-a-host", "qa", "hi", self.cwd)
        with self.assertRaises(ValueError):
            hr.build("claude", "qa", "hi", self.cwd / "does-not-exist")


if __name__ == "__main__":
    unittest.main()
