"""Run a real Codex Skill call in a read-only sandbox; no simulated PASS."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

SKILLS = ("verified-change-loop", "feature-journey-map", "skill-evaluation-gate")


def parse_events(output):
    events = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            pass
    return events


def assess(events, name, nonce, exit_code):
    completed = any(x.get("type") == "turn.completed" for x in events)
    failed = any(x.get("type") in ("turn.failed", "error") for x in events)
    messages = [x.get("item", {}).get("text", "") for x in events
                if x.get("type") == "item.completed"
                and x.get("item", {}).get("type") == "agent_message"]
    answer = "\n".join(s for s in messages if isinstance(s, str))
    skill_read = case_read = False
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if item.get("type") != "command_execution" or item.get("exit_code") != 0:
            continue
        command = item.get("command", "")
        if not isinstance(command, str) or not re.search(
                r"\b(?:cat|sed|head|tail|type|Get-Content|rg)\b", command, re.I):
            continue
        command = command.replace("\\", "/")
        skill_read |= bool(re.search(r"(?:^|/)" + re.escape(name) + r"/SKILL\.md", command))
        case_read |= bool(re.search(r"(?:^|[\s/])CASE\.md\b", command))
    checks = {
        "completed_real_agent_turn": completed and not failed and exit_code == 0,
        "read_skill_file": skill_read,
        "read_case_fixture": case_read,
        "responded_with_unknown_fixture_nonce": nonce in answer,
        "reported_live_app_NOT_RUN": bool(re.search(r"\bNOT_RUN\b", answer)),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks, "agent_answer": answer[:4000],
            "events": len(events)}


def run(name, codex="codex", timeout=180, root=None):
    if name not in SKILLS:
        raise ValueError("unsupported Skill")
    root = root or Path(__file__).resolve().parents[1]
    source = (root / "skills" / name / "SKILL.md").resolve(strict=True)
    result = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "skill": name, "status": "NOT_RUN", "invoked": False}
    exe = shutil.which(codex)
    if not exe:
        result["reason"] = "Codex CLI not installed in executing environment"
        return result
    try:
        login = subprocess.run([exe, "login", "status"], capture_output=True,
                               timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        result["reason"] = "Could not check Codex CLI authentication"
        return result
    if login.returncode:
        result["reason"] = "Codex CLI not authenticated in this environment"
        return result

    with tempfile.TemporaryDirectory(prefix="aka-agent-activation-") as tmp:
        workspace = Path(tmp).resolve()
        target = workspace / ".agents" / "skills" / name
        target.mkdir(parents=True)
        (target / "SKILL.md").write_bytes(source.read_bytes())
        nonce = "AKA-PROBE-" + uuid.uuid4().hex[:12].upper()
        (workspace / "CASE.md").write_text(
            "# Synthetic incident\n\nCase ID: " + nonce + "\n\n"
            "User reports the login dashboard sometimes shows a stale empty state. "
            "No running app, browser, server, or reproducible environment is provided. "
            "Analyze next steps but do not claim any real defect was reproduced. "
            "Mark behavior verification NOT_RUN.\n", encoding="utf-8")
        prompt = (
            "Explicitly use $" + name + ". Read the installed SKILL.md and CASE.md "
            "in this workspace, then analyze the case using the Skill's method. "
            "Quote the exact Case ID from CASE.md in your final answer. Mark "
            "unperformed live behavior as NOT_RUN. Provide actionable verification "
            "steps. Do not modify files, use network, or invent test results.")
        args = [exe, "exec", "--json", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check",
                "--cd", str(workspace), prompt]
        result["invoked"] = True
        try:
            proc = subprocess.run(args, cwd=workspace, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {**result, "status": "FAIL", "reason": "Agent timed out"}
        except OSError:
            return {**result, "status": "FAIL", "reason": "Agent execution failed"}
        result.update(assess(parse_events(proc.stdout), name, nonce, proc.returncode))
        result["exit_code"] = proc.returncode
        result["reason"] = ("Observed agent loading Skill and producing valid behavior"
                            if result["status"] == "PASS"
                            else "Agent trace did not prove all required assertions")
        # Never persist raw JSONL, which may contain private host context.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Live Codex Skill invocation test")
    parser.add_argument("--skill", choices=SKILLS, default=SKILLS[0])
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not 10 <= args.timeout <= 900:
        parser.error("timeout must be 10..900")
    try:
        result = run(args.skill, args.codex_bin, args.timeout)
    except (OSError, ValueError) as exc:
        result = {"status": "FAIL", "reason": type(exc).__name__}
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(output, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    return 0 if result["status"] == "PASS" else 2 if result["status"] == "NOT_RUN" else 1


if __name__ == "__main__":
    sys.exit(main())
