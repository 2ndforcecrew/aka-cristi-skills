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


def decode_output(raw):
    """Codex JSONL is UTF-8, not the Windows console ANSI code page."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw


def json_lines(raw):
    records = []
    for line in decode_output(raw).splitlines():
        try:
            x = json.loads(line)
            if isinstance(x, dict):
                records.append(x)
        except (TypeError, ValueError):
            pass
    return records


def find_role_tomls(codex_home, role_source=None):
    found = {}
    for filename, role in zip(ROLE_FILES, ROLES):
        path = (Path(role_source) if role_source else codex_home / "agents") / (filename + ".toml")
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


def object_value(raw):
    """Decode only structured JSON objects; never mine IDs from prose."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    return raw if isinstance(raw, dict) else None


def spawn_evidence(events):
    calls, outputs = {}, {}
    ambiguous = set()
    for event in events:
        payload = event.get("payload", event)
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "response_item" and isinstance(payload.get("payload"), dict):
            payload = payload["payload"]
        call_id = payload.get("call_id")
        if not isinstance(call_id, str) or not call_id:
            continue
        if payload.get("type") == "function_call" and str(payload.get("name", "")).split(".")[-1] == "spawn_agent":
            args = object_value(payload.get("arguments"))
            if not args:
                continue
            role = args.get("agent_type")
            if role not in ROLES:
                continue
            if call_id in calls:
                ambiguous.add(call_id)
            calls[call_id] = role
        elif payload.get("type") == "function_call_output":
            if call_id in outputs:
                ambiguous.add(call_id)
            outputs[call_id] = object_value(payload.get("output"))
    attempts = {role: False for role in ROLES}
    proof = {}
    for call_id, role in calls.items():
        attempts[role] = True
        if call_id in ambiguous:
            continue
        output = outputs.get(call_id)
        if not output or output.get("error") or output.get("success") is False or output.get("status") not in (None, "success", "completed"):
            continue
        child = output.get("agent_id")
        if not isinstance(child, str) or not UUID_RE.fullmatch(child):
            continue
        if role in proof:
            # More than one successful child for a requested role is ambiguous.
            proof[role] = None
        else:
            proof[role] = {"child_thread_id": child, "parent_call_id": call_id}
    proof = {role: info for role, info in proof.items() if info is not None}
    counts = {}
    for info in proof.values():
        counts[info["child_thread_id"]] = counts.get(info["child_thread_id"], 0) + 1
    proof = {role: info for role, info in proof.items() if counts[info["child_thread_id"]] == 1}
    return attempts, proof


def parse_spawn_calls(events):
    """Exact named role, paired call ID and structured successful agent_id."""
    return spawn_evidence(events)[1]


def recent_metadata(meta, started):
    if not started:
        return True  # Offline diagnostics: age is not asserted.
    try:
        stamp = datetime.fromisoformat(meta["timestamp"].replace("Z", "+00:00")).timestamp()
        return started - 120 <= stamp <= time.time() + 120
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def child_assessment(codex_home, role, child_id, started, parent_thread):
    stages = {"ROLE_SELECTED": False, "CHILD_COMPLETED": False}
    files = rooted_sessions(codex_home, child_id, started)
    if len(files) != 1:
        return stages
    try:
        records = json_lines(files[0].read_bytes())
    except OSError:
        return stages
    metadata = [x.get("payload") for x in records if x.get("type") == "session_meta"]
    if len(metadata) != 1 or not isinstance(metadata[0], dict):
        return stages
    meta = metadata[0]
    if meta.get("id") != child_id or not recent_metadata(meta, started):
        return stages
    source = meta.get("source")
    source = source.get("subagent") if isinstance(source, dict) else None
    spawn = source.get("thread_spawn") if isinstance(source, dict) else None
    if not isinstance(spawn, dict):
        return stages
    # Optional top-level duplicates must agree; role aliases mirror Codex serde.
    parents = [spawn.get("parent_thread_id")]
    roles = [spawn.get("agent_role", spawn.get("agent_type"))]
    if "parent_thread_id" in meta:
        parents.append(meta["parent_thread_id"])
    for key in ("agent_role", "agent_type"):
        if key in meta:
            roles.append(meta[key])
        if key in spawn:
            roles.append(spawn[key])
    if not all(value == parent_thread for value in parents) or not all(value == role for value in roles):
        return stages
    stages["ROLE_SELECTED"] = True
    # The terminal event is required. A tool-call preamble is not completion.
    completions = [x.get("payload", {}) for x in records if x.get("type") == "event_msg"
                   and isinstance(x.get("payload"), dict)
                   and x["payload"].get("type") in ("task_complete", "turn_complete")]
    if completions:
        last = completions[-1]
        reply = last.get("last_agent_message")
        stages["CHILD_COMPLETED"] = bool(last.get("turn_id") and not last.get("error")
                                         and isinstance(reply, str) and reply.strip())
    return stages


def inspect_child(codex_home, role, child_id, started, parent_thread=None):
    """Compatibility wrapper; missing parent evidence always fails closed."""
    stages = child_assessment(codex_home, role, child_id, started, parent_thread)
    return all(stages.values())


