"""Builder and lifecycle tests, run only after implementation is complete."""
import json
from contextlib import chdir
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.skill_builder import create
from tools.skill_lifecycle import inventory


class BuilderLifecycleTests(unittest.TestCase):
    def test_preview_is_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve() / "sample-skill"
            result = create("sample-skill", target, "A sample task")
            self.assertEqual(result["status"], "PLANNED")
            self.assertFalse(target.exists())

    def test_create_preflight_inventory_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve() / "sample-skill"
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
            root = Path(d).resolve()
            for name in ("../escape", "Bad_Name", "-oops"):
                with self.assertRaises(ValueError):
                    create(name, root / "target", "Description")
            with self.assertRaises(ValueError):
                create("safe-name", root / "target", "desc\nname: injected")

    def test_description_round_trips_as_quoted_scalar(self):
        descriptions = ("Task: details", "Task # comment", "true", "null", "[items]", "{key: value}")
        with tempfile.TemporaryDirectory() as d:
            for index, description in enumerate(descriptions):
                with self.subTest(description=description):
                    target = Path(d).resolve() / ("sample-" + str(index))
                    create("sample-skill", target, description, apply=True)
                    lines = (target / "SKILL.md").read_text(encoding="utf-8").splitlines()
                    value = next(line.removeprefix("description: ")
                                 for line in lines if line.startswith("description: "))
                    # A JSON quoted string is also a YAML double-quoted scalar.
                    # Parse the emitted artifact, without a new YAML dependency.
                    try:
                        decoded = json.loads(value)
                    except ValueError:
                        self.fail("generated description is not a safely quoted scalar")
                    self.assertEqual(decoded, description)

    def test_description_preserves_unicode_separators_and_emoji(self):
        emoji = "\U0001f600"
        with tempfile.TemporaryDirectory() as d:
            for codepoint in (0x85, 0x2028, 0x2029):
                with self.subTest(codepoint=codepoint):
                    separator = chr(codepoint)
                    description = "First" + separator + "second " + emoji
                    target = Path(d).resolve() / ("sample-" + str(codepoint))
                    create("sample-skill", target, description, apply=True)
                    content = (target / "SKILL.md").read_text(encoding="utf-8")
                    frontmatter = content.split("---", 2)[1]
                    self.assertNotIn(separator, frontmatter)
                    self.assertIn(emoji, frontmatter)
                    value = next(line.removeprefix("description: ")
                                 for line in frontmatter.splitlines()
                                 if line.startswith("description: "))
                    self.assertEqual(json.loads(value), description)

    def test_inventory_blocks_unreadable_subdirectory(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve() / "sample-skill"
            create("sample-skill", target, "A sample task", apply=True)
            private = target / "unreadable"
            private.mkdir()
            (private / "notes.txt").write_text("must not disappear from inventory", encoding="utf-8")
            real_scandir = os.scandir

            def denied_scandir(path):
                if Path(path) == private:
                    raise PermissionError("synthetic unreadable directory")
                return real_scandir(path)

            with patch("tools.skill_lifecycle.os.scandir", side_effect=denied_scandir):
                result = inventory(target)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(result["runtime_verified"])
            self.assertNotIn("digest_sha256", result)

    def test_inventory_blocks_file_stat_error(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve() / "sample-skill"
            create("sample-skill", target, "A sample task", apply=True)
            real_stat = Path.stat

            def denied_stat(path, *args, **kwargs):
                if path == target / "CHANGELOG.md":
                    raise PermissionError("synthetic stat denial")
                return real_stat(path, *args, **kwargs)

            with patch.object(Path, "stat", denied_stat):
                try:
                    result = inventory(target)
                except OSError:
                    self.fail("inventory leaked an OS error instead of returning BLOCKED")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertNotIn("digest_sha256", result)

    def test_inventory_blocks_file_read_error(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve() / "sample-skill"
            create("sample-skill", target, "A sample task", apply=True)
            real_read = Path.read_bytes

            def denied_read(path):
                if path == target / "CHANGELOG.md":
                    raise PermissionError("synthetic read denial")
                return real_read(path)

            with patch.object(Path, "read_bytes", denied_read):
                try:
                    result = inventory(target)
                except OSError:
                    self.fail("inventory leaked an OS error instead of returning BLOCKED")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertNotIn("digest_sha256", result)

    def test_inventory_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve() / "sample-skill"
            create("sample-skill", target, "A sample task", apply=True)
            before = inventory(target)["digest_sha256"]
            with (target / "SKILL.md").open("a", encoding="utf-8") as f:
                f.write("\nchanged\n")
            after = inventory(target)["digest_sha256"]
            self.assertNotEqual(before, after)

    def test_inventory_blocks_missing_entry(self):
        with tempfile.TemporaryDirectory() as d:
            result = inventory(Path(d).resolve())
            self.assertEqual(result["status"], "BLOCKED")


class RedirectSafetyTests(unittest.TestCase):
    def make_redirect(self, path, target):
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(path), str(target)],
                capture_output=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 0, "Windows junction creation failed")
        else:
            path.symlink_to(target, target_is_directory=True)

    def test_builder_rejects_redirected_destination_ancestor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            outside = root / "outside"
            (outside / "nested").mkdir(parents=True)
            sentinel = outside / "private.txt"
            sentinel.write_bytes(b"preserve outside")
            alias = root / "alias"
            self.make_redirect(alias, outside)
            target = alias / "nested" / "new-skill"
            with self.assertRaises(ValueError):
                create("new-skill", target, "A sample task", apply=True)
            self.assertFalse((outside / "nested" / "new-skill").exists())
            self.assertEqual(sentinel.read_bytes(), b"preserve outside")

    def test_builder_uses_checked_expanded_destination(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            home, work, outside = root / "home", root / "work", root / "outside"
            for path in (home, work, outside):
                path.mkdir()
            sentinel = outside / "private.txt"
            sentinel.write_bytes(b"preserve outside")
            self.make_redirect(work / "~", outside)
            with patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}), chdir(work):
                result = create("new-skill", Path("~/new-skill"), "A sample task", apply=True)
            self.assertEqual(result["destination"], str(home / "new-skill"))
            self.assertTrue((home / "new-skill" / "SKILL.md").is_file())
            self.assertFalse((outside / "new-skill").exists())
            self.assertEqual(sentinel.read_bytes(), b"preserve outside")

    def test_inventory_uses_checked_expanded_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            home, work, outside = root / "home", root / "work", root / "outside"
            for path in (home, work, outside):
                path.mkdir()
            create("sample-skill", home / "sample-skill", "A sample task", apply=True)
            sentinel = outside / "private.txt"
            sentinel.write_bytes(b"preserve outside")
            self.make_redirect(work / "~", outside)
            with patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}), chdir(work):
                result = inventory(Path("~/sample-skill"))
            self.assertEqual(result["status"], "INVENTORIED_NOT_RELEASED")
            self.assertEqual(result["files"], ["CHANGELOG.md", "SKILL.md"])
            self.assertEqual(sentinel.read_bytes(), b"preserve outside")

    def test_inventory_rejects_redirected_root_before_reading(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            outside = root / "outside"
            create("sample-skill", outside, "A sample task", apply=True)
            alias = root / "alias"
            self.make_redirect(alias, outside)
            with patch.object(Path, "read_text", side_effect=AssertionError("redirected root was read")):
                result = inventory(alias)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(result["runtime_verified"])

    def test_inventory_rejects_nested_redirect_before_reading(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            target = root / "sample-skill"
            create("sample-skill", target, "A sample task", apply=True)
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "private.txt"
            sentinel.write_bytes(b"preserve outside")
            self.make_redirect(target / "resources", outside)
            real_read = Path.read_bytes

            def guarded_read(path):
                if path.name == "private.txt":
                    raise AssertionError("redirected private file was read")
                return real_read(path)

            with patch.object(Path, "read_bytes", guarded_read):
                result = inventory(target)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(result["runtime_verified"])
            self.assertEqual(sentinel.read_bytes(), b"preserve outside")


if __name__ == "__main__":
    unittest.main()
