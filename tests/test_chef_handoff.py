"""Portable dual-engine handoff is a plan only, never a fake agent run."""
import json
import tempfile
import unittest
from pathlib import Path

from tools import chef_handoff


class HandoffTests(unittest.TestCase):
    def test_hybrid_sequence_and_no_agent_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            data = chef_handoff.plan("hybrid", "Review UX after patch", "workbuddy", project)
            self.assertEqual([x["role"] for x in data["sequence"]],
                             ["factory", "studio", "qa"])
            self.assertEqual(data["native_dispatch"], "NOT_RUN")
            self.assertEqual(data["status"], "PLAN_ONLY")
            self.assertEqual(list(project.iterdir()), [])

    def test_file_written_with_no_pass_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            p = folder / "project"
            p.mkdir()
            spec = chef_handoff.plan("studio", "Review storyboard", "claude", p)
            result = chef_handoff.write_plan(spec, folder)
            saved = json.loads(Path(result["file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "HANDOFF_WRITTEN")
            self.assertEqual(saved["sequence"][-1]["role"], "qa")
            self.assertTrue(all(x["state"] == "NOT_RUN" for x in saved["sequence"]))
            self.assertEqual(saved["native_dispatch"], "NOT_RUN")

    def test_reject_unsafe_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve()
            with self.assertRaises(ValueError):
                chef_handoff.plan("factory", "", "workbuddy", p)
            with self.assertRaises(ValueError):
                chef_handoff.plan("factory", "task", "unknown", p)


if __name__ == "__main__":
    unittest.main()
