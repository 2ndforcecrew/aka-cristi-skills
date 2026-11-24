"""Shared training is bundled through the existing managed Skill installer."""
import tempfile
import unittest
from pathlib import Path

from tools import skill_installer

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "chef-orchestrator"
REFERENCES = ("AGENTS.md", "rules/TRAINING.md",
              "rules/GLOBAL_WORK_RULES.md", "docs/SYNC_PROTOCOL.md")


class SharedTrainingBundleTests(unittest.TestCase):
    def test_source_and_bundle_match(self):
        for name in REFERENCES:
            with self.subTest(name=name):
                self.assertEqual(
                    (ROOT / "shared-training" / name).read_bytes(),
                    (SKILL / "references" / "shared-training" / name).read_bytes(),
                )

    def test_existing_installer_copies_rules_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "skills"
            plan = skill_installer.inspect(SKILL, "directory", root)
            self.assertEqual(plan["action"], "install")
            self.assertFalse(root.exists())
            skill_installer.install(SKILL, "directory", root, apply=True)
            for name in REFERENCES:
                self.assertEqual(
                    (ROOT / "shared-training" / name).read_bytes(),
                    (root / "chef-orchestrator" / "references" /
                     "shared-training" / name).read_bytes(),
                )
            self.assertEqual(
                skill_installer.inspect(SKILL, "directory", root)["action"],
                "already_installed",
            )
            self.assertEqual(
                skill_installer.verify("chef-orchestrator", "directory", root)["integrity"],
                "PASS",
            )


if __name__ == "__main__":
    unittest.main()
