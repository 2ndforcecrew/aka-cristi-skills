"""CHEF V0.3 dual-engine runtime: real subprocess adapters, not simulated agents."""
import argparse
import hashlib
import json
import os
import shutil
import signal
import sqlite3
import stat
import subprocess
import time
import uuid
from pathlib import Path

from tools import host_runtime

ROLES = {"factory": "Implement and test the requested change.", "studio": "Review user journey, visual quality and product intent.", "qa": "Independently audit the actual outputs and report concrete evidence."}

def route(kind):
    if kind not in ("factory", "studio", "hybrid"):
        raise ValueError("unknown task kind")
    return ["factory", "studio"] if kind == "hybrid" else [kind]

def private_log_file(path):
    """Create new logs privately; reject unsafe existing files without chmod."""
    path = Path(path)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or (os.name == "posix" and info.st_mode & 0o077):
            raise ValueError("log must be a private regular file")
    else:
        os.close(fd)


def init_db(path):
    private_log_file(path)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS events (task_id TEXT, role TEXT, status TEXT, timestamp REAL, evidence TEXT)")
    db.commit()
    return db

def record(db, task_id, role, status, evidence=""):
    db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (task_id, role, status, time.time(), evidence))
    db.commit()

def codex_available():
    return shutil.which("codex") is not None

