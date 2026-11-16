"""Strict summary gate tests. These fixtures are synthetic, not live scans."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.scan_report_gate import summarize


class ScanReportGateTests(unittest.TestCase):
    def sample(self, *, rec="SAFE", coverage=100, complete=True, success=True):
        return {
            "risk_assessment": {"score": 0, "recommendation": rec},
            "execution_successful": success,
            "analysis_completeness": {
                "is_complete": complete,
                "coverage_percent": coverage,
                "execution_successful": success,
                "ledger_exceptions": [],
                "dependency_inspection": {"status": "not_requested"},
            },
            "issues": [],
        }

    def check(self, report, scanner_exit=0):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "scan.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            return summarize(path, scanner_exit)

    def test_complete_safe_is_only_static_pass(self):
        result = self.check(self.sample())
        self.assertEqual(result["status"], "STATIC_SCAN_PASS_ONLY")
        self.assertEqual(result["dependency_inspection_status"], "not_requested")

    def test_do_not_install_is_not_changed_by_report_summary(self):
        result = self.check(self.sample(rec="DO_NOT_INSTALL"))
        self.assertEqual(result["status"], "BLOCKED_RISK")
        self.assertEqual(result["recommendation"], "DO_NOT_INSTALL")

    def test_caution_is_not_automatic_release_approval(self):
        self.assertEqual(self.check(self.sample(rec="CAUTION"))["status"], "BLOCKED_RISK")

    def test_incomplete_blocks_even_when_safe(self):
        self.assertEqual(self.check(self.sample(coverage=98.1, complete=False))["status"],
                         "BLOCKED_INCOMPLETE")

    def test_nonzero_scanner_exit_blocks(self):
        self.assertNotEqual(self.check(self.sample(), scanner_exit=1)["status"],
                            "STATIC_SCAN_PASS_ONLY")

    def test_missing_or_untrusted_json_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(summarize(Path(d) / "missing.json", 2)["status"],
                             "BLOCKED_INVALID_REPORT")
        self.assertEqual(self.check({"recommendation": "SAFE"})["status"],
                         "BLOCKED_INVALID_REPORT")


if __name__ == "__main__":
    unittest.main()
