"""Verify shared training is shipped by the existing managed Skill installer."""
import tempfile
import unittest
from pathlib import Path

from tools import skill_installer

ROOT = Path(__file__).resolve().parents[1]
CHEF = ROOT / "skills" / "chef-orchestrator"
RULES = ("TRAINING.md", "GLOBAL_WORK_RULES.md")


class BundledSharedTrainingTest(unittest.TestCase):
    def test_public_and_installable_rule_copies_match(self):
        entry = (CHEF / "SKILL.md").read_text(encoding="utf-8")
        for name in RULES:
            with self.subTest(name=name):
                self.assertIn("references/" + name, entry)
                self.assertEqual(
                    (CHEF / "references" / name).read_bytes(),
                    (ROOT / "shared-training" / "rules" / name).read_bytes(),
                )

    def test_install_and_verify_in_isolated_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            # macOS tempfile may use /var, a symlink to /private/var.
            # Resolve only our freshly created test directory; retain installer guards.
            dest = Path(folder).resolve(strict=True) / "skills"
            preview = skill_installer.inspect(CHEF, "directory", dest)
            self.assertEqual(preview["action"], "install")
            self.assertFalse(dest.exists())
            installed = skill_installer.install(CHEF, "directory", dest, apply=True)
            self.assertTrue(installed["applied"])
            self.assertEqual(
                skill_installer.verify("chef-orchestrator", "directory", dest)["integrity"],
                "PASS",
            )
            for name in RULES:
                self.assertEqual(
                    (dest / "chef-orchestrator" / "references" / name).read_bytes(),
                    (ROOT / "shared-training" / "rules" / name).read_bytes(),
                )
            self.assertEqual(
                skill_installer.inspect(CHEF, "directory", dest)["action"],
                "already_installed",
            )


if __name__ == "__main__":
    unittest.main()