def evaluate(rollout, codex_home, started, root_thread, exit_code, completed):
    empty = {role: {"SPAWN_ATTEMPT": False, "SPAWN_SUCCESS": False,
                   "ROLE_SELECTED": False, "CHILD_COMPLETED": False, "ROLE_PASS": False}
             for role in ROLES}
    result = {"status": "INCONCLUSIVE", "roles": {role: "NOT_VERIFIED" for role in ROLES},
              "role_stages": empty, "confirmed_child_threads": {}}
    root_files = rooted_sessions(codex_home, root_thread, started)
    if len(root_files) != 1:
        return {**result, "reason": "Missing or ambiguous attributable root rollout"}
    try:
        records = json_lines(root_files[0].read_bytes())
    except OSError:
        return {**result, "reason": "Cannot read attributable root rollout"}
    metas = [x.get("payload") for x in records if x.get("type") == "session_meta"]
    if len(metas) != 1 or not isinstance(metas[0], dict) or metas[0].get("id") != root_thread:
        return {**result, "reason": "Root metadata does not identify requested thread"}
    attempts, calls = spawn_evidence(records)
    for role in ROLES:
        stages = empty[role]
        stages["SPAWN_ATTEMPT"] = attempts[role]
        info = calls.get(role)
        stages["SPAWN_SUCCESS"] = info is not None
        if info:
            stages.update(child_assessment(codex_home, role, info["child_thread_id"], started, root_thread))
        stages["ROLE_PASS"] = all(stages[key] for key in
            ("SPAWN_ATTEMPT", "SPAWN_SUCCESS", "ROLE_SELECTED", "CHILD_COMPLETED"))
        if stages["ROLE_PASS"]:
            result["roles"][role] = "PASS"
            result["confirmed_child_threads"][role] = info["child_thread_id"]
    ok = completed and exit_code == 0 and all(x == "PASS" for x in result["roles"].values())
    result["status"] = "PASS" if ok else "INCONCLUSIVE"
    result["reason"] = "All 4 exact-role child threads and completed replies verified" if ok else "Named-role parent/child/completion evidence incomplete"
    return result


def failure_category(stderr):
    """Only fixed diagnostic categories may leave local process memory."""
    text = decode_output(stderr).lower()
    for needles, category in (
        (("unexpected argument", "unrecognized option"), "CLI_OPTION_REJECTED"),
        (("failed to load config", "error loading config", "invalid config", "unknown field"), "CONFIGURATION_REJECTED"),
        (("not logged in", "unauthorized", "authentication"), "AUTHORIZATION_FAILED"),
        (("connection refused", "network", "dns", "timed out"), "NETWORK_FAILURE"),
        (("permission denied", "operation not permitted"), "PERMISSION_DENIED"),
    ):
        if any(needle in text for needle in needles):
            return category
    return "CLI_NONZERO_UNCLASSIFIED"


def run(timeout=600, codex_bin="codex", codex_home=None, role_source=None):
    base = Path(codex_home or os.environ.get("CODEX_HOME") or
                Path.home() / ".codex").expanduser().resolve()
    result = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "status": "NOT_RUN", "invoked": False,
              "roles": {x: "NOT_RUN" for x in ROLES}}
    exe = shutil.which(codex_bin)
    if not exe:
        result["reason"] = "Codex CLI missing on this machine"
        return result
    try:
        version = subprocess.run([exe, "--version"], capture_output=True, timeout=10, check=False)
        match = re.fullmatch(r"codex-cli [0-9A-Za-z.+_-]+", decode_output(version.stdout).strip())
        result["codex_cli_version"] = match.group(0) if version.returncode == 0 and match else "UNKNOWN"
    except (OSError, subprocess.TimeoutExpired):
        result["codex_cli_version"] = "UNKNOWN"
    found = find_role_tomls(base, role_source)
    result["installed_roles"] = found
    if not all(x == "PASS" for x in found.values()):
        result["reason"] = "Install all 4 validated native role definitions first"
        return result
    try:
        auth = subprocess.run([exe, "login", "status"], capture_output=True,
                              timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        result["reason"] = "Cannot inspect Codex CLI authentication"
        return result
    if auth.returncode:
        result["reason"] = "Codex CLI not logged in on this machine"
        return result
    with tempfile.TemporaryDirectory(prefix="aka-chef-4agents-") as temp:
        wd = Path(temp).resolve()
        overrides = []
        if role_source:
            staged = wd / "role-profiles"
            staged.mkdir()
            for filename, role in zip(ROLE_FILES, ROLES):
                source = Path(role_source) / (filename + ".toml")
                target = staged / source.name
                target.write_bytes(source.read_bytes())
                overrides += ["-c", "agents." + role + ".config_file=" + json.dumps(str(target))]
            result["role_configuration"] = "TEMPORARY_PER_PROCESS_OVERRIDES"
        else:
            result["role_configuration"] = "EXISTING_HOST_INSTALLATION"
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
                   "-c", "features.unified_exec=false", *overrides, prompt]
        result["invoked"] = True
        try:
            proc = subprocess.run(command, cwd=wd, capture_output=True,
                                  timeout=timeout, check=False)
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
        if proc.returncode != 0:
            assessment["status"] = "FAIL"
            assessment["failure_category"] = failure_category(proc.stderr)
            assessment["reason"] = "Codex CLI exited unsuccessfully; no runtime PASS is possible"
        return {**result, **assessment, "invoked": True,
                "root_thread_id": root_thread, "exit_code": proc.returncode,
                "agent_completion_observed": completed,
                "privacy": "No raw rollout or authentication contents copied into report"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Strict 4-native-Agent Codex E2E")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--role-source", type=Path, help="stage validated public role TOMLs in a temporary workspace; no host install")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not 30 <= args.timeout <= 1800:
        parser.error("--timeout outside allowed 30..1800 seconds")
    result = run(args.timeout, args.codex_bin, args.codex_home, args.role_source)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0 if result["status"] == "PASS" else 2 if result["status"] in (
        "NOT_RUN", "INCONCLUSIVE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
