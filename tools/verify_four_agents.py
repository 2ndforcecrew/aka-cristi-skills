"""Real four-role Codex subagent acceptance probe.

Strictly refuses to call a prose claim proof of spawning. Requires a
signed-in Codex CLI and attributable rollout thread evidence.
This code does not simulate or impersonate Codex agents.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROLES = ("aka_research", "aka_coding", "aka_qa", "aka_automation")
ROLE_FILES = ("research", "coding", "qa", "automation")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def json_lines(raw):
    records = []
    for line in raw.splitlines():
        try:
            x = json.loads(line)
            if isinstance(x, dict):
                records.append(x)
        except (TypeError, ValueError):
            pass
    return records


def find_role_tomls(codex_home):
    found = {}
    for filename, role in zip(ROLE_FILES, ROLES):
        path = codex_home / "agents" / (filename + ".toml")
        if not path.is_file() or path.is_symlink():
            found[role] = "NOT_INSTALLED"
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            found[role] = "PASS" if (data.get("name") == role
                and data.get("description") and data.get("developer_instructions")
                ) else "FAIL"
        except (OSError, ValueError, UnicodeError):
            found[role] = "FAIL"
    return found


def rooted_sessions(codex_home, thread_id, started):
    """Read only specifically matching current-session rollout files.

    This requires persisted Codex session logs; do not run --ephemeral.
    """
    folder = codex_home / "sessions"
    if not folder.exists() or not UUID_RE.fullmatch(thread_id or ""):
        return []
    candidates = []
    for path in folder.rglob("*.jsonl"):
        if thread_id not in path.name:
            continue
        try:
            if path.stat().st_mtime >= started - 120:
                candidates.append(path)
        except OSError:
            pass
    return candidates


def parse_spawn_calls(events):
    """Require actual machine events, not reported claims in agent messages."""
    calls = {}
    outputs = {}
    for x in events:
        payload = x.get("payload", x)
        if not isinstance(payload, dict):
            continue
        # Codex rollout uses {"type":"response_item","payload":{...}}.
        if x.get("type") == "response_item" and isinstance(payload.get("payload"), dict):
            payload = payload["payload"]
        kind = payload.get("type")
        if kind == "function_call":
            tool = str(payload.get("name", "")).split(".")[-1]
            if tool != "spawn_agent":
                continue
            raw = payload.get("arguments", {})
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
            except ValueError:
                continue
            if not isinstance(args, dict):
                continue
            # task_name is a human label, NOT proof of custom agent selection.
            role = args.get("agent_type") or args.get("agent_name") or args.get("role")
            if isinstance(role, str) and role in ROLES and payload.get("call_id"):
                calls[payload["call_id"]] = role
        elif kind == "function_call_output" and payload.get("call_id"):
            outputs[payload["call_id"]] = str(payload.get("output", ""))
    proof = {}
    for call_id, role in calls.items():
        output = outputs.get(call_id, "")
        # A real successful spawn returns a child identifier.
        matched = UUID_RE.search(output)
        if matched and not re.search(r"\b(error|failed to spawn)\b", output, re.I):
            proof[role] = {"child_thread_id": matched.group(0), "parent_call_id": call_id}
    return proof


def inspect_child(codex_home, role, child_id, started):
    files = rooted_sessions(codex_home, child_id, started)
    for path in files:
        records = json_lines(path.read_text(encoding="utf-8", errors="replace"))
        metadata = [x.get("payload", {}) for x in records
                    if x.get("type") == "session_meta"]
        if not metadata:
            continue
        # Do not use a task label as evidence that the named TOML role loaded.
        agent_info = metadata[0].get("source", {})
        marker = json.dumps(agent_info, ensure_ascii=False)
        is_subagent = "subagent" in marker or "sub_agent" in marker or "thread_spawn" in marker
        # Custom role metadata varies across Codex builds. An explicit role is mandatory.
        role_selected = role in marker
        has_reply = any(x.get("type") == "response_item"
                        and x.get("payload", {}).get("type") in ("message", "agent_message")
                        and x.get("payload", {}).get("role") == "assistant"
                        for x in records)
        if is_subagent and role_selected and has_reply:
            return True
    return False


def evaluate(rollout, codex_home, started, root_thread, exit_code, completed):
    root_files = rooted_sessions(codex_home, root_thread, started)
    if not root_files:
        return {"status": "INCONCLUSIVE",
                "reason": "No attributable root rollout; CLI stdout alone may omit spawn events",
                "roles": {x: "NOT_VERIFIED" for x in ROLES}}
    records = []
    for path in root_files:
        records.extend(json_lines(path.read_text(encoding="utf-8", errors="replace")))
    calls = parse_spawn_calls(records)
    statuses = {}
    for role in ROLES:
        info = calls.get(role)
        statuses[role] = ("PASS" if info and inspect_child(
            codex_home, role, info["child_thread_id"], started)
            else "NOT_VERIFIED")
    ok = completed and exit_code == 0 and all(x == "PASS" for x in statuses.values())
    return {"status": "PASS" if ok else "INCONCLUSIVE",
            "roles": statuses,
            "confirmed_child_threads": {role: calls[role]["child_thread_id"]
                for role in ROLES if statuses[role] == "PASS"},
            "reason": ("All 4 custom-role child rollouts verified" if ok
                      else "Actual named-role spawn + child reply evidence incomplete")}


def run(timeout=600, codex_bin="codex", codex_home=None):
    base = Path(codex_home or os.environ.get("CODEX_HOME") or
                Path.home() / ".codex").expanduser().resolve()
    result = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "status": "NOT_RUN", "invoked": False,
              "roles": {x: "NOT_RUN" for x in ROLES}}
    exe = shutil.which(codex_bin)
    if not exe:
        result["reason"] = "Codex CLI missing on this machine"
        return result
    found = find_role_tomls(base)
    result["installed_roles"] = found
    if not all(x == "PASS" for x in found.values()):
        result["reason"] = "Install all 4 validated native role definitions first"
        return result
    try:
        auth = subprocess.run([exe, "login", "status"], capture_output=True,
                              text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        result["reason"] = "Cannot inspect Codex CLI authentication"
        return result
    if auth.returncode:
        result["reason"] = "Codex CLI not logged in on this machine"
        return result
    with tempfile.TemporaryDirectory(prefix="aka-chef-4agents-") as temp:
        wd = Path(temp).resolve()
        token = "CHEF-" + uuid.uuid4().hex[:10]
        (wd / "CASE.md").write_text(
            "# Synthetic project - " + token + "\n\n"
            "The dashboard intermittently shows an empty state after sign-in. "
            "No real app or credentials exist. An example utility adds duplicate "
            "event listeners, and a planned webhook requires safe retries. "
            "Do not modify files, invoke external APIs, or claim a live defect was reproduced.",
            encoding="utf-8")
        prompt = (
            "Run a real native multi-agent handoff. Spawn exactly one of EACH "
            "named custom Codex role aka_research, aka_coding, aka_qa, aka_automation, "
            "not generic workers and not role-label-only tasks. "
            "Have aka_research inspect CASE.md and summarize evidence; "
            "aka_coding propose a minimal reversible fix WITHOUT editing files; "
            "aka_qa independently review those findings and classify missing "
            "verification NOT_RUN; aka_automation draft an idempotent safe retry "
            "plan. Wait for all four actual spawned threads. "
            "In your final response report the actual worker/thread IDs. "
            "If native named role selection is unavailable, say BLOCKED "
            "and do not substitute generic agents. No external access.")
        started = time.time()
        command = [exe, "exec", "--json", "--sandbox", "read-only",
                   "--skip-git-repo-check", "-C", str(wd),
                   "-c", "features.multi_agent=true",
                   "-c", "features.unified_exec=false", prompt]
        result["invoked"] = True
        try:
            proc = subprocess.run(command, cwd=wd, capture_output=True,
                                  text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {**result, "status": "FAIL", "reason": "Codex session timed out"}
        except OSError:
            return {**result, "status": "FAIL", "reason": "Codex failed to start"}
        events = json_lines(proc.stdout)
        root_thread = next((x.get("thread_id") for x in events
                            if x.get("type") == "thread.started"), None)
        completed = any(x.get("type") == "turn.completed" for x in events)
        assessment = evaluate(events, base, started, root_thread,
                              proc.returncode, completed)
        return {**result, **assessment, "invoked": True,
                "root_thread_id": root_thread, "exit_code": proc.returncode,
                "agent_completion_observed": completed,
                "privacy": "No raw rollout or authentication contents copied into report"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Strict 4-native-Agent Codex E2E")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not 30 <= args.timeout <= 1800:
        parser.error("--timeout outside allowed 30..1800 seconds")
    result = run(args.timeout, args.codex_bin, args.codex_home)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0 if result["status"] == "PASS" else 2 if result["status"] in (
        "NOT_RUN", "INCONCLUSIVE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
