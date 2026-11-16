"""Skill preflight regression tests; no external tools or host calls."""
import tempfile
import unittest
from pathlib import Path

from tools.skill_validator import validate_skill, main


class SkillValidatorTests(unittest.TestCase):
    def make_skill(self, root: Path, body: str = "---\nname: demo-skill\ndescription: A test skill\n---\n# Instructions\nDo work.\n") -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "SKILL.md").write_text(body, encoding="utf-8")
        return root

    def test_valid_skill_is_preflight_only_not_runtime_verified(self):
        with tempfile.TemporaryDirectory() as d:
            result = validate_skill(self.make_skill(Path(d) / "demo"))
        self.assertEqual(result["status"], "PREFLIGHT_ONLY")
        self.assertFalse(result["runtime_verified"])
        self.assertFalse(result["host_compatibility_verified"])

    def test_missing_entry_fails(self):
        with tempfile.TemporaryDirectory() as d:
            result = validate_skill(Path(d))
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["findings"][0]["code"], "MISSING_ENTRY")

    def test_bad_name_and_empty_instructions_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_skill(Path(d) / "bad", "---\nname: Bad_Name\ndescription: test\n---\n")
            result = validate_skill(root)
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("INVALID_NAME", [f["code"] for f in result["findings"]])
        self.assertIn("EMPTY_INSTRUCTIONS", [f["code"] for f in result["findings"]])

    def test_multiline_description_does_not_claim_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_skill(Path(d) / "multiline", "---\nname: demo-skill\ndescription: >\n  multi line\n---\nWork.\n")
            result = validate_skill(root)
        self.assertEqual(result["status"], "PREFLIGHT_ONLY")
        self.assertIn("DESCRIPTION_REVIEW", [f["code"] for f in result["findings"]])

    def test_script_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_skill(Path(d) / "demo")
            (root / "scripts").mkdir()
            target = Path(d) / "outside.py"
            target.write_text("print('not executed')", encoding="utf-8")
            try:
                (root / "scripts" / "escape.py").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            result = validate_skill(root)
            self.assertEqual(result["status"], "FAILED")
            self.assertIn("SYMLINK_IN_SCRIPTS", [f["code"] for f in result["findings"]])


if __name__ == "__main__":
    unittest.main()
