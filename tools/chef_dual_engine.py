"""CHEF V0.3 dual-engine runtime: real subprocess adapters, not simulated agents."""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

ROLES = {"factory": "Implement and test the requested change.", "studio": "Review user journey, visual quality and product intent.", "qa": "Independently audit the actual outputs and report concrete evidence."}

def route(kind):
    if kind not in ("factory", "studio", "hybrid"):
        raise ValueError("unknown task kind")
    return ["factory", "studio"] if kind == "hybrid" else [kind]

def init_db(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS events (task_id TEXT, role TEXT, status TEXT, timestamp REAL, evidence TEXT)")
    db.commit()
    return db

def record(db, task_id, role, status, evidence=""):
    db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (task_id, role, status, time.time(), evidence))
    db.commit()

def codex_available():
    return shutil.which("codex") is not None

def run_codex(role, prompt, workspace, timeout=300):
    if role not in ROLES:
        raise ValueError("unknown role")
    if not codex_available():
        return {"status": "NOT_RUN", "reason": "Codex CLI not installed"}
    # Read-only sandbox by default. Real modifications require a separately authorized workflow.
    cmd = ["codex", "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "-C", str(workspace), ROLES[role] + "\n\nTask: " + prompt]
    try:
        result = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "reason": "timeout"}
    except OSError as exc:
        return {"status": "FAILED", "reason": type(exc).__name__}
    events = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            continue
    completed = any(e.get("type") == "turn.completed" for e in events)
    return {"status": "COMPLETED" if result.returncode == 0 and completed else "FAILED",
            "exit_code": result.returncode, "event_count": len(events),
            "thread_ids": [e.get("thread_id") for e in events if e.get("type") == "thread.started" and e.get("thread_id")],
            "stderr_tail": result.stderr[-500:]}

def execute(kind, prompt, workspace, db_path, timeout=300):
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace must exist")
    task_id = str(uuid.uuid4())
    db = init_db(db_path)
    try:
        results = {}
        for role in route(kind):
            record(db, task_id, role, "STARTED")
            result = run_codex(role, prompt, workspace, timeout)
            results[role] = result
            record(db, task_id, role, result["status"], json.dumps(result))
            if result["status"] != "COMPLETED":
                return {"task_id": task_id, "status": "BLOCKED", "results": results, "qa": "NOT_RUN"}
        # QA is a separate invocation, not a self-reported pass.
        record(db, task_id, "qa", "STARTED")
        qa = run_codex("qa", prompt + "\nReview the prior task deliverables in this workspace; report missing evidence.", workspace, timeout)
        record(db, task_id, "qa", qa["status"], json.dumps(qa))
        # Invocation success alone does NOT constitute independent acceptance.
        return {"task_id": task_id, "status": "REVIEW_REQUIRED", "results": results, "qa": qa}
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["factory", "studio", "hybrid"], required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--db", type=Path, default=Path("chef-runtime.sqlite3"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600:
        parser.error("timeout must be 1..3600")
    result = execute(args.kind, args.prompt, args.workspace, args.db, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REVIEW_REQUIRED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
