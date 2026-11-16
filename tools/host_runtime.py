"""Bounded, opt-in, read-only *host turns* for CHEF.

This is NOT proof of a native child-agent spawn. Official headless command
interfaces are supported conservatively. No dynamic shell or arbitrary command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from tools.fs_safety import checked_path

HOST_BIN = {"claude": "claude", "gemini": "gemini", "opencode": "opencode"}
UNVERIFIED = ("workbuddy", "hermes", "generic", "chatgpt")
ROLES = {
    "factory": "Prepare a concrete, testable patch proposal, without changing files.",
    "studio": "Review user journey, visual direction, accessibility and product intent without changing files.",
    "qa": "Independently review delivered evidence and regressions without changing files.",
}
MAX_PROMPT = 20000
MAX_LOG = 1024 * 1024
MAX_MESSAGE = 30000


def command(host: str, prompt: str) -> list[str]:
    """Allowlisted CLI args, always in host read-only/plan mode."""
    if host not in HOST_BIN:
        raise ValueError("No verified headless CLI adapter for host")
    if host == "claude":
        return ["claude", "-p", prompt, "--output-format", "json",
                "--permission-mode", "plan", "--max-turns", "5"]
    if host == "gemini":
        return ["gemini", "-p", prompt, "--output-format", "stream-json",
                "--approval-mode", "plan"]
    return ["opencode", "run", "--agent", "plan", "--format", "json", prompt]


def _objects(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return [obj]
    except ValueError:
        pass
    events = []
    for line in text.splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                events.append(obj)
        except ValueError:
            continue
    return events[:2000]


def parse(host: str, raw: bytes, exit_code: int) -> dict:
    """Evidence: distinct host session/turn only, not child-agent ancestry."""
    if len(raw) > MAX_LOG:
        return {"status": "INCONCLUSIVE", "reason": "OUTPUT_TOO_LARGE"}
    events = _objects(raw)
    message = ""
    session = None
    ended = False
    rejected = False
    if host == "claude":
        result = next((e for e in events if e.get("type") == "result"), {})
        message = result.get("result", "")
        session = result.get("session_id")
        ended = result.get("subtype") == "success" and result.get("is_error") is False
        rejected = result.get("is_error") is True
    elif host == "gemini":
        for event in events:
            if event.get("type") == "init":
                session = event.get("session_id")
            if event.get("type") == "result":
                ended = event.get("status") in ("success", "completed") and not event.get("error")
                message = event.get("response", "")
                if not message and isinstance(event.get("result"), str):
                    message = event["result"]
            if event.get("type") == "error":
                rejected = True
    elif host == "opencode":
        parts = []
        for event in events:
            session = session or event.get("sessionID")
            part = event.get("part") if isinstance(event.get("part"), dict) else {}
            if event.get("type") == "text" and isinstance(part.get("text"), str):
                parts.append(part["text"])
            if event.get("type") == "step_finish":
                ended = part.get("reason") in ("stop", "end_turn", "end")
            if event.get("type") == "error":
                rejected = True
        message = "\n".join(parts)
    else:
        return {"status": "NOT_RUN", "reason": "UNSUPPORTED_HOST"}
    if not isinstance(message, str):
        message = ""
    if not isinstance(session, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", session):
        session = None
    ok = (exit_code == 0 and ended and bool(message.strip()) and bool(session)
          and not rejected)
    status = "COMPLETED" if ok else (
        "FAILED" if exit_code != 0 or rejected else "INCONCLUSIVE")
    return {
        "status": status,
        "reason": "HOST_TURN_OBSERVED" if ok else "HOST_TURN_NOT_CORRELATED",
        "output": message[:MAX_MESSAGE],
        "thread_ids": [session] if ok else [],
        "host_session_id": session,
        "native_child_agents": "NOT_VERIFIED",
        "host_event_count": len(events),
        "stdout_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _launch(argv: list[str], workspace: Path, timeout: int):
    """Kill whole process tree on timeout, including non-tty child workers."""
    process = None
    try:
        process = subprocess.Popen(
            argv, cwd=workspace, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=os.name != "nt",
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP
                           if os.name == "nt" else 0),
        )
        out, err = process.communicate(timeout=timeout)
        return {"status": "EXITED", "code": process.returncode, "stdout": out, "stderr": err}
    except subprocess.TimeoutExpired:
        if process is not None:
            if os.name == "nt":
                try:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, timeout=10, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
            process.communicate()
        return {"status": "TIMEOUT"}
    except OSError:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
        return {"status": "SPAWN_ERROR"}


def run(host: str, role: str, prompt: str, workspace: Path, timeout=300,
        *, authorized=False) -> dict:
    """Never call a model unless the caller explicitly authorizes inference."""
    if role not in ROLES:
        raise ValueError("Unknown CHEF role")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT:
        raise ValueError("Invalid prompt")
    if not 1 <= timeout <= 1800:
        raise ValueError("Timeout must be 1..1800 seconds")
    workspace = checked_path(Path(workspace).expanduser().absolute())
    if not workspace.is_dir():
        raise ValueError("Existing workspace required")
    if host not in HOST_BIN:
        return {"host": host, "status": "NOT_RUN", "reason": "NO_VERIFIED_HEADLESS_ADAPTER",
                "native_child_agents": "NOT_VERIFIED"}
    binary = shutil.which(HOST_BIN[host])
    if not binary:
        return {"host": host, "status": "NOT_RUN", "reason": "HOST_CLI_MISSING",
                "native_child_agents": "NOT_VERIFIED"}
    if not authorized:
        return {"host": host, "status": "NOT_RUN", "reason": "INFERENCE_CONSENT_REQUIRED",
                "native_child_agents": "NOT_VERIFIED"}
    text = (ROLES[role] + "\n\nCHEF host turn; do not call tools that write,"
            " publish, deploy, spend money, modify credentials, or launch child agents."
            " Return concrete evidence, not a fabricated PASS.\n\nTASK:\n" + prompt)
    outcome = _launch(command(host, text), workspace, timeout)
    if outcome["status"] != "EXITED":
        return {"host": host, "status": "FAILED", "reason": outcome["status"],
                "native_child_agents": "NOT_VERIFIED"}
    result = parse(host, outcome["stdout"], outcome["code"])
    return {"host": host, **result, "exit_code": outcome["code"],
            "scope": "read_only_plan", "model_invocation": "ATTEMPTED"}


def main(argv=None):
    p = argparse.ArgumentParser(description="CHEF host turn, no native child-spawn claims")
    p.add_argument("--host", required=True)
    p.add_argument("--role", choices=tuple(ROLES), required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--authorize-inference", action="store_true",
                   help="opt in to a potentially paid model request")
    args = p.parse_args(argv)
    try:
        result = run(args.host, args.role, args.prompt, args.workspace,
                     args.timeout, authorized=args.authorize_inference)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "COMPLETED" else 2
    except (OSError, ValueError):
        print(json.dumps({"status": "FAIL", "reason": "INVALID_INPUT"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
