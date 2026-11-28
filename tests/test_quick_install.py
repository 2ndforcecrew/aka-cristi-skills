"""统一安装器的真实临时文件系统测试，不运行 Codex 或模型。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.quick_install import (
    NATIVE_SKILLS,
    SKILLS,
    VENDOR_SKILLS,
    execute,
    main,
    skill_source,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class QuickInstallTests(unittest.TestCase):
    def test_preview_has_no_writes(self):
        with tempfile.TemporaryDirectory() as d:
            home, skills = Path(d).resolve() / "codex", Path(d).resolve() / "skills"
            result = execute(codex_home=home, skills_root=skills)
            self.assertEqual(result["status"], "PREVIEW")
            self.assertFalse(home.exists())
            self.assertFalse(skills.exists())

    def test_install_verify_reinstall_preserves_existing_rules(self):
        with tempfile.TemporaryDirectory() as d:
            home, skills = Path(d).resolve() / "codex", Path(d).resolve() / "skills"
            home.mkdir()
            original = "# 私有规则，禁止覆盖\r\n\r\n"
            (home / "AGENTS.md").write_bytes(original.encode("utf-8"))
            result = execute(apply=True, codex_home=home, skills_root=skills)
            self.assertEqual(result["status"], "FILES_VERIFIED")
            self.assertEqual(len(result["roles"]), 4)
            self.assertEqual(len(result["skills"]), len(SKILLS))
            self.assertEqual(result["agent_activation"], "NOT_RUN")
            self.assertTrue((home / "AGENTS.md").read_bytes().startswith(original.encode("utf-8")))
            self.assertEqual(execute(apply=True, codex_home=home,
                                     skills_root=skills)["status"], "FILES_VERIFIED")

    def test_interactive_cancel_never_writes(self):
        with tempfile.TemporaryDirectory() as d:
            home, skills = Path(d).resolve() / "codex", Path(d).resolve() / "skills"
            with patch("builtins.input", return_value="no"):
                code = main(["--interactive", "--codex-home", str(home),
                             "--skills-root", str(skills)])
            self.assertEqual(code, 0)
            self.assertFalse(home.exists())
            self.assertFalse(skills.exists())

    def test_conflict_rejects_all_writes(self):
        with tempfile.TemporaryDirectory() as d:
            home, skills = Path(d).resolve() / "codex", Path(d).resolve() / "skills"
            role_folder = home / "agents"
            role_folder.mkdir(parents=True)
            untouched = role_folder / "research.toml"
            untouched.write_text("private content", encoding="utf-8")
            with self.assertRaises(ValueError):
                execute(apply=True, codex_home=home, skills_root=skills)
            self.assertEqual(untouched.read_text(encoding="utf-8"), "private content")
            self.assertFalse((home / "AGENTS.md").exists())
            self.assertFalse(skills.exists())

    def test_skills_match_skill_index(self):
        # The generated index (tools/generate_skill_index.py) is the source
        # of truth for the installable set; the installer literals must
        # match it exactly, or the two drift apart silently.
        index = json.loads((REPO_ROOT / "docs" / "skill-index.json").read_text(encoding="utf-8"))
        installable = {s["name"] for s in index["skills"] if s["installable"]}
        self.assertEqual(set(SKILLS), installable)
        self.assertEqual(len(NATIVE_SKILLS), 7)
        self.assertEqual(len(VENDOR_SKILLS), 25)
        self.assertEqual(len(SKILLS), 32)
        for skill in SKILLS:
            source = skill_source(skill)
            self.assertTrue((source / "SKILL.md").is_file(), skill)
        # Vendored interview-me is reference-only: the name resolves to
        # the NATIVE skill, and the vendor tuple never contains it.
        self.assertNotIn("interview-me", VENDOR_SKILLS)
        self.assertEqual(
            skill_source("interview-me"),
            REPO_ROOT / "skills" / "interview-me")
        with self.assertRaises(ValueError):
            skill_source("no-such-skill")

    def test_install_writes_no_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            home, skills = Path(d).resolve() / "codex", Path(d).resolve() / "skills"
            result = execute(apply=True, codex_home=home, skills_root=skills)
            self.assertEqual(result["status"], "FILES_VERIFIED")
            self.assertEqual(len(result["skills"]), 32)
            links = [p for p in skills.rglob("*") if p.is_symlink()]
            self.assertEqual(links, [])


if __name__ == "__main__":
    unittest.main()
