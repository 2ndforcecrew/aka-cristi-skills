"""Offline CHEF Skill journal tests; no paid model calls."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "chef-control-center" / "scripts" / "events.py"
spec = importlib.util.spec_from_file_location("chef_skill_events", SCRIPT)
events = importlib.util.module_from_spec(spec)
spec.loader.exec_module(events)


class EventJournalTests(unittest.TestCase):
    def test_record_and_read_without_agent_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "events.sqlite3"
            events.record(db, "TASK-1", "coding", "STARTED", "build", "sha256:abc")
            rows = events.read(db, "TASK-1")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "STARTED")
            self.assertEqual(rows[0]["evidence_ref"], "sha256:abc")

    def test_rejects_sensitive_unstructured_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "events.sqlite3"
            with self.assertRaises(ValueError):
                events.record(db, "TASK-1", "coding", "STARTED", "build", note="/private/secret")
            self.assertFalse(db.exists())

    def test_missing_read_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "absent.sqlite3"
            with self.assertRaises(FileNotFoundError):
                events.read(db)
            self.assertFalse(db.exists())

    def test_installer_includes_skill(self):
        from tools.quick_install import SKILLS
        self.assertIn("chef-control-center", SKILLS)


if __name__ == "__main__":
    unittest.main()
