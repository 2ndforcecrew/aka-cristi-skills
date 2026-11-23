"""Contract tests for Visual Design Skill evidence ledger validation."""
import unittest
from tools.visual_design_evidence import validate


class EvidenceLedgerTests(unittest.TestCase):
    def base(self):
        return {
            "artifact": "examples/site/index.html",
            "medium": "web",
            "checks": [
                {"name": name, "status": "NOT_RUN", "method": "Browser inspection", "limitation": "Browser not available"}
                for name in ("responsive", "keyboard", "reduced-motion")
            ],
        }

    def test_valid_unverified_ledger(self):
        self.assertEqual(validate(self.base()), [])

    def test_verified_requires_evidence(self):
        data = self.base()
        data["checks"][0] = {"name": "responsive", "status": "VERIFIED", "method": "Browser"}
        self.assertTrue(any("requires evidence" in e for e in validate(data)))

    def test_no_false_interactive_coverage(self):
        data = self.base()
        data["checks"].pop()
        self.assertTrue(any("reduced-motion" in e for e in validate(data)))

    def test_failed_requires_limitation(self):
        data = self.base()
        data["checks"][0] = {"name": "responsive", "status": "FAILED", "method": "Browser"}
        self.assertTrue(any("requires limitation" in e for e in validate(data)))

    def test_duplicate_checks_rejected(self):
        data = self.base()
        data["checks"].append(data["checks"][0].copy())
        self.assertTrue(any("Duplicate" in e for e in validate(data)))


if __name__ == "__main__":
    unittest.main()
