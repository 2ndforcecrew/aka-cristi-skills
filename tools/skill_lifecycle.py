"""Read-only Skill lifecycle inventory, provenance digest and retirement advice.

This is not a release manager and does not mutate installed Skills.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

from tools.fs_safety import checked_path
from tools.skill_validator import validate_skill

EXCLUDED = {".git", "__pycache__", ".aka-skill-installer"}


def _raise_walk_error(error: OSError) -> None:
    raise error


def inventory(root: Path) -> dict[str, object]:
    try:
        return _inventory_checked(checked_path(root))
    except (OSError, ValueError) as exc:
        # Never publish a partial digest or private filesystem exception text.
        return {"status": "BLOCKED", "reason": "unsafe or unreadable filesystem",
                "error_type": type(exc).__name__, "runtime_verified": False}


def _inventory_checked(root: Path) -> dict[str, object]:
    preflight = validate_skill(root)
    if preflight["status"] == "FAILED":
        return {"status": "BLOCKED", "preflight": preflight, "runtime_verified": False}
    digest = hashlib.sha256()
    files: list[str] = []
    for folder, dirs, names in os.walk(root, followlinks=False, onerror=_raise_walk_error):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for dirname in dirs:
            directory = checked_path(Path(folder) / dirname)
            if directory.is_symlink():
                return {"status": "BLOCKED", "reason": "symlink directory", "runtime_verified": False}
        for name in sorted(names):
            path = checked_path(Path(folder) / name)
            if path.is_symlink() or not path.is_file():
                return {"status": "BLOCKED", "reason": "non-regular file", "runtime_verified": False}
            rel = path.relative_to(root).as_posix()
            if len(files) >= 100 or path.stat().st_size > 2 * 1024 * 1024:
                return {"status": "BLOCKED", "reason": "package limits exceeded", "runtime_verified": False}
            files.append(rel)
            digest.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return {
        "status": "INVENTORIED_NOT_RELEASED",
        "digest_sha256": digest.hexdigest(),
        "files": files,
        "preflight": preflight,
        "runtime_verified": False,
        "release_approved": False,
        "host_evidence": {"codex": "NOT_RUN", "claude": "NOT_RUN", "gemini": "NOT_RUN", "opencode": "NOT_RUN", "hermes": "NOT_RUN"},
        "maintenance": {"review_required": True, "deprecation_decision": "HUMAN_REVIEW_REQUIRED"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Skill lifecycle inventory")
    parser.add_argument("skill_dir", type=Path)
    args = parser.parse_args(argv)
    result = inventory(args.skill_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
