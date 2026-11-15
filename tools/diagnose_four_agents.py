"""Privacy-preserving local diagnostics for Codex multi-agent rollout evidence.

Never prints prompts, messages, tool arguments, secrets or raw session records.
"""
import argparse
import collections
import json
import os
from pathlib import Path

from tools.verify_four_agents import ROLES, json_lines, rooted_sessions, parse_spawn_calls

def classify_call(item):
    if item.get("type") != "function_call":
        return None
    name = str(item.get("name", "")).split(".")[-1]
    if name not in ("spawn_agent", "send_input", "wait", "close_agent", "resume_agent"):
        return None
    # Never retain arguments: their contents could be sensitive.
    return name

def diagnostic(home, root_thread):
    sessions = rooted_sessions(home, root_thread, 0)
    result = {
        "root_rollout_found": bool(sessions),
        "root_rollout_count": len(sessions),
        "spawn_calls_observed": 0,
        "agent_tool_calls": {},
        "root_event_types": {},
        "spawn_role_argument_fields": {},
        "named_role_spawn_outputs": [],
        "child_rollout_count": 0,
        "child_session_metadata_keys": {},
        "child_source_shape": {},
        "notes": [],
    }
    if not sessions:
        result["notes"].append("Root rollout missing or not stored under CODEX_HOME/sessions")
        return result
    records = []
    for path in sessions:
        try:
            records.extend(json_lines(path.read_bytes()))
        except OSError:
            result["notes"].append("Could not read one root rollout file")
    result["root_event_types"] = dict(collections.Counter(
        str(x.get("type", "UNKNOWN")) for x in records))
    counters = collections.Counter()
    argument_shapes = collections.Counter()
    for event in records:
        payload = event.get("payload", {})
        if event.get("type") != "response_item" or not isinstance(payload, dict):
            continue
        tool = classify_call(payload)
        if not tool:
            continue
        counters[tool] += 1
        if tool == "spawn_agent":
            result["spawn_calls_observed"] += 1
            raw = payload.get("arguments")
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, ValueError):
                args = {}
            if isinstance(args, dict):
                for key in ("agent_type", "agent_name", "role", "task_name"):
                    if key in args:
                        # Field present only: do not disclose raw argument values.
                        argument_shapes[key] += 1
    result["agent_tool_calls"] = dict(counters)
    result["spawn_role_argument_fields"] = dict(argument_shapes)
    verified_candidates = parse_spawn_calls(records)
    result["named_role_spawn_outputs"] = sorted(verified_candidates)
    # Inspect only whether recent child rollouts exist and their sanitized metadata structure.
    folder = home / "sessions"
    if folder.exists():
        child_keys = collections.Counter()
        source_shapes = collections.Counter()
        count = 0
        for path in folder.rglob("*.jsonl"):
            if root_thread in path.name:
                continue
            try:
                head = path.open("rb")
                with head:
                    lines = [head.readline() for _ in range(8)]
            except OSError:
                continue
            metas = [x.get("payload", {}) for x in json_lines(b"".join(lines))
                     if x.get("type") == "session_meta"]
            if not metas:
                continue
            meta = metas[0]
            if isinstance(meta, dict):
                source = meta.get("source")
                if isinstance(source, dict):
                    if any(v in json.dumps(source).lower()
                           for v in ("subagent", "thread_spawn", "sub_agent")):
                        count += 1
                        child_keys.update(meta.keys())
                        source_shapes.update(source.keys())
        result["child_rollout_count"] = count
        result["child_session_metadata_keys"] = dict(child_keys)
        result["child_source_shape"] = dict(source_shapes)
    if result["spawn_calls_observed"] == 0:
        result["notes"].append("No native spawn_agent call found in root response_item rollout")
    if result["spawn_calls_observed"] > 0 and not verified_candidates:
        result["notes"].append("Spawn calls exist but exact named-role + successful child-ID evidence not paired")
    if verified_candidates and result["child_rollout_count"] == 0:
        result["notes"].append("Named-role spawns found, but no child session metadata found in this CODEX_HOME")
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description="Safe four-agent diagnostic (no raw logs)")
    parser.add_argument("--root-thread", required=True)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    home = Path(args.codex_home or os.environ.get("CODEX_HOME") or
                Path.home() / ".codex").expanduser().resolve()
    output = diagnostic(home, args.root_thread)
    payload = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    print(payload, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    return 0 if output["root_rollout_found"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
