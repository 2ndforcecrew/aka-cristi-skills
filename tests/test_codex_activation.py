"""Offline tests of activation EVIDENCE JUDGING, not real Codex runs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_codex_activation import assess, parse_events, run


NAME = "verified-change-loop"
NONCE = "AKA-PROBE-12345ABC"


def trace(name=NAME, nonce=NONCE):
    return [
        {"type": "thread.started", "thread_id": "fixture-only"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {
            "type": "command_execution",
            "command": "cat .agents/skills/" + name + "/SKILL.md",
            "exit_code": 0}},
        {"type": "item.completed", "item": {
            "type": "command_execution", "command": "cat CASE.md", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "agent_message",
            "text": "Case ID: " + nonce + ". Live defect reproduction NOT_RUN."}},
        {"type": "turn.completed", "usage": {"input_tokens": 42}},
    ]


class CodexAgentEvidenceTests(unittest.TestCase):
    def test_synthetic_positive_evidence(self):
        self.assertEqual(assess(trace(), NAME, NONCE, 0)["status"], "PASS")

    def test_no_skill_file_read_fails(self):
        x = trace()
        x[2]["item"]["command"] = "echo loaded"
        self.assertEqual(assess(x, NAME, NONCE, 0)["status"], "FAIL")

    def test_no_case_read_fails(self):
        x = trace()
        x[3]["item"]["command"] = "echo CASE.md"
        self.assertEqual(assess(x, NAME, NONCE, 0)["status"], "FAIL")

    def test_wrong_case_id_fails(self):
        self.assertEqual(assess(trace(), NAME, "DIFFERENT", 0)["status"], "FAIL")

    def test_no_completed_agent_turn_fails(self):
        self.assertEqual(assess(trace()[:-1], NAME, NONCE, 0)["status"], "FAIL")

    def test_failed_exit_fails(self):
        self.assertEqual(assess(trace(), NAME, NONCE, 1)["status"], "FAIL")

    def test_no_events_fails(self):
        self.assertEqual(assess([], NAME, NONCE, 0)["status"], "FAIL")

    def test_parse_jsonl_ignores_noise(self):
        line = "not-json\n" + "\n".join(json.dumps(x) for x in trace())
        self.assertEqual(len(parse_events(line)), len(trace()))

    def test_missing_codex_reports_not_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "skills" / NAME
            src.mkdir(parents=True)
            (src / "SKILL.md").write_text(
                "---\nname: verified-change-loop\ndescription: test\n---\n",
                encoding="utf-8")
            with patch("tools.verify_codex_activation.shutil.which",
                       return_value=None):
                result = run(NAME, root=root)
            self.assertEqual(result["status"], "NOT_RUN")
            self.assertFalse(result["invoked"])


if __name__ == "__main__":
    unittest.main()
