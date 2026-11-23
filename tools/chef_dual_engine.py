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

class ProcessGroupTimeout(subprocess.TimeoutExpired):
    """TimeoutExpired carrying POSIX descendant verification (WP-C).

    ``descendants_verified_terminated`` is True only when the whole
    process group was observed empty after SIGKILL (two consecutive
    empty polls, mirroring WP-B's wait_for_job_empty on Windows);
    ``alive_pids`` lists PIDs still observed at the end of the
    verification window (best effort: the direct child pid when it is
    still alive -- individual grandchild PIDs are not enumerated
    without psutil).
    """

    def __init__(self, cmd, timeout, *, descendants_verified_terminated=False, alive_pids=()):
        super().__init__(cmd, timeout)
        self.descendants_verified_terminated = bool(descendants_verified_terminated)
        self.alive_pids = list(alive_pids)

def _process_group_empty(pgid):
    """True when no live process remains in *pgid*.

    On Linux /proc is consulted so a zombie awaiting reaping does not
    count as alive; elsewhere killpg(pgid, 0) is the check (ESRCH
    means the group is gone).
    """
    procfs = Path("/proc")
    if procfs.is_dir():
        try:
            entries = list(procfs.iterdir())
        except OSError:
            return False
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                text = (entry / "stat").read_text(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                continue
            rparen = text.rfind(")")
            fields = text[rparen + 2:].split()
            if len(fields) < 3:
                continue
            try:
                pgrp = int(fields[2])
            except ValueError:
                continue
            if pgrp == pgid and fields[0] != "Z":
                return False
        return True
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False

def _alive_pids(proc):
    try:
        return [] if proc.poll() is not None else [proc.pid]
    except OSError:
        return [proc.pid]

def _kill_and_verify_process_group(proc, *, verify_timeout=5.0, poll_interval=0.05):
    """SIGKILL *proc*'s process group and verify it emptied.

    Returns (verified, alive_pids). verified is True only after two
    consecutive empty polls (mirroring WP-B wait_for_job_empty); a
    failed poll counts as not-verified, never as empty. Never raises.
    """
    pgid = proc.pid  # start_new_session=True makes pgid == child pid
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass  # Group exists but is not ours; polls below report alive.
    deadline = time.monotonic() + verify_timeout
    empty_streak = 0
    while True:
        try:
            reaped = proc.poll() is not None
            empty = _process_group_empty(pgid)
        except OSError:
            return False, _alive_pids(proc)
        if reaped and empty:
            empty_streak += 1
            if empty_streak >= 2:
                return True, []
        else:
            empty_streak = 0
        if time.monotonic() >= deadline:
            return False, _alive_pids(proc)
        time.sleep(poll_interval)

def run_in_process_group(command, cwd, timeout, env=None, *, text=False,
                         encoding=None, errors=None, verify_timeout=5.0,
                         poll_interval=0.05):
    """Run *command* in its own POSIX process group; return CompletedProcess.

    POSIX counterpart of WP-B's run_in_job: the child gets a fresh
    session (start_new_session=True), so its process-group id equals
    its pid. On timeout the whole group is SIGKILLed and polled until
    empty, then a ProcessGroupTimeout is raised carrying
    descendants_verified_terminated (True only when the group was
    observed empty) and alive_pids. Raises OSError if the child
    cannot start. POSIX only; Windows callers must use run_in_job.
    """
    if os.name != "posix":
        raise ValueError("run_in_process_group is POSIX-only")
    proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=text, encoding=encoding,
                            errors=errors, env=env, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        verified, alive = _kill_and_verify_process_group(
            proc, verify_timeout=verify_timeout, poll_interval=poll_interval)
        try:
            # Reap and drain like subprocess.run does after a timeout;
            # also closes the pipes (no ResourceWarning on the caller).
            proc.communicate()
        except (OSError, ValueError):
            pass
        raise ProcessGroupTimeout(command, timeout,
                                  descendants_verified_terminated=verified,
                                  alive_pids=alive) from None
    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)

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


def orchestrate(kind, prompt, workspace, db_path, timeout=300, *, task_id=None):
    """Durable isolated proposals; never grants release or QA acceptance.

    Recovery is explicit, limited to three attempts per role, and starts failed
    attempts from committed snapshots. A DB write lock prevents duplicate workers.
    Artifact directories are private; callers must retain them with the database.
    """
    roles = route(kind) + ["qa"]
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
    config = json.dumps(dict(kind=kind, prompt=prompt, workspace=str(workspace), head=head, timeout=timeout), sort_keys=True)
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
                           scope=str(target), allowed_tools="local sandbox tools",
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
                result = run_codex(role, text, target, timeout,
                                   sandbox="workspace-write" if role == "factory" else "read-only")
                result["workspace"] = str(target)
                # Preserve untracked files and modifications in this private proposal clone.
                _git(target, "add", "--all")
                patch = _git(target, "diff", "--cached", "--binary", baseline)
                artifact = root / (target.name + ".patch")
                artifact.write_bytes(patch)
                result["patch"] = str(artifact)
                result["patch_sha256"] = hashlib.sha256(patch).hexdigest()
                if role != "factory" and patch:
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
                    evidence_kind="agent_invocation_requires_independent_acceptance")
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
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--resume", help="Explicitly retry a durable task ID (maximum 3 attempts per role)")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600:
        parser.error("timeout must be 1..3600")
    db_path = args.db or args.workspace.resolve().parent / (args.workspace.resolve().name + ".chef-runtime.sqlite3")
    result = orchestrate(args.kind, args.prompt, args.workspace, db_path, args.timeout, task_id=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REVIEW_REQUIRED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
