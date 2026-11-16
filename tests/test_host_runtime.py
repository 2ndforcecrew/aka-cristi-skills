"""Synthetic protocol and safe host CLI tests, never model inference."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import host_runtime as rt


class HostRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.project = Path(self.dir.name).resolve()

    def test_default_never_invokes_model_even_if_binary_exists(self):
        with patch.object(rt.shutil, "which", return_value="/bin/mock"), \
             patch.object(rt, "_launch") as launch:
            out = rt.run("claude", "qa", "Inspect", self.project)
        self.assertEqual(out["status"], "NOT_RUN")
        self.assertEqual(out["reason"], "INFERENCE_CONSENT_REQUIRED")
        launch.assert_not_called()

    def test_missing_binary_and_unverified_hosts_block_model(self):
        with patch.object(rt.shutil, "which", return_value=None), \
             patch.object(rt, "_launch") as launch:
            self.assertEqual(rt.run("gemini", "qa", "x", self.project,
                                    authorized=True)["reason"], "HOST_CLI_MISSING")
            for host in ("workbuddy", "hermes", "chatgpt", "generic"):
                self.assertEqual(rt.run(host, "factory", "x", self.project,
                                        authorized=True)["status"], "NOT_RUN")
            launch.assert_not_called()

    def test_only_allowlisted_read_only_cli_options(self):
        claude = rt.command("claude", "prompt")
        self.assertIn("plan", claude)
        self.assertNotIn("--dangerously-skip-permissions", claude)
        gemini = rt.command("gemini", "prompt")
        self.assertEqual(gemini[gemini.index("--approval-mode") + 1], "plan")
        self.assertNotIn("--yolo", gemini)
        opencode = rt.command("opencode", "prompt")
        self.assertEqual(opencode[opencode.index("--agent") + 1], "plan")
        self.assertNotIn("--auto", opencode)
        with self.assertRaises(ValueError):
            rt.command("hermes", "x")

    def test_strict_claude_session_and_completion(self):
        raw = json.dumps({"type": "result", "subtype": "success",
                          "is_error": False, "result": "Observed real reply",
                          "session_id": "sess-12345678"}).encode()
        out = rt.parse("claude", raw, 0)
        self.assertEqual(out["status"], "COMPLETED")
        self.assertEqual(out["thread_ids"], ["sess-12345678"])
        self.assertEqual(out["native_child_agents"], "NOT_VERIFIED")
        forged = rt.parse("claude", json.dumps({"type": "result",
            "subtype": "success", "is_error": False,
            "result": "I spawned four agents"}).encode(), 0)
        self.assertEqual(forged["status"], "INCONCLUSIVE")
        self.assertEqual(forged["thread_ids"], [])

    def test_gemini_requires_init_final_and_nonempty_reply(self):
        good = (json.dumps({"type": "init", "session_id": "gem-123456789"}) + "\n"
                + json.dumps({"type": "result", "status": "success",
                              "response": "Test evidence"})).encode()
        self.assertEqual(rt.parse("gemini", good, 0)["status"], "COMPLETED")
        no_id = json.dumps({"response": "Just prose"}).encode()
        self.assertEqual(rt.parse("gemini", no_id, 0)["status"], "INCONCLUSIVE")
        with_error = good + b'\n{"type":"error","error":"denied"}'
        self.assertNotEqual(rt.parse("gemini", with_error, 0)["status"], "COMPLETED")

    def test_opencode_requires_correlated_step_finish(self):
        lines = [
            {"type": "text", "sessionID": "ses_abcdefgh",
             "part": {"text": "Report"}},
            {"type": "step_finish", "sessionID": "ses_abcdefgh",
             "part": {"reason": "stop"}},
        ]
        data = ("\n".join(json.dumps(x) for x in lines)).encode()
        self.assertEqual(rt.parse("opencode", data, 0)["status"], "COMPLETED")
        self.assertNotEqual(rt.parse("opencode", data.replace(b"ses_abcdefgh",
                                      b"short"), 0)["status"], "COMPLETED")
        self.assertNotEqual(rt.parse("opencode", data, 1)["status"], "COMPLETED")

    def test_authorized_run_uses_real_interface_and_reports_not_spawn(self):
        raw = json.dumps({"type": "result", "subtype": "success",
                          "is_error": False, "result": "Answer",
                          "session_id": "session-123456789"}).encode()
        with patch.object(rt.shutil, "which", return_value="/bin/claude"), \
             patch.object(rt, "_launch", return_value={
                 "status": "EXITED", "code": 0, "stdout": raw, "stderr": b""
             }) as launch:
            result = rt.run("claude", "studio", "Review homepage",
                            self.project, timeout=30, authorized=True)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["native_child_agents"], "NOT_VERIFIED")
        self.assertEqual(result["scope"], "read_only_plan")
        self.assertEqual(launch.call_args[0][2], 30)

    def test_timeout_does_not_claim_completion(self):
        with patch.object(rt.shutil, "which", return_value="/bin/mock"), \
             patch.object(rt, "_launch", return_value={"status": "TIMEOUT"}):
            result = rt.run("gemini", "qa", "Review", self.project, authorized=True)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["reason"], "TIMEOUT")

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            rt.run("claude", "boss", "x", self.project, authorized=True)
        with self.assertRaises(ValueError):
            rt.run("claude", "qa", "", self.project, authorized=True)
        with self.assertRaises(ValueError):
            rt.run("claude", "qa", "x", self.project, timeout=99999,
                   authorized=True)
        with self.assertRaises(ValueError):
            rt.run("claude", "qa", "x", self.project / "missing",
                   authorized=True)

    def test_oversized_log_is_never_a_pass(self):
        self.assertEqual(rt.parse("claude", b"x" * (rt.MAX_LOG + 1), 0)["status"],
                         "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
