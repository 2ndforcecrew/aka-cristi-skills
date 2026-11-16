import unittest
from tools.release_gate_triage import report

class ReleaseGateTriageTests(unittest.TestCase):
    def test_all_six_gates_are_distinct(self):
        gates = report()["gates"]
        self.assertEqual([g["issue"] for g in gates], list(range(8, 14)))
        self.assertEqual(len({g["workstream"] for g in gates}), 6)

    def test_never_claims_unverified_release_pass(self):
        result = report()
        self.assertEqual(result["release_status"], "BLOCKED")
        self.assertTrue(all(g["release_pass"] is False for g in result["gates"]))

if __name__ == "__main__":
    unittest.main()
