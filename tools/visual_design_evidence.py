"""Validate Visual Design Skill evidence ledgers without claiming visual quality.

Usage: python -m tools.visual_design_evidence path/to/evidence.json
"""
import argparse
import json
from pathlib import Path

STATUSES = {"VERIFIED", "FAILED", "NOT_RUN", "SUBJECTIVE_REVIEW"}
REQUIRED = {"artifact", "medium", "checks"}
INTERACTIVE = {"web", "ui", "interactive", "motion"}


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["Evidence must be a JSON object"]
    for field in REQUIRED - data.keys():
        errors.append(f"Missing field: {field}")
    if not isinstance(data.get("artifact"), str) or not data.get("artifact", "").strip():
        errors.append("artifact must be a nonempty path or URL")
    medium = data.get("medium")
    if not isinstance(medium, str) or not medium.strip():
        errors.append("medium must be a nonempty string")
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        return errors + ["checks must be a nonempty list"]
    seen = set()
    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"checks[{i}] must be an object")
            continue
        name = check.get("name")
        status = check.get("status")
        method = check.get("method")
        evidence = check.get("evidence")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"checks[{i}].name missing")
        elif name in seen:
            errors.append(f"Duplicate check: {name}")
        else:
            seen.add(name)
        if status not in STATUSES:
            errors.append(f"checks[{i}].status invalid: {status}")
        if not isinstance(method, str) or not method.strip():
            errors.append(f"checks[{i}].method missing")
        if status == "VERIFIED" and (not isinstance(evidence, str) or not evidence.strip()):
            errors.append(f"checks[{i}] VERIFIED requires evidence")
        if status in {"NOT_RUN", "FAILED"} and not check.get("limitation"):
            errors.append(f"checks[{i}] {status} requires limitation")
    if medium in INTERACTIVE:
        for required in ("responsive", "keyboard", "reduced-motion"):
            if required not in seen:
                errors.append(f"Interactive medium requires check: {required}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.ledger.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot read ledger: {exc}\n")
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: evidence ledger contract valid; this does NOT prove visual quality or live Agent execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
