"""CHEF runtime capability probes and explicitly authorized read-only host invocations.

A CLI process completing is not proof of a native subagent. No login, token reads,
automatic paid inference, repository modifications or host capability assumptions.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
from pathlib import Path

from tools.chef_dual_engine import run_codex
from tools.chef_handoff import plan
from tools.fs_safety import checked_path
from tools.universal_chef import HOSTS

EXECUTABLES = {
    "codex": "codex", "claude": "claude", "gemini": "gemini",
    "opencode": "opencode", "hermes": "hermes", "workbuddy": None,
    "generic": None,
}
LIVE_HOSTS = {"codex", "claude"}
MAX_OUTPUT = 64 * 1024


def probe(host, *, which=shutil.which, run=subprocess.run):
    if host not in HOSTS:
        raise ValueError("Unknown host")
    binary = EXECUTABLES[host]
    if binary is None:
        return {"host": host, "status": "UNSUPPORTED", "binary": "UNKNOWN",
                "live_runtime": "NOT_VERIFIED", "native_subagent": "NOT_VERIFIED",
                "reason": "No verified supported CLI executable for this host"}
    executable = which(binary)
    if executable is None:
        return {"host": host, "status": "NOT_INSTALLED", "binary": binary,
                "live_runtime": "NOT_RUN", "native_subagent": "NOT_RUN"}
    try:
        result = run([executable, "--version"], stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                     timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return {"host": host, "status": "TIMEOUT", "binary": binary,
                "live_runtime": "NOT_RUN", "native_subagent": "NOT_RUN"}
    except OSError:
        return {"host": host, "status": "ERROR", "binary": binary,
                "live_runtime": "NOT_RUN", "native_subagent": "NOT_RUN"}
    raw = result.stdout
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    version = re.search(r"(?<![\w.])\d+\.\d+\.\d+(?:[-+][\w.-]+)?", (raw or "")[:512])
    return {"host": host, "status": "DETECTED" if result.returncode == 0 else "ERROR",
            "binary": binary, "version": version.group(0) if version else None,
            "live_runtime": "NOT_RUN", "native_subagent": "NOT_RUN",
            "runtime_adapter": "READ_ONLY_EXPLICIT_CONSENT" if host in LIVE_HOSTS else "NOT_IMPLEMENTED"}


def _process(cmd, cwd, timeout):
    """No shell, no inherited stdin; kill process group on timeout."""
    if not 1 <= timeout <= 600:
        raise ValueError("timeout must be 1..600 seconds")
    kwargs = {
        "cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL, "text": True,
        "start_new_session": os.name == "posix",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = None
    try:
        process = subprocess.Popen(cmd, **kwargs)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10, check=False)
            process.kill()
            process.communicate()
            return {"status": "FAILED", "reason": "TIMEOUT"}
    except OSError:
        return {"status": "FAILED", "reason": "PROCESS_ERROR"}
    if process.returncode != 0:
        return {"status": "FAILED", "reason": "NONZERO_EXIT",
                "exit_code": process.returncode}
    # Keep raw model output out of logs, evidence and reports.
    if len(stdout) > MAX_OUTPUT:
        return {"status": "FAILED", "reason": "OVERSIZED_OUTPUT"}
    try:
        payload = json.loads(stdout)
    except (ValueError, TypeError):
        return {"status": "FAILED", "reason": "UNRECOGNIZED_HOST_OUTPUT"}
    if not isinstance(payload, dict):
        return {"status": "FAILED", "reason": "UNRECOGNIZED_HOST_OUTPUT"}
    return {"status": "OBSERVED", "payload": payload}


def invoke(host, role, objective, project, *, consent=False, timeout=120,
           which=shutil.which, runner=_process):
    """Real read-only CLI invocation. Does NOT claim native child Agent creation."""
    if host not in HOSTS or role not in ("factory", "studio", "qa"):
        raise ValueError("Unsupported host or role")
    if not consent:
        return {"host": host, "role": role, "status": "CONSENT_REQUIRED",
                "native_subagent": "NOT_RUN", "quota": "NOT_SPENT"}
    if host not in LIVE_HOSTS:
        return {"host": host, "role": role, "status": "UNSUPPORTED",
                "native_subagent": "NOT_RUN", "reason": "No verified CLI runner"}
    if not 1 <= timeout <= 600:
        raise ValueError("timeout must be 1..600 seconds")
    project = checked_path(Path(project).expanduser().absolute()).resolve(strict=True)
    if not project.is_dir():
        raise ValueError("Existing project required")
    specification = plan("factory" if role == "factory" else "studio",
                         objective, host, project)
    instructions = next(x["instructions"] for x in specification["sequence"]
                        if x["role"] == role) if role != "qa" else (
                            "Independently audit the task, no file edits, no self-approval.")
    prompt = (instructions + "\nRead-only inspection only. Do not modify files, "
              "install packages, publish, access secrets, or use network tools.\nTask: " + objective)
    executable = which(EXECUTABLES[host])
    if executable is None:
        return {"host": host, "role": role, "status": "NOT_INSTALLED",
                "native_subagent": "NOT_RUN"}
    if host == "codex":
        # Codex's existing audited CLI parser already checks real JSON events.
        # It has a fixed executable and independent sandbox controls.
        result = run_codex(role, prompt, project, timeout, sandbox="read-only")
        return {"host": host, "role": role,
                "status": "HOST_COMPLETED" if result["status"] == "COMPLETED" else "BLOCKED",
                "thread_ids": result.get("thread_ids", []),
                "native_subagent": "NOT_VERIFIED",
                "evidence_kind": "CODEX_CLI_THREAD_NOT_CHILD_AGENT"}
    # Claude Code: --permission-mode plan blocks edits; -p prints one result.
    # This is a parent CLI turn, NOT a native delegated subagent invocation.
    result = runner([executable, "-p", "--output-format", "json",
                     "--permission-mode", "plan", prompt], str(project), timeout)
    if result["status"] != "OBSERVED":
        return {"host": host, "role": role, "status": "BLOCKED",
                "reason": result.get("reason", "HOST_FAILURE"),
                "native_subagent": "NOT_VERIFIED"}
    data = result["payload"]
    session = data.get("session_id")
    valid = (data.get("type") == "result" and data.get("is_error") is False
             and isinstance(session, str) and bool(session.strip())
             and isinstance(data.get("result"), str) and bool(data["result"].strip()))
    return {"host": host, "role": role,
            "status": "HOST_COMPLETED" if valid else "BLOCKED",
            "evidence_kind": "CLAUDE_PARENT_SESSION_NOT_CHILD_AGENT",
            "session_observed": bool(valid),
            "native_subagent": "NOT_VERIFIED",
            "release": "REQUIRES_INDEPENDENT_QA"}


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only host probes and gated CLI turn")
    p.add_argument("action", choices=("probe", "invoke"))
    p.add_argument("--host", choices=HOSTS, required=True)
    p.add_argument("--role", choices=("factory", "studio", "qa"))
    p.add_argument("--objective")
    p.add_argument("--project", type=Path)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--allow-paid-inference", action="store_true",
                   help="Explicitly authorize ONE live host CLI turn; may use quota")
    args = p.parse_args(argv)
    try:
        if args.action == "probe":
            report = probe(args.host)
        else:
            if not args.role or not args.objective or args.project is None:
                p.error("invoke requires --role, --objective and --project")
            report = invoke(args.host, args.role, args.objective, args.project,
                            consent=args.allow_paid_inference, timeout=args.timeout)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0 if report["status"] in ("DETECTED", "HOST_COMPLETED") else 2
    except (ValueError, OSError, UnicodeError):
        print(json.dumps({"status": "FAIL", "reason": "INVALID_OR_UNSAFE_ARGUMENTS"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
