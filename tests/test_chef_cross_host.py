"""Cross-host Dual-Engine: real local git snapshots, synthetic host responses ONLY."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import chef_dual_engine as chef


def git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)


class CrossHostDualEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / "project"
        self.project.mkdir()
        git(self.project, "init", "--quiet")
        (self.project / "README.md").write_text("A test only\n", encoding="utf-8")
        git(self.project, "add", "README.md")
        git(self.project, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "fixture")
        self.db = self.base / "private" / "chef.sqlite3"
        self.db.parent.mkdir()

    def test_cross_host_attempt_needs_quota_consent_without_creating_state(self):
        with patch("tools.host_runtime.run") as launch:
            result = chef.orchestrate(
                "studio", "Review UX", self.project, self.db, 20,
                studio_host="claude", qa_host="gemini", consent_live=False
            )
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertFalse(self.db.exists())
        launch.assert_not_called()

    def test_real_git_handoff_separate_backend_sessions_no_native_spawn_claim(self):
        results = [
            {"status": "COMPLETED", "session_id": "claude-session-100",
             "output": "Studio review", "runtime_evidence": "CLI_TRACE"},
            {"status": "COMPLETED", "session_id": "gemini-session-200",
             "output": "QA review", "runtime_evidence": "CLI_TRACE"},
        ]
        with patch("tools.host_runtime.run", side_effect=results) as launch:
            result = chef.orchestrate(
                "studio", "Review UX", self.project, self.db, 20,
                studio_host="claude", qa_host="gemini", consent_live=True
            )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["release"], "BLOCKED")
        self.assertIn("NOT_native_subagents", result["evidence_kind"])
        self.assertEqual(result["results"]["studio"]["host"], "claude")
        self.assertEqual(result["qa"]["host"], "gemini")
        self.assertEqual(launch.call_count, 2)
        self.assertEqual(launch.call_args_list[0].args[0], "claude")
        self.assertEqual(launch.call_args_list[1].args[0], "gemini")
        self.assertTrue(self.db.exists())
        self.assertEqual((self.project / "README.md").read_text(), "A test only\n")

    def test_unattributable_second_session_blocks_completion(self):
        with patch("tools.host_runtime.run", side_effect=[
            {"status": "COMPLETED", "session_id": "shared-session",
             "output": "Studio review"},
            {"status": "COMPLETED", "session_id": "shared-session",
             "output": "QA report"},
        ]):
            result = chef.orchestrate(
                "studio", "Review UX", self.project, self.db, 20,
                studio_host="claude", qa_host="gemini", consent_live=True
            )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["qa"]["status"], "FAILED")

    def test_missing_cli_fails_closed_and_records_not_run(self):
        with patch("tools.host_runtime.run", return_value={
            "status": "NOT_RUN", "reason": "HOST_CLI_NOT_FOUND",
        }):
            result = chef.orchestrate(
                "studio", "Review UX", self.project, self.db, 20,
                studio_host="workbuddy", consent_live=True
            )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["qa"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
