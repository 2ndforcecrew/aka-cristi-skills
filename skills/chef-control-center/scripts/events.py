"""Portable CHEF event journal. Python stdlib only; no agent dispatch."""
import argparse
import json
import sqlite3
import time
from pathlib import Path

STATUSES = {"PLANNED", "STARTED", "COMPLETED", "FAILED", "BLOCKED", "REVIEW_REQUIRED", "VERIFIED"}
MAX_TEXT = 128


def _safe(value):
    if not value or len(value) > MAX_TEXT or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.: " for c in value):
        raise ValueError("invalid event metadata")
    return value


def _connect(path, create=False):
    p = Path(path).expanduser()
    if p.is_symlink() or (p.exists() and not p.is_file()):
        raise ValueError("unsafe database path")
    if not create and not p.is_file():
        raise FileNotFoundError("journal does not exist")
    if create:
        p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(p) if create else p.resolve().as_uri() + "?mode=ro", uri=not create)
    if create:
        db.execute("CREATE TABLE IF NOT EXISTS chef_events (id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, actor TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL, timestamp REAL NOT NULL, evidence_ref TEXT, note TEXT)")
        db.commit()
    else:
        db.execute("PRAGMA query_only=ON")
    return db


def record(path, task, actor, status, stage, evidence_ref=None, note=None):
    task, actor, stage = (_safe(x) for x in (task, actor, stage))
    if status not in STATUSES:
        raise ValueError("invalid status")
    if evidence_ref is not None:
        _safe(evidence_ref)
    if note is not None:
        _safe(note)
    with _connect(path, create=True) as db:
        db.execute("INSERT INTO chef_events(task_id,actor,status,stage,timestamp,evidence_ref,note) VALUES (?,?,?,?,?,?,?)",
                   (task, actor, status, stage, time.time(), evidence_ref, note))
        db.commit()


def read(path, task=None, limit=100):
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    with _connect(path) as db:
        if task:
            _safe(task)
            rows = db.execute("SELECT task_id,actor,status,stage,timestamp,evidence_ref,note FROM chef_events WHERE task_id=? ORDER BY id DESC LIMIT ?", (task, limit))
        else:
            rows = db.execute("SELECT task_id,actor,status,stage,timestamp,evidence_ref,note FROM chef_events ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(zip(("task_id", "actor", "status", "stage", "timestamp", "evidence_ref", "note"), row)) for row in rows]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    sub = p.add_subparsers(dest="action", required=True)
    r = sub.add_parser("record")
    for name in ("task", "actor", "status", "stage"):
        r.add_argument("--" + name, required=True)
    r.add_argument("--evidence-ref")
    r.add_argument("--note")
    sub.add_parser("list")
    t = sub.add_parser("timeline")
    t.add_argument("--task", required=True)
    args = p.parse_args(argv)
    if args.action == "record":
        record(args.db, args.task, args.actor, args.status, args.stage, args.evidence_ref, args.note)
        result = {"status": "RECORDED", "agent_execution": "NOT_RUN"}
    else:
        result = {"events": read(args.db, args.task if args.action == "timeline" else None)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
