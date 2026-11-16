"""Portable Skill template generator: dry-run by default, no host configuration writes."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from tools.skill_validator import validate_skill

NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def plan(name: str, destination: Path, description: str) -> dict[str, object]:
    if not NAME.fullmatch(name) or len(name) > 64:
        raise ValueError("name must be lowercase kebab-case, up to 64 chars")
    if not description.strip() or "\n" in description or "\r" in description or len(description) > 500:
        raise ValueError("description must be a nonempty single line up to 500 chars")
    if any(c in description for c in "\\'\""):
        raise ValueError("description contains unsupported YAML quoting characters")
    destination = Path(destination)
    if destination.is_symlink() or destination.exists():
        raise FileExistsError("destination already exists; refusing overwrite")
    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise ValueError("destination parent must be an existing real directory")
    return {"name": name, "destination": str(destination), "files": ["SKILL.md", "CHANGELOG.md"], "status": "PLANNED"}


def create(name: str, destination: Path, description: str, *, apply: bool = False) -> dict[str, object]:
    result = plan(name, destination, description)
    if not apply:
        return result
    destination = Path(destination)
    # mkdir(exist_ok=False) is an atomic no-overwrite check on the final component.
    destination.mkdir(exist_ok=False)
    try:
        (destination / "SKILL.md").write_text(
            "---\nname: " + name + "\ndescription: " + description + "\n---\n\n"
            "# " + name + "\n\n## When to use\nDescribe the trigger.\n\n"
            "## Procedure\n1. Inspect permissions and project context.\n"
            "2. Execute within the approved scope.\n3. Verify and record evidence.\n\n"
            "## Stop conditions\nStop on missing permission or unsafe operation.\n",
            encoding="utf-8",
        )
        (destination / "CHANGELOG.md").write_text("# Changelog\n\n- 0.1.0: Initial template (unverified).\n", encoding="utf-8")
        verification = validate_skill(destination)
        if verification["status"] == "FAILED":
            raise ValueError("generated Skill failed structural preflight")
        return {**result, "status": "CREATED_PREFLIGHT_ONLY", "preflight": verification}
    except Exception:
        # Only remove files that this function created inside its new directory.
        for filename in ("SKILL.md", "CHANGELOG.md"):
            (destination / filename).unlink(missing_ok=True)
        destination.rmdir()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portable Skill template generator")
    parser.add_argument("name")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--description", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = create(args.name, args.destination, args.description, apply=args.apply)
    except (ValueError, FileExistsError, OSError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
