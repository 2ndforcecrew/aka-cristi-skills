"""Builder and lifecycle tests, run only after implementation is complete."""
import tempfile
import unittest
from pathlib import Path

from tools.skill_builder import create
from tools.skill_lifecycle import inventory


class BuilderLifecycleTests(unittest.TestCase):
    def test_preview_is_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "sample-skill"
            result = create("sample-skill", target, "A sample task")
            self.assertEqual(result["status"], "PLANNED")
            self.assertFalse(target.exists())

    def test_create_preflight_inventory_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "sample-skill"
            result = create("sample-skill", target, "A sample task", apply=True)
            self.assertEqual(result["status"], "CREATED_PREFLIGHT_ONLY")
            first = inventory(target)
            second = inventory(target)
            self.assertEqual(first["digest_sha256"], second["digest_sha256"])
            self.assertFalse(first["runtime_verified"])
            self.assertFalse(first["release_approved"])
            with self.assertRaises(FileExistsError):
                create("sample-skill", target, "A sample task", apply=True)

    def test_reject_unsafe_names_and_descriptions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ("../escape", "Bad_Name", "-oops"):
                with self.assertRaises(ValueError):
                    create(name, root / "target", "Description")
            with self.assertRaises(ValueError):
                create("safe-name", root / "target", "desc\nname: injected")

    def test_inventory_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "sample-skill"
            create("sample-skill", target, "A sample task", apply=True)
            before = inventory(target)["digest_sha256"]
            with (target / "SKILL.md").open("a", encoding="utf-8") as f:
                f.write("\nchanged\n")
            after = inventory(target)["digest_sha256"]
            self.assertNotEqual(before, after)

    def test_inventory_blocks_missing_entry(self):
        with tempfile.TemporaryDirectory() as d:
            result = inventory(Path(d))
            self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
