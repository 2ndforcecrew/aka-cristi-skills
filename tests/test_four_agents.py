"""Contract tests: synthetic traces are NOT counted as real Codex invocations."""
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from tools.verify_four_agents import (
    ROLES, evaluate, find_role_tomls, json_lines, parse_spawn_calls, run,
)


class FourAgentEvidenceTests(unittest.TestCase):
    def test_no_codex_returns_not_run(self):
        with patch("tools.verify_four_agents.shutil.which", return_value=None):
            result = run(codex_home=Path("/nonexistent-aka-codex"))
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertFalse(result["invoked"])

    def test_plain_text_claim_does_not_prove_spawn(self):
        text = json.dumps({"type": "item.completed", "item": {
            "type": "agent_message",
            "text": "I spawned aka_research, aka_coding, aka_qa, aka_automation"}})
        self.assertEqual(parse_spawn_calls(json_lines(text)), {})

    def test_task_name_label_not_custom_agent_role(self):
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "call_id": "call1", "arguments": json.dumps({
                "task_name": "aka_research", "prompt": "Hello"})}}
        output = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": json.dumps({"agent_id": str(uuid.uuid4())})}}
        self.assertEqual(parse_spawn_calls([call, output]), {})

    def test_generic_agent_type_not_custom_role(self):
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "call_id": "call1", "arguments": json.dumps({"agent_type": "worker"})}}
        output = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": json.dumps({"agent_id": str(uuid.uuid4())})}}
        self.assertEqual(parse_spawn_calls([call, output]), {})

    def test_exact_role_and_correlated_output_can_prove_spawn_stage(self):
        thread = str(uuid.uuid4())
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "functions.spawn_agent",
            "call_id": "call1", "arguments": json.dumps({
                "agent_type": "aka_research", "message": "Read fixture"})}}
        output = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": json.dumps({"agent_id": thread})}}
        result = parse_spawn_calls([call, output])
        self.assertEqual(result["aka_research"]["child_thread_id"], thread)

    def test_unpaired_call_or_failed_output_cannot_prove_spawn(self):
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "call_id": "call1", "arguments": '{"agent_type":"aka_research"}'}}
        self.assertEqual(parse_spawn_calls([call]), {})
        out = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": "Failed to spawn " + str(uuid.uuid4())}}
        self.assertEqual(parse_spawn_calls([call, out]), {})

    def test_empty_real_rollout_is_inconclusive_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            result = evaluate([], Path(d), 0, str(uuid.uuid4()), 0, True)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertTrue(all(v == "NOT_VERIFIED" for v in result["roles"].values()))

    def test_no_child_rollout_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            tid = str(uuid.uuid4())
            session = home / "sessions" / ("rollout-" + tid + ".jsonl")
            session.parent.mkdir()
            session.write_text(json.dumps({"type": "session_meta",
                                          "payload": {"id": tid}}))
            result = evaluate([], home, 0, tid, 0, True)
        self.assertEqual(result["status"], "INCONCLUSIVE")

    def test_source_of_truth_contains_four_roles(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            folder = home / "agents"
            folder.mkdir()
            for name in ("research", "coding", "qa", "automation"):
                (folder / (name + ".toml")).write_bytes(
                    (root / "agents" / (name + ".toml")).read_bytes())
            checked = find_role_tomls(home)
        self.assertEqual(set(checked), set(ROLES))
        self.assertTrue(all(v == "PASS" for v in checked.values()))


if __name__ == "__main__":
    unittest.main()
