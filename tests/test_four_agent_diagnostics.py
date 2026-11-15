import json
import tempfile
import unittest
import uuid
from pathlib import Path

from tools.diagnose_four_agents import diagnostic

class FourAgentDiagnosticTests(unittest.TestCase):
    def test_missing_rollout_is_not_proof(self):
        with tempfile.TemporaryDirectory() as d:
            result = diagnostic(Path(d), str(uuid.uuid4()))
        self.assertFalse(result["root_rollout_found"])
        self.assertEqual(result["spawn_calls_observed"], 0)
        self.assertEqual(result["named_role_spawn_outputs"], [])

    def test_reports_tool_name_and_argument_keys_without_leaking_prompt(self):
        root = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            folder = home / "sessions"
            folder.mkdir()
            path = folder / ("rollout-" + root + ".jsonl")
            secret = "SENSITIVE_DO_NOT_OUTPUT"
            items = [
                {"type": "session_meta", "payload": {"id": root}},
                {"type": "response_item", "payload": {"type": "function_call",
                 "name": "functions.spawn_agent", "call_id": "call1",
                 "arguments": json.dumps({"agent_type": "aka_research", "message": secret})}},
            ]
            path.write_text("\n".join(json.dumps(x) for x in items) + "\n",
                            encoding="utf-8")
            result = diagnostic(home, root)
        self.assertTrue(result["root_rollout_found"])
        self.assertEqual(result["spawn_calls_observed"], 1)
        self.assertEqual(result["spawn_role_argument_fields"]["agent_type"], 1)
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(result["named_role_spawn_outputs"], [])

    def test_stage_diagnostic_exposes_no_raw_argument_or_output(self):
        root = str(uuid.uuid4())
        child = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            folder = home / "sessions"
            folder.mkdir()
            secret = "PRIVATE_REPORT_SENTINEL"
            records = [
                {"type": "session_meta", "payload": {"id": root}},
                {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent", "call_id": "x", "arguments": json.dumps({"agent_type": "aka_research", "message": secret})}},
                {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "x", "output": json.dumps({"agent_id": child, "nickname": secret})}},
            ]
            (folder / ("rollout-" + root + ".jsonl")).write_text("\n".join(json.dumps(x) for x in records), encoding="utf-8")
            result = diagnostic(home, root)
        self.assertTrue(result["role_stages"]["aka_research"]["SPAWN_SUCCESS"])
        self.assertFalse(result["role_stages"]["aka_research"]["ROLE_PASS"])
        self.assertNotIn(secret, json.dumps(result))

if __name__ == "__main__":
    unittest.main()
