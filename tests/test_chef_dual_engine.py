"""Offline tests; mocked adapters do not count as live agent acceptance."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import chef_dual_engine

class DualEngineTests(unittest.TestCase):
    def test_route(self):
        self.assertEqual(chef_dual_engine.route("hybrid"), ["factory", "studio"])
        with self.assertRaises(ValueError):
            chef_dual_engine.route("unknown")

    def test_missing_cli_is_not_run(self):
        with patch.object(chef_dual_engine, "codex_available", return_value=False):
            self.assertEqual(chef_dual_engine.run_codex("factory", "x", Path.cwd())["status"], "NOT_RUN")

    def test_real_execution_not_claimed_from_mock(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(chef_dual_engine, "run_codex", return_value={"status": "COMPLETED"}):
                result = chef_dual_engine.execute("hybrid", "inspect", folder, Path(folder)/"events.db")
            self.assertEqual(result["status"], "REVIEW_REQUIRED")
            self.assertEqual(result["qa"]["status"], "COMPLETED")

    def test_failed_agent_blocks_qa(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(chef_dual_engine, "run_codex", return_value={"status": "FAILED"}):
                result = chef_dual_engine.execute("hybrid", "inspect", folder, Path(folder)/"events.db")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["qa"], "NOT_RUN")

if __name__ == "__main__":
    unittest.main()
