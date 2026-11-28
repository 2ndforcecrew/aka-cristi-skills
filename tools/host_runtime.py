"""Authorized host CLI runtime for CHEF. No inferred or simulated runtime PASS.

Structured host traces only. Safe mode never auto-grants tool privileges;
hosts with no enforceable read-only mode remain blocked by default. Do not
use this runner with production credentials/data or as a substitute for OS sandbox.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from tools.fs_safety import checked_path

HOSTS = {
    "workbuddy": "codebuddy",
    "claude": "claude",
    "gemini": "gemini",
    "opencode": "opencode",
    "hermes": "hermes",
}
ROLES = ("research", "coding", "qa", "automation", "factory", "studio")
MAX_OUTPUT = 1024 * 1024
MAX_TEXT = 4096


def _safe_workspace(value):
    path = checked_path(Path(value).expanduser().absolute())
    if not path.is_dir():
        raise ValueError("Workspace must exist")
    return path


def _role_prompt(role, objective):
    if role not in ROLES or not isinstance(objective, str) or not 1 <= len(objective.strip()) <= 10000:
        raise ValueError("Invalid role or objective")
    return (
        f"CHEF / {role.upper()} — read-only research and planning invocation. "
        "Do not edit or create files, run arbitrary commands, deploy, publish, "
        "change permissions or access secret material. Return concrete evidence "
        "from this isolated workspace and explicitly state unverified items. "
        "This is one independent host session, NOT proof of native child-agent spawn.\n\n"
        + objective
    )


def build(host, role, objective, workspace, *, allow_risky_host=False):
    """Build argv WITHOUT shell. Preview never executes a CLI or spends quota."""
    if host not in HOSTS:
        raise ValueError("Unsupported host")
    project = _safe_workspace(workspace)
    prompt = _role_prompt(role, objective)
    # WorkBuddy requires -y for permissioned tools in headless mode; Hermes
    # can attach a gateway with toolsets from user configuration. Neither is
    # auto-authorized in default safe mode.
    if host in ("workbuddy", "hermes") and not allow_risky_host:
        return {"host": host, "role": role, "status": "HOST_PERMISSION_REVIEW_REQUIRED",
                "reason": "Read-only tool policy cannot be independently enforced by this adapter",
                "executable": HOSTS[host], "cwd": str(project),
                "command": None, "mode": "NOT_RUN"}
    if host == "workbuddy":
        cmd = ["codebuddy", "--print", "--output-format", "json",
               "--permission-mode", "plan",
               "--disallowedTools", "Bash,Write,Edit,MultiEdit,NotebookEdit",
               "-y"]
        stdin = prompt
    elif host == "claude":
        cmd = ["claude", "--print", "--output-format", "json",
               "--permission-mode", "plan", "--max-turns", "6"]
        stdin = prompt
    elif host == "gemini":
        cmd = ["gemini", "--prompt", prompt, "--output-format", "stream-json",
               "--approval-mode", "plan"]
        stdin = None
    elif host == "opencode":
        cmd = ["opencode", "run", "--agent", "plan", "--format", "json",
               "--archived", prompt]
        stdin = None
    else:
        cmd = ["hermes", "chat", "--oneshot", "--query-file", "-",
               "--format", "stream-json"]
        stdin = prompt
    return {"host": host, "role": role, "status": "READY_FOR_EXPLICIT_AUTHORIZATION",
            "command": cmd, "stdin": stdin, "cwd": str(project),
            "permission_boundary": "HOST_POLICY_NOT_OS_SANDBOX",
            "native_subagent": "NOT_VERIFIED"}


def _structured(stdout, host, exit_code):
    """Never turn a plain text assertion into a completed host invocation."""
    try:
        if host in ("claude", "workbuddy"):
            obj = json.loads(stdout)
            if not isinstance(obj, dict):
                raise ValueError("Not an object")
            sid = obj.get("session_id")
            message = obj.get("result")
            bad = obj.get("is_error", False)
            if obj.get("type") not in (None, "result"):
                raise ValueError("Wrong result event")
            success = exit_code == 0 and bad is False and isinstance(message, str) and bool(message.strip())
        else:
            items = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            if not items or not all(isinstance(x, dict) for x in items):
                raise ValueError("No JSONL result")
            sid = None
            message = None
            success = False
            if host == "hermes":
                final = [x for x in items if x.get("type") == "result"]
                if final:
                    end = final[-1]
                    sid = end.get("session_id")
                    message = end.get("text")
                    success = exit_code == 0 and end.get("exit_code") == 0 and not end.get("error")
            elif host == "gemini":
                init = [x for x in items if x.get("type") == "init"]
                final = [x for x in items if x.get("type") == "result"]
                if init and final:
                    sid = init[0].get("session_id")
                    end = final[-1]
                    message = end.get("response")
                    if not isinstance(message, str):
                        chunks = [x.get("content") for x in items
                                  if x.get("type") == "message" and x.get("role") == "assistant"]
                        message = "\n".join(c for c in chunks if isinstance(c, str))
                    success = exit_code == 0 and not end.get("error") and end.get("status") not in ("error", "failed")
            elif host == "opencode":
                finish = [x for x in items if x.get("type") == "step_finish"]
                chunks = [x.get("part", {}) for x in items if x.get("type") == "text"]
                if finish:
                    sid = finish[-1].get("part", {}).get("sessionID")
                    message = "\n".join(c.get("text", "") for c in chunks if isinstance(c, dict))
                    success = exit_code == 0 and finish[-1].get("part", {}).get("reason") in ("stop", "completed")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{5,128}", sid):
            return {"status": "INCONCLUSIVE", "reason": "NO_ATTRIBUTABLE_SESSION"}
        if not success or not isinstance(message, str) or not message.strip():
            return {"status": "FAIL" if exit_code else "INCONCLUSIVE",
                    "reason": "INCOMPLETE_OR_UNRECOGNIZED_RESULT"}
        return {"status": "COMPLETED", "session_id": sid, "output": message[:MAX_TEXT],
                "output_truncated": len(message) > MAX_TEXT}
    except (TypeError, ValueError, AttributeError):
        return {"status": "INCONCLUSIVE", "reason": "UNRECOGNIZED_HOST_TRACE"}


def _terminate(process):
    if process.poll() is not None:
        return
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()
    else:
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()


def run(host, role, objective, workspace, *, consent=False, allow_risky_host=False,
        timeout=180):
    if not 10 <= timeout <= 900:
        raise ValueError("Timeout outside safe bounds")
    spec = build(host, role, objective, workspace, allow_risky_host=allow_risky_host)
    preview = {"host": host, "role": role, "status": spec["status"],
               "cwd": spec["cwd"], "runtime_evidence": "NOT_RUN"}
    if spec["command"] is None:
        preview["reason"] = spec["reason"]
        return preview
    # No prompt in returned preview; keep sensitive prompts out of command logs.
    redacted_prompt = _role_prompt(role, objective)
    preview["argv_preview"] = [
        "<PROMPT_REDACTED>" if arg == redacted_prompt else arg
        for arg in spec["command"]
    ]
    if not consent:
        return preview
    binary = shutil.which(HOSTS[host])
    if not binary:
        return {**preview, "status": "NOT_RUN", "reason": "HOST_CLI_NOT_FOUND"}
    argv = [binary, *spec["command"][1:]]
    process = None
    try:
        process = subprocess.Popen(
            argv, cwd=spec["cwd"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            env={**os.environ, "CODEBUDDY_CODE_DISABLE_BACKGROUND_TASKS": "1"},
        )
        stdout, stderr = process.communicate(input=spec["stdin"], timeout=timeout)
        if not isinstance(stdout, str):
            return {**preview, "status": "INCONCLUSIVE", "reason": "HOST_STDOUT_UNREADABLE"}
        if len(stdout.encode("utf-8", errors="replace")) > MAX_OUTPUT:
            return {**preview, "status": "FAIL", "reason": "HOST_OUTPUT_TOO_LARGE"}
        parsed = _structured(stdout, host, process.returncode)
        return {"host": host, "role": role, **parsed,
                "runtime_evidence": "CLI_TRACE" if parsed["status"] == "COMPLETED" else "UNVERIFIED",
                "native_subagent": "NOT_VERIFIED", "sandbox": "HOST_POLICY_ONLY",
                "exit_code": process.returncode}
    except subprocess.TimeoutExpired:
        _terminate(process)
        process.communicate()
        return {**preview, "status": "FAIL", "reason": "HOST_TIMEOUT"}
    except OSError:
        return {**preview, "status": "FAIL", "reason": "HOST_PROCESS_ERROR"}
    except UnicodeError:
        return {**preview, "status": "INCONCLUSIVE", "reason": "HOST_ENCODING_ERROR"}


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only host CLI role probe: explicit quota consent only")
    p.add_argument("--host", choices=sorted(HOSTS), required=True)
    p.add_argument("--role", choices=ROLES, required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--allow-live", action="store_true",
                   help="explicitly authorize one real model query and potential quota cost")
    p.add_argument("--allow-host-permissions", action="store_true",
                   help="separate high-risk opt-in for WorkBuddy/Hermes: host tools may have broad access")
    opts = p.parse_args(argv)
    try:
        result = run(opts.host, opts.role, opts.prompt, opts.workspace,
                     consent=opts.allow_live, allow_risky_host=opts.allow_host_permissions,
                     timeout=opts.timeout)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] in ("READY_FOR_EXPLICIT_AUTHORIZATION", "COMPLETED") else 2
    except (ValueError, OSError):
        print(json.dumps({"status": "FAIL", "reason": "INVALID_OR_UNSAFE_INPUT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
