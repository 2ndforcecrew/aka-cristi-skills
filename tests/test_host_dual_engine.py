"""Full isolated Git/SQLite host handoff tests; all host turns mocked, never inference."""
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import chef_dual_engine as runtime


class HostDualEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.repo = root / "repo"
        self.repo.mkdir()
        self.db = root / "state.db"
        for args in (("init",), ("config", "user.email", "test@example.invalid"),
                     ("config", "user.name", "Test")):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                           capture_output=True)
        (self.repo / "README.md").write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-m", "initial"],
                       check=True, capture_output=True)

    def test_no_consent_before_creating_db(self):
        with self.assertRaises(ValueError):
            runtime.orchestrate("hybrid", "inspect", self.repo, self.db,
                                host="claude")
        self.assertFalse(self.db.exists())

    def test_unsupported_host_refuses_without_file_writes(self):
        with self.assertRaises(ValueError):
            runtime.orchestrate("hybrid", "inspect", self.repo, self.db,
                                host="workbuddy", authorize_inference=True)
        self.assertFalse(self.db.exists())

    def test_three_separate_read_only_host_turns(self):
        history = []
        def host_turn(host, role, text, workspace, timeout, **kwargs):
            history.append((host, role, Path(workspace), kwargs))
            return {
                "status": "COMPLETED",
                "thread_ids": ["sess-" + role + "-12345"],
                "output": "Synthetic " + role + " evidence",
                "native_child_agents": "NOT_VERIFIED",
            }
        with patch.object(runtime.host_runtime, "run", side_effect=host_turn):
            result = runtime.orchestrate(
                "hybrid", "review homepage", self.repo, self.db,
                host="claude", authorize_inference=True)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["native_child_agents"], "NOT_VERIFIED")
        self.assertEqual(result["evidence_kind"],
                         "independent_host_turns_not_native_agent_spawns")
        self.assertEqual([x[1] for x in history], ["factory", "studio", "qa"])
        self.assertEqual(len(set(x[2] for x in history)), 3)
        self.assertTrue(all(x[3].get("authorized") for x in history))
        self.assertEqual((self.repo / "README.md").read_text(), "original\n")
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 3)

    def test_non_codex_factory_must_not_write_even_if_host_tries(self):
        def naughty(host, role, text, workspace, timeout, **kwargs):
            (Path(workspace) / "README.md").write_text("tampered\n")
            return {"status": "COMPLETED", "thread_ids": ["session-factory-abc"],
                    "output": "Untrusted agent claimed pass"}
        with patch.object(runtime.host_runtime, "run", side_effect=naughty):
            result = runtime.orchestrate(
                "factory", "propose", self.repo, self.db, host="opencode",
                authorize_inference=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["results"]["factory"]["status"], "FAILED")
        self.assertEqual((self.repo / "README.md").read_text(), "original\n")

    def test_distinct_sessions_are_required(self):
        with patch.object(runtime.host_runtime, "run", return_value={
            "status": "COMPLETED", "thread_ids": ["same-session"],
            "output": "Synthetic fixture only"}):
            result = runtime.orchestrate(
                "studio", "review", self.repo, self.db, host="gemini",
                authorize_inference=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["qa"]["status"], "FAILED")
        self.assertEqual(result["qa"]["reason"], "missing output or independent thread identity")


if __name__ == "__main__":
    unittest.main()
