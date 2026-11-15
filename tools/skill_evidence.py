"""Validate Skill verification ledger format; NEVER assert tests were executed.

The record is a declaration plus evidence references. An independent reviewer must
inspect the actual referenced artifacts before accepting it as verified.
"""
import argparse
import json
import re
from pathlib import Path

IDENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")
DIGEST = re.compile(r"^[0-9a-f]{40,64}$")
STATES = {"PASS", "FAIL", "NOT RUN"}
CATEGORIES = {"behavior", "performance", "quality", "security", "accessibility"}
CHECK_KEYS = {"category", "name", "status", "evidence"}
ROOT_KEYS = {"task_id", "revision", "scenario", "executor", "reviewer", "checks", "approval", "rollback"}


def _safe_string(value, *, max_length=512):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError("missing or excessive string")
    if any(c in value for c in ("\x00", "\r", "\n")):
        raise ValueError("control character")
    return value.strip()


def validate_ledger(document):
    if not isinstance(document, dict) or set(document) != ROOT_KEYS:
        raise ValueError("ledger schema keys do not match")
    for key in ("task_id", "executor", "reviewer"):
        if not isinstance(document[key], str) or not IDENT.fullmatch(document[key]):
            raise ValueError("invalid " + key)
    if document["executor"] == document["reviewer"]:
        raise ValueError("reviewer must differ from executor")
    if not isinstance(document["revision"], str) or not DIGEST.fullmatch(document["revision"]):
        raise ValueError("revision must be a git-like hex commit digest")
    _safe_string(document["scenario"])
    _safe_string(document["rollback"])
    if type(document["approval"]) is not bool:
        raise ValueError("approval must be boolean")
    checks = document["checks"]
    if not isinstance(checks, list) or not checks:
        raise ValueError("at least one check required")
    seen = set()
    for check in checks:
        if not isinstance(check, dict) or set(check) != CHECK_KEYS:
            raise ValueError("invalid check keys")
        if check["category"] not in CATEGORIES or check["status"] not in STATES:
            raise ValueError("unsupported category or status")
        name = _safe_string(check["name"], max_length=120)
        unique = (check["category"], name)
        if unique in seen:
            raise ValueError("duplicate check")
        seen.add(unique)
        evidence = check["evidence"]
        if check["status"] in ("PASS", "FAIL"):
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("executed checks require evidence references")
            for reference in evidence:
                ref = _safe_string(reference)
                if "://" in ref and not ref.startswith("https://"):
                    raise ValueError("only HTTPS URLs permitted")
        elif evidence != []:
            raise ValueError("NOT RUN cannot claim supporting evidence")
    return {
        "well_formed": True,
        "reviewer_separate": True,
        "statuses": {state: sum(check["status"] == state for check in checks)
                     for state in ("PASS", "FAIL", "NOT RUN")},
        "all_checks_pass": all(check["status"] == "PASS" for check in checks),
        "approval_recorded": document["approval"],
        "evidence_authenticity_verified": False,
        "task_replayed": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Check evidence declarations; does not execute tests")
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate_ledger(json.loads(args.file.read_text(encoding="utf-8")))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"well_formed": False, "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
