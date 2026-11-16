"""Read-only structural and safety preflight for portable Agent Skills.

This does NOT execute scripts, install packages or prove runtime compatibility.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_SCRIPT_EXT = {".py", ".js", ".ts", ".sh", ".ps1", ".bat", ".cmd"}
MAX_SKILL_BYTES = 256 * 1024


def validate_skill(root: Path) -> dict[str, object]:
    root = Path(root)
    findings: list[dict[str, str]] = []

    def finding(code: str, message: str, severity: str = "error") -> None:
        findings.append({"code": code, "message": message, "severity": severity})

    if not root.is_dir() or root.is_symlink():
        finding("INVALID_ROOT", "Skill root must be a real directory, not a symlink.")
        return _result(root, findings)

    entry = root / "SKILL.md"
    if entry.is_symlink() or not entry.is_file():
        finding("MISSING_ENTRY", "A regular SKILL.md file is required.")
        return _result(root, findings)

    if entry.stat().st_size > MAX_SKILL_BYTES:
        finding("OVERSIZE_ENTRY", "SKILL.md exceeds the preflight size limit.")
        return _result(root, findings)

    try:
        data = entry.read_text(encoding="utf-8")
    except (UnicodeError, OSError) as exc:
        finding("UNREADABLE_ENTRY", type(exc).__name__)
        return _result(root, findings)

    lines = data.splitlines()
    if not lines or lines[0].strip() != "---":
        finding("MISSING_FRONTMATTER", "SKILL.md must start with YAML frontmatter.")
    else:
        try:
            closing = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        except StopIteration:
            finding("UNCLOSED_FRONTMATTER", "Missing closing ---.")
        else:
            # Deliberately parse only mandatory top-level scalar fields; no YAML execution.
            fields: dict[str, str] = {}
            for line in lines[1:closing]:
                match = re.match(r"^(name|description):\s*(.*)$", line)
                if match:
                    fields[match.group(1)] = match.group(2).strip().strip("'\"")
            name = fields.get("name", "")
            if not NAME_RE.fullmatch(name) or len(name) > 64:
                finding("INVALID_NAME", "name must be lowercase kebab-case, up to 64 characters.")
            if not fields.get("description") or fields.get("description") in (">", "|", ">-", "|-"):
                # Multiline YAML descriptions require a real parser; flag for review, not false PASS.
                finding("DESCRIPTION_REVIEW", "description missing or multiline; manually review YAML.", "warning")
            if not any(line.strip() for line in lines[closing + 1:]):
                finding("EMPTY_INSTRUCTIONS", "SKILL.md must contain instructions after frontmatter.")

    scripts = root / "scripts"
    if scripts.exists():
        if scripts.is_symlink() or not scripts.is_dir():
            finding("UNSAFE_SCRIPTS_DIR", "scripts must be a real directory.")
        else:
            for path in scripts.rglob("*"):
                if path.is_symlink():
                    finding("SYMLINK_IN_SCRIPTS", f"Symlink is not accepted: {path.relative_to(root)}")
                elif path.is_file() and path.suffix.lower() not in ALLOWED_SCRIPT_EXT:
                    finding("SCRIPT_REVIEW", f"Unrecognized script asset: {path.relative_to(root)}", "warning")

    return _result(root, findings)


def _result(root: Path, findings: list[dict[str, str]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "skill_path": str(root),
        "status": "FAILED" if any(f["severity"] == "error" for f in findings) else "PREFLIGHT_ONLY",
        "runtime_verified": False,
        "host_compatibility_verified": False,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Skill preflight; no runtime claims")
    parser.add_argument("skill_dir", type=Path)
    args = parser.parse_args(argv)
    result = validate_skill(args.skill_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
