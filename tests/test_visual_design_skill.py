"""Offline checks for the brand-neutral Visual Design Skill V0.1 contract."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "visual-design" / "SKILL.md"
TEMPLATE = ROOT / "skills" / "visual-design" / "references" / "decision-record.md"


class VisualDesignSkillContract(unittest.TestCase):
    def test_skill_exists_and_has_frontmatter(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: visual-design", text)
        self.assertIn("description:", text)

    def test_three_core_engines_and_honest_qa(self):
        text = SKILL.read_text(encoding="utf-8").lower()
        for item in ("perceive", "reason", "execute", "verify", "style dna", "not_run", "reduced-motion", "brand-neutral"):
            with self.subTest(item=item):
                self.assertIn(item, text)

    def test_decision_record_has_evidence_and_statuses(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        for item in ("Design Decision Record", "Style DNA", "Evidence", "NOT_RUN", "SUBJECTIVE_REVIEW", "Independent reviewer"):
            with self.subTest(item=item):
                self.assertIn(item.lower(), text.lower())


if __name__ == "__main__":
    unittest.main()
