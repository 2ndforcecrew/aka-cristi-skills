"""Runtime acceptance tests: mocks are explicitly not live evidence."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import chef_host_runtime as runtime


class HostRuntimeTests(unittest.TestCase):
    def test_probe_no_binary_does_not_claim_compatibility(self):
        for host in runtime.HOSTS:
            with self.subTest(host=host):
                report = runtime.probe(host, which=lambda _: None)
                self.assertIn(report["status"], ("UNSUPPORTED", "NOT_INSTALLED"))
                self.assertNotEqual(report["native_subagent"], "PASS")

    def test_version_probe_only_and_bounded(self):
        call = Mock(return_value=Mock(returncode=0, stdout=b"claude 2.0.1", stderr=b""))
        data = runtime.probe("claude", which=lambda _: "/usr/bin/claude", run=call)
        self.assertEqual(data["version"], "2.0.1")
        self.assertEqual(data["live_runtime"], "NOT_RUN")
        self.assertEqual(call.call_args.args[0], ["/usr/bin/claude", "--version"])
        self.assertEqual(call.call_args.kwargs["timeout"], 5)

    def test_no_inference_without_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = Mock()
            result = runtime.invoke("claude", "qa", "review", Path(tmp).resolve(),
                                    runner=runner, consent=False)
            self.assertEqual(result["status"], "CONSENT_REQUIRED")
            runner.assert_not_called()

    def test_unverified_workbuddy_dispatch_refuses_to_invoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = Mock()
            result = runtime.invoke("workbuddy", "qa", "review", Path(tmp).resolve(),
                                    runner=runner, consent=True)
            self.assertEqual(result["status"], "UNSUPPORTED")
            runner.assert_not_called()

    def test_claude_parent_turn_never_claims_native_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = Mock(return_value={
                "status": "OBSERVED",
                "payload": {"type": "result", "is_error": False,
                            "session_id": "session-123", "result": "Reviewed"},
            })
            result = runtime.invoke("claude", "qa", "review", Path(tmp).resolve(),
                                    runner=runner, which=lambda _: "/bin/claude",
                                    consent=True)
            self.assertEqual(result["status"], "HOST_COMPLETED")
            self.assertEqual(result["native_subagent"], "NOT_VERIFIED")
            self.assertEqual(result["evidence_kind"], "CLAUDE_PARENT_SESSION_NOT_CHILD_AGENT")
            cmd = runner.call_args.args[0]
            self.assertIn("--permission-mode", cmd)
            self.assertIn("plan", cmd)
            self.assertNotIn("--dangerously-skip-permissions", cmd)

    def test_claude_missing_evidence_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = Mock(return_value={"status": "OBSERVED", "payload": {"result": "ok"}})
            result = runtime.invoke("claude", "studio", "review", Path(tmp).resolve(),
                                    runner=runner, which=lambda _: "/bin/claude",
                                    consent=True)
            self.assertEqual(result["status"], "BLOCKED")

    def test_timeout_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                runtime.invoke("claude", "qa", "test", Path(tmp).resolve(),
                               consent=True, timeout=99999)
            with self.assertRaises(ValueError):
                runtime._process(["nope"], Path(tmp).resolve(), 0)

    def test_no_codex_approval_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runtime, "run_codex", return_value={
                "status": "COMPLETED", "thread_ids": ["parent"]}) as codex:
                result = runtime.invoke("codex", "qa", "review", Path(tmp).resolve(),
                                        which=lambda _: "/bin/codex", consent=True)
                self.assertEqual(result["native_subagent"], "NOT_VERIFIED")
                self.assertEqual(codex.call_args.kwargs["sandbox"], "read-only")


if __name__ == "__main__":
    unittest.main()