def run_codex(role, prompt, workspace, timeout=300, *, sandbox="read-only"):
    if role not in ROLES:
        raise ValueError("unknown role")
    if not codex_available():
        return {"status": "NOT_RUN", "reason": "Codex CLI not installed"}
    if sandbox not in ("read-only", "workspace-write") or (role == "qa" and sandbox != "read-only"):
        raise ValueError("invalid role sandbox")
    # Read-only sandbox by default. Real modifications require a separately authorized workflow.
    cmd = ["codex", "exec", "--json", "--sandbox", sandbox, "-c", 'approval_policy="never"', "-c", "sandbox_workspace_write.network_access=false", "--skip-git-repo-check", "-C", str(workspace), ROLES[role] + "\n\nTask: " + prompt]
    process = None
    def terminate_tree():
        if process is None:
            return
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=10, check=False)
        process.kill()
        process.communicate()
    try:
        process = subprocess.Popen(cmd, cwd=workspace, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True,
                                   stdin=subprocess.DEVNULL,
                                   start_new_session=os.name == "posix",
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        stdout, stderr = process.communicate(timeout=timeout)
        result = subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        terminate_tree()
        return {"status": "FAILED", "reason": "timeout"}
    except OSError as exc:
        return {"status": "FAILED", "reason": type(exc).__name__}
    except BaseException:
        terminate_tree()
        raise
    events = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            continue
    output = "\n".join(e.get("item", {}).get("text", "") for e in events
                       if e.get("type") == "item.completed" and
                       e.get("item", {}).get("type") == "agent_message")
    completed = any(e.get("type") == "turn.completed" for e in events)
    return {"status": "COMPLETED" if result.returncode == 0 and completed else "FAILED",
            "exit_code": result.returncode, "event_count": len(events), "output": output,
            "events": events, "sandbox": sandbox,
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

def _git(workspace, *args):
    return subprocess.run(["git", "-C", str(workspace), *args], check=True,
                          capture_output=True, timeout=60).stdout


def orchestrate(kind, prompt, workspace, db_path, timeout=300, *,
                task_id=None, host="codex", authorize_inference=False):
    """Durable isolated proposals; never grants release or QA acceptance.

    Recovery is explicit, limited to three attempts per role, and starts failed
    attempts from committed snapshots. A DB write lock prevents duplicate workers.
    Artifact directories are private; callers must retain them with the database.
    """
    roles = route(kind) + ["qa"]
    if host != "codex":
        if host not in host_runtime.HOST_BIN:
            raise ValueError("No verified host runtime adapter")
        if not authorize_inference:
            raise ValueError("Explicit --authorize-inference required for non-Codex hosts")
    if not 1 <= timeout <= 3600:
        raise ValueError("timeout must be 1..3600")
    workspace = Path(workspace).resolve(strict=True)
    head = _git(workspace, "rev-parse", "HEAD").decode().strip()
    if _git(workspace, "status", "--porcelain"):
        raise ValueError("commit or preserve workspace changes before isolated execution")
    if Path(db_path).is_symlink():
        raise ValueError("database symlink is not allowed")
    db_path = Path(db_path).resolve()
    if db_path.is_relative_to(workspace):
        raise ValueError("database and artifacts must be outside the source workspace")
    db = init_db(db_path)
    db.execute("CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, config TEXT, status TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS attempts (task_id TEXT, role TEXT, attempt INTEGER, result TEXT, PRIMARY KEY(task_id, role, attempt))")
    db.commit()
    details = dict(kind=kind, prompt=prompt, workspace=str(workspace),
                   head=head, timeout=timeout)
    if host != "codex":
        details["host"] = host
    config = json.dumps(details, sort_keys=True)
    # Separate SQLite mutex permits durable checkpoints without duplicate dispatch.
    lock = None
    try:
        private_log_file(str(db_path) + ".lock")
        lock = sqlite3.connect(str(db_path) + ".lock", timeout=1)
        lock.execute("BEGIN EXCLUSIVE")
        if task_id is None:
            task_id = str(uuid.uuid4())
            db.execute("INSERT INTO tasks VALUES (?,?,?)", (task_id, config, "IN_PROGRESS"))
        else:
            old = db.execute("SELECT config FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if old is None or old[0] != config:
                raise ValueError("resume configuration or source commit mismatch")
        db.commit()
        root = db_path.parent / (db_path.name + ".runs") / task_id
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        results = {}
        previous = workspace
        status = "REVIEW_REQUIRED"
        for role in roles:
            rows = db.execute("SELECT attempt, result FROM attempts WHERE task_id=? AND role=? ORDER BY attempt", (task_id, role)).fetchall()
            if rows and json.loads(rows[-1][1])["status"] == "COMPLETED":
                result = json.loads(rows[-1][1])
                saved = Path(result["workspace"])
                artifact = Path(result["patch"])
                if (not saved.is_dir() or _git(saved, "status", "--porcelain") or
                        _git(saved, "rev-parse", "HEAD").decode().strip() != result["snapshot"] or
                        not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != result["patch_sha256"]):
                    raise ValueError("resume artifact missing or modified")
                results[role] = result
                previous = Path(result["workspace"])
                continue
            if len(rows) >= 3:
                status = "BLOCKED"
                break
            attempt = len(rows) + 1
            # A crash before durable result leaves an orphan directory, never reused.
            target = root / (role + "-" + str(attempt) + "-" + uuid.uuid4().hex)
            handoff = dict(task_id=task_id, engine=kind, role=role, objective=prompt,
                           scope=str(target), allowed_tools=(
                               "local sandbox tools" if host == "codex"
                               else "read-only plan mode; text proposals only"),
                           prohibited_actions="No network, publishing, credential changes, merge, release, paid calls or sandbox escalation",
                           acceptance_criteria="Report commands, results and concrete evidence; never self-certify release",
                           timeout=timeout, retry_policy="explicit resume, maximum 3 attempts",
                           input_artifacts={k: dict(workspace=v["workspace"], output=v.get("output", "")) for k,v in results.items()},
                           escalation="Return BLOCKED with missing evidence")
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (task_id, role, "STARTED", time.time(), json.dumps(handoff)))
            db.execute("INSERT INTO attempts VALUES (?,?,?,?)", (task_id, role, attempt,
                       json.dumps(dict(status="INTERRUPTED", workspace=str(target)))))
            db.commit()
            try:
                _git(workspace, "clone", "--quiet", "--no-hardlinks", str(previous), str(target))
                _git(target, "checkout", "--detach", "--quiet")
                baseline = _git(target, "rev-parse", "HEAD").decode().strip()
                text = json.dumps(handoff, ensure_ascii=False) + "\nInspect prior deliverables. " + prompt
                if host == "codex":
                    result = run_codex(role, text, target, timeout,
                                       sandbox="workspace-write" if role == "factory" else "read-only")
                else:
                    result = host_runtime.run(host, role, text, target,
                                              timeout, authorized=authorize_inference)
                result["workspace"] = str(target)
                # Preserve untracked files and modifications in this private proposal clone.
                _git(target, "add", "--all")
                patch = _git(target, "diff", "--cached", "--binary", baseline)
                artifact = root / (target.name + ".patch")
                artifact.write_bytes(patch)
                result["patch"] = str(artifact)
                result["patch_sha256"] = hashlib.sha256(patch).hexdigest()
                if (host != "codex" or role != "factory") and patch:
                    result.update(status="FAILED", reason="read-only role modified deliverables")
                if result["status"] == "COMPLETED":
                    ids = result.get("thread_ids", [])
                    used = [i for v in results.values() for i in v.get("thread_ids", [])]
                    if len(ids) != 1 or ids[0] in used or not result.get("output", "").strip():
                        result.update(status="FAILED", reason="missing output or independent thread identity")
                    else:
                        _git(target, "-c", "user.name=CHEF proposal", "-c", "user.email=chef@example.invalid",
                             "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false", "commit", "--quiet", "--allow-empty", "-m", "CHEF isolated proposal")
                        result["snapshot"] = _git(target, "rev-parse", "HEAD").decode().strip()
            except (OSError, subprocess.SubprocessError) as exc:
                result = dict(status="FAILED", reason=type(exc).__name__, workspace=str(target))
            results[role] = result
            db.execute("UPDATE attempts SET result=? WHERE task_id=? AND role=? AND attempt=?", (json.dumps(result), task_id, role, attempt))
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (task_id, role, result["status"], time.time(), json.dumps(result)))
            db.commit()
            if result["status"] != "COMPLETED":
                status = "BLOCKED"
                break
            previous = target
        db.execute("UPDATE tasks SET status=? WHERE task_id=?", (status, task_id))
        db.commit()
        return dict(task_id=task_id, status=status, results=results,
                    qa=results.get("qa", "NOT_RUN"), release="BLOCKED",
                    host=host, native_child_agents=(
                        "NOT_VERIFIED" if host != "codex" else "HOST_EVIDENCE_REQUIRED"),
                    evidence_kind=(
                        "independent_host_turns_not_native_agent_spawns"
                        if host != "codex" else
                        "agent_invocation_requires_independent_acceptance"))
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
        if lock is not None:
            lock.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["factory", "studio", "hybrid"], required=True)
    parser.add_argument("--host", choices=["codex", *host_runtime.HOST_BIN], default="codex")
    parser.add_argument("--authorize-inference", action="store_true",
                        help="required for non-Codex model usage; may consume credits")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--resume", help="Explicitly retry a durable task ID (maximum 3 attempts per role)")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600:
        parser.error("timeout must be 1..3600")
    if args.host != "codex" and not args.authorize_inference:
        parser.error("Non-Codex runtime requires --authorize-inference")
    db_path = args.db or args.workspace.resolve().parent / (args.workspace.resolve().name + ".chef-runtime.sqlite3")
    result = orchestrate(args.kind, args.prompt, args.workspace, db_path,
                         args.timeout, task_id=args.resume, host=args.host,
                         authorize_inference=args.authorize_inference)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REVIEW_REQUIRED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
