"""Portable Factory / Studio / QA handoff contract. Does NOT invoke a model.

Outputs explicit role input and acceptance criteria for any host able to read
JSON. Native spawning requires a separately authenticated host-specific adapter.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid
from pathlib import Path

from tools.chef_dual_engine import route
from tools.fs_safety import checked_path
from tools.universal_chef import HOSTS


def plan(kind, objective, host, project):
    if host not in HOSTS:
        raise ValueError("Unsupported host")
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 10000:
        raise ValueError("Objective must be 1..10000 characters")
    project = checked_path(Path(project).expanduser().absolute())
    if not project.is_dir():
        raise ValueError("Existing project directory required")
    tasks = []
    for role in route(kind) + ["qa"]:
        tasks.append({
            "role": role,
            "preferred_agent": {
                "factory": "aka_coding",
                "studio": "aka_research",
                "qa": "aka_qa",
            }[role],
            "instructions": {
                "factory": "Implement a narrowly-scoped patch in an isolated workspace, run tests and return diff plus evidence.",
                "studio": "Review the real user journey, visual/product intent and UX of the candidate without editing files.",
                "qa": "Independently review actual deliverables, regressions, security and evidence, without self-certifying release.",
            }[role],
            "verification": "Require separately attributable native host task/thread and real output. Text labels or mocked results are not a PASS.",
            "state": "NOT_RUN",
        })
    return {
        "schema_version": 1,
        "host": host,
        "engine": kind,
        "objective": objective,
        "project": str(project),
        "sequence": tasks,
        "native_dispatch": "NOT_RUN",
        "handoff_activation": "NOT_RUN",
        "release": "REQUIRES_HUMAN_APPROVAL",
        "status": "PLAN_ONLY",
        "note": "This JSON is an execution contract, NOT proof that any Agent was invoked.",
    }


def write_plan(spec, output_dir):
    path = checked_path(Path(output_dir).expanduser().absolute())
    if not path.is_dir():
        raise ValueError("Existing, private output directory required")
    # A new UUID and O_EXCL prevent overwriting any existing task record.
    task_id = uuid.uuid4().hex
    destination = checked_path(path / ("chef-handoff-" + task_id + ".json"))
    payload = {**spec, "task_id": task_id}
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True, indent=2)
            handle.write("\n")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return {"status": "HANDOFF_WRITTEN", "file": str(destination),
            "native_dispatch": "NOT_RUN", "task_id": task_id}


def main(argv=None):
    p = argparse.ArgumentParser(description="Host-neutral CHEF dual-engine handoff plan")
    p.add_argument("--kind", choices=("factory", "studio", "hybrid"), required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--host", choices=HOSTS, required=True)
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--out", type=Path, help="existing private folder outside the project")
    p.add_argument("--apply", action="store_true", help="write one handoff JSON, no model call")
    args = p.parse_args(argv)
    try:
        specification = plan(args.kind, args.objective, args.host, args.project)
        if args.apply:
            if args.out is None:
                p.error("--out required for --apply")
            result = write_plan(specification, args.out)
        else:
            result = specification
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({"status": "FAIL", "reason": "Invalid or unsafe project/output"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
