"""Contract tests for read-only CLI dispatch. Fake results NEVER count as live acceptance."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import chef_runtime_dispatch as rt


class HostRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name).resolve() / "project"
        self.project.mkdir()

    def test_preview_default_never_contacts_host(self):
        with patch.object(rt, "_spawn") as spawn, patch.object(rt.shutil, "which") as which:
            report = rt.run("codebuddy", "hybrid", "Describe a safe fix",
                            self.project)
            self.assertEqual(report["status"], "NOT_RUN")
            self.assertEqual(report["sequence"], ["factory", "studio", "qa"])
            spawn.assert_not_called()
            which.assert_not_called()

    def test_read_only_commands_have_no_permission_bypass(self):
        for host in ("codebuddy", "claude"):
            command = rt.command(host, "review me")
            self.assertNotIn("--dangerously-skip-permissions", command)
            self.assertNotIn("-y", command)
            self.assertIn("--tools", command)
            self.assertEqual(command[command.index("--tools") + 1], "")
            self.assertNotIn("Bash", command)
            self.assertNotIn("--auto", command)
            self.assertEqual(command[-1], "review me")

    def test_missing_cli_no_call(self):
        with patch.object(rt.shutil, "which", return_value=None), \
             patch.object(rt, "_spawn") as spawn:
            report = rt.run("codebuddy", "hybrid", "review",
                            self.project, allow_quota=True)
            self.assertEqual(report["reason"], "HOST_CLI_NOT_INSTALLED")
            spawn.assert_not_called()

    def test_independent_real_cli_process_evidence_contract_not_native_subagent(self):
        fake = [
            {"session_id": "session-factory01", "result": "Implementation sketch"},
            {"session_id": "session-studio02", "result": "UX review"},
            {"session_id": "session-qa-0003", "result": "Independent assessment"},
        ]
        responses = [{"exit_code": 0, "stdout": json.dumps(f), "error": None}
                     for f in fake]
        with patch.object(rt.shutil, "which", return_value="/mock/cli"), \
             patch.object(rt, "_spawn", side_effect=responses) as spawn:
            report = rt.run("codebuddy", "hybrid", "Assess my project",
                            self.project, allow_quota=True)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["native_subagent"], "NOT_VERIFIED")
        self.assertEqual([r["role"] for r in report["roles"]],
                         ["factory", "studio", "qa"])
        self.assertEqual(spawn.call_count, 3)
        self.assertTrue(all(r["status"] == "INVOCATION_OBSERVED"
                            for r in report["roles"]))
        self.assertNotIn("Implementation sketch", json.dumps(report))
        self.assertNotIn("Assess my project", json.dumps(report))

    def test_reused_session_id_blocks_acceptance(self):
        response = {"exit_code": 0, "error": None,
                    "stdout": json.dumps({"session_id": "session-12345",
                                           "result": "review text"})}
        with patch.object(rt.shutil, "which", return_value="/mock/cli"), \
             patch.object(rt, "_spawn", return_value=response) as spawn:
            report = rt.run("claude", "hybrid", "read-only review",
                            self.project, allow_quota=True)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["roles"][1]["reason"], "REUSED_SESSION_ID")
            self.assertEqual(spawn.call_count, 2)

    def test_no_qa_after_host_failure(self):
        response = {"exit_code": 1, "stdout": "",
                    "error": "HOST_PROCESS_FAILED"}
        with patch.object(rt.shutil, "which", return_value="/mock/cli"), \
             patch.object(rt, "_spawn", return_value=response) as spawn:
            report = rt.run("claude", "hybrid", "Check",
                            self.project, allow_quota=True)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["roles"][0]["status"], "FAILED")
            spawn.assert_called_once()

    def test_missing_session_is_not_pass(self):
        parsed = rt._parse_result("codebuddy", {"exit_code": 0,
            "stdout": '{"result":"Looks fine"}', "error": None})
        self.assertEqual(parsed["status"], "INCONCLUSIVE")

    def test_raw_host_result_never_written_to_audit(self):
        with tempfile.TemporaryDirectory() as outdir:
            private = Path(outdir).resolve()
            if private.stat().st_mode & 0o077:
                private.chmod(0o700)
            filepath = private / "result.json"
            response = {"exit_code": 0, "error": None,
                        "stdout": json.dumps({
                            "result": "MODEL RAW CONTENT, DO NOT SAVE",
                            "session_id": "session-12345",
                        })}
            with patch.object(rt.shutil, "which", return_value="/mock/cli"), \
                 patch.object(rt, "_spawn", return_value=response):
                report = rt.run("claude", "studio", "Review",
                                self.project, allow_quota=True, out=filepath)
            self.assertEqual(report["status"], "BLOCKED")  # reused session
            self.assertTrue(filepath.is_file())
            self.assertNotIn("MODEL RAW CONTENT", filepath.read_text())
            with self.assertRaises(ValueError):
                rt.run("claude", "studio", "Review", self.project,
                       allow_quota=True, out=filepath)

    def test_four_role_preview_requires_no_quota_and_no_process(self):
        with patch.object(rt, "_spawn") as spawn:
            report = rt.run("codebuddy", "four-roles",
                            "Study a small system", self.project)
        self.assertEqual(report["sequence"],
                         ["research", "coding", "qa", "automation"])
        self.assertEqual(report["status"], "NOT_RUN")
        spawn.assert_not_called()

    def test_four_role_sessions_observable_but_not_native_subagent(self):
        answers = [
            {"exit_code": 0, "error": None,
             "stdout": json.dumps({"session_id": f"separate-session-{i:02d}",
                                    "result": f"Role response {i}"})}
            for i in range(4)
        ]
        with patch.object(rt.shutil, "which", return_value="/mock/cli"), \
             patch.object(rt, "_spawn", side_effect=answers):
            report = rt.run("claude", "four-roles", "Review workflow",
                            self.project, allow_quota=True)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(len(report["roles"]), 4)
        self.assertEqual([r["role"] for r in report["roles"]],
                         ["research", "coding", "qa", "automation"])
        self.assertEqual(report["native_subagent"], "NOT_VERIFIED")

    def test_real_local_subprocess_transport_no_model_invocation(self):
        """Use an actual Python child, not an AI host. Does not prove AI acceptance."""
        payload = json.dumps({"result": "Synthetic test only",
                              "session_id": "synthetic-98765"})
        script = "import sys; sys.stdout.write(" + repr(payload) + ")"
        raw = rt._spawn([sys.executable, "-c", script], self.project, 8)
        self.assertIsNone(raw["error"])
        parsed = rt._parse_result("claude", raw)
        self.assertEqual(parsed["status"], "INVOCATION_OBSERVED")
        self.assertEqual(parsed["session_id"], "synthetic-98765")

    def test_real_local_child_timeout_stops(self):
        raw = rt._spawn([sys.executable, "-c",
                         "import time; time.sleep(8)"], self.project, 1)
        self.assertEqual(raw["error"], "HOST_TIMEOUT")

    def test_bounded_stdout_with_no_model_calls(self):
        raw = rt._spawn([sys.executable, "-c",
                         "import sys; sys.stdout.write('x'*1100000)"],
                        self.project, 10)
        self.assertEqual(raw["error"], "OUTPUT_TOO_LARGE")
        self.assertEqual(raw["stdout"], "")

    def test_invalid_inputs_fail_before_spawning(self):
        with patch.object(rt, "_spawn") as spawn:
            for host in ("workbuddy", "hermes", "gemini", "opencode"):
                with self.assertRaises(ValueError):
                    rt.run(host, "hybrid", "hello", self.project, allow_quota=True)
            with self.assertRaises(ValueError):
                rt.run("codebuddy", "hybrid", "hello", self.project, timeout=0,
                       allow_quota=True)
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
