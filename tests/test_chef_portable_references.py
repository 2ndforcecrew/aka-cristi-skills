"""CHEF references must remain usable after copying only the Skill folder."""
import contextlib
import io
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.generate_skill_index import main


ROOT = Path(__file__).resolve().parents[1]


class ChefPortableReferencesTests(unittest.TestCase):
    def test_routing_references_resolve_in_isolated_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "chef-orchestrator"
            shutil.copytree(ROOT / "skills" / "chef-orchestrator", skill)
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            for label in ("docs/skill-index.json", "docs/dedup-decisions.md"):
                match = re.search(r"\[" + re.escape(label) + r"\]\(([^)]+)\)", text)
                self.assertIsNotNone(match, label)
                target = (skill / match.group(1)).resolve()
                self.assertTrue(target.is_relative_to(skill.resolve()), label)
                self.assertTrue(target.is_file(), str(target))

    def fixture(self, root):
        skill = root / "skills" / "chef-orchestrator"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: chef-orchestrator\ndescription: Lead scoped tasks.\n---\n",
            encoding="utf-8",
        )
        (root / "vendor" / "addy-agent-skills" / "skills").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "docs" / "dedup-decisions.md").write_text("# Decisions\n", encoding="utf-8")

    def run_generator(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return main(list(args))

    def test_default_generation_and_check_keep_bundled_references_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            self.assertEqual(self.run_generator("--root", str(root)), 0)
            bundled = root / "skills" / "chef-orchestrator" / "references"
            for name in ("skill-index.json", "dedup-decisions.md"):
                # Git may check out canonical docs with CRLF on Windows;
                # generated copies deliberately use deterministic LF.
                self.assertEqual(
                    (bundled / name).read_text(encoding="utf-8"),
                    (root / "docs" / name).read_text(encoding="utf-8"),
                )
            self.assertEqual(self.run_generator("--root", str(root), "--check"), 0)
            (bundled / "dedup-decisions.md").write_text("stale\n", encoding="utf-8")
            self.assertEqual(self.run_generator("--root", str(root), "--check"), 1)
            self.assertEqual(self.run_generator("--root", str(root)), 0)
            (bundled / "skill-index.json").unlink()
            self.assertEqual(self.run_generator("--root", str(root), "--check"), 1)

    def test_custom_output_does_not_mutate_default_or_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            output = root / "custom.json"
            self.assertEqual(self.run_generator("--root", str(root), "--output", str(output)), 0)
            self.assertTrue(output.is_file())
            self.assertFalse((root / "docs" / "skill-index.json").exists())
            self.assertFalse((root / "skills" / "chef-orchestrator" / "references").exists())
            self.assertEqual(self.run_generator("--root", str(root), "--output", str(output), "--check"), 0)


if __name__ == "__main__":
    unittest.main()
