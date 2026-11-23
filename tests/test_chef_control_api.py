"""Offline regression checks for the CHEF local read-only API."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.chef_control_api import task_summary


class ControlApiTests(unittest.TestCase):
    def test_reads_only_public_task_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chef.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, config TEXT, status TEXT)")
                db.execute("INSERT INTO tasks VALUES (?,?,?)",
                           ("task-123", '{"prompt":"SECRET","workspace":"/private/path"}', "IN_PROGRESS"))
                db.commit()
            rows = task_summary(path)
            self.assertEqual(rows, [{"task_id": "task-123", "status": "IN_PROGRESS"}])
            self.assertNotIn("SECRET", repr(rows))
            self.assertNotIn("/private/path", repr(rows))

    def test_missing_database_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "absent.sqlite3"
            with self.assertRaises(FileNotFoundError):
                task_summary(path)
            self.assertFalse(path.exists())

    def test_legacy_events_only_database_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE events (task_id TEXT, role TEXT, status TEXT, timestamp REAL, evidence TEXT)")
            self.assertEqual(task_summary(path), [])

    def test_rejects_invalid_limits(self):
        with self.assertRaises(ValueError):
            task_summary("/missing", limit=0)
        with self.assertRaises(ValueError):
            task_summary("/missing", limit=101)


if __name__ == "__main__":
    unittest.main()
