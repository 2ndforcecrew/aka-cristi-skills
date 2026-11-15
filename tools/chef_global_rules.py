"""Conservative global Codex AGENTS.md installer. Preview-first, non-destructive."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

START = "<!-- AKA.CRISTI CHEF GLOBAL START v1 -->"
END = "<!-- AKA.CRISTI CHEF GLOBAL END v1 -->"


class GlobalRulesError(ValueError):
    pass


def destination(home=None):
    if home is None:
        home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    folder = Path(home).expanduser().absolute()
    dest = folder / "AGENTS.md"
    if dest.is_symlink():
        raise GlobalRulesError("refusing symlink AGENTS.md")
    return dest


def managed_block(template):
    raw = Path(template).read_text(encoding="utf-8")
    if not raw.strip() or START in raw or END in raw:
        raise GlobalRulesError("invalid template")
    return START + "\n" + raw.rstrip() + "\n" + END


def read_old(path):
    if path.exists() and not path.is_file():
        raise GlobalRulesError("AGENTS.md is not a regular file")
    if path.is_symlink():
        raise GlobalRulesError("refusing symlink AGENTS.md")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def locate(old):
    if old.count(START) != old.count(END) or old.count(START) > 1:
        raise GlobalRulesError("ambiguous or corrupted managed markers")
    if START not in old:
        return None
    start = old.index(START)
    end = old.index(END)
    if end < start:
        raise GlobalRulesError("invalid managed marker order")
    return start, end + len(END)


def plan(action, template, home=None):
    path = destination(home)
    old = read_old(path)
    span = locate(old)
    block = managed_block(template)
    if action == "install":
        if span:
            existing = old[span[0]:span[1]]
            state = "already_installed" if existing == block else "conflict_modified"
        else:
            state = "append" if old else "create"
    elif action == "verify":
        state = ("PASS" if span and old[span[0]:span[1]] == block else
                 "FAIL" if span else "NOT_INSTALLED")
    elif action == "uninstall":
        state = "NOT_INSTALLED" if not span else (
            "remove_managed_block" if old[span[0]:span[1]] == block
            else "conflict_modified")
    else:
        raise GlobalRulesError("unsupported action")
    return {"action": action, "state": state, "target": str(path),
            "content_sha256": hashlib.sha256(block.encode()).hexdigest(),
            "applied": False}


def write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".aka-chef-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def apply(action, template, home=None, confirmed=False):
    info = plan(action, template, home)
    if action == "verify" or not confirmed:
        return info
    if info["state"] in ("already_installed", "NOT_INSTALLED"):
        return info
    if info["state"] == "conflict_modified":
        raise GlobalRulesError("managed block modified; refusing overwrite")
    path = destination(home)
    old = read_old(path)
    span = locate(old)
    block = managed_block(template)
    if action == "install":
        # Do not alter a pre-existing project/user policy; append a clearly owned section.
        new = old.rstrip("\n") + ("\n\n" if old.strip() else "") + block + "\n"
    else:
        new = old[:span[0]] + old[span[1]:]
        new = new.rstrip("\n") + "\n" if new.strip() else ""
    backup = None
    if path.exists():
        backup_folder = path.parent / ".aka-chef-backups"
        backup_folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = backup_folder / ("AGENTS-" + stamp + "-" + os.urandom(4).hex() + ".md")
        shutil.copy2(path, backup)
    try:
        write_atomic(path, new)
    except Exception:
        if backup is not None and backup.exists():
            shutil.copy2(backup, path)
        raise
    return {**info, "applied": True,
            "backup": str(backup) if backup else None,
            "post_state": plan("verify", template, home)["state"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Safe global Codex AGENTS.md setup")
    parser.add_argument("action", choices=["preview", "install", "verify", "uninstall"])
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parents[1] /
                        "templates" / "AGENTS.global.md")
    parser.add_argument("--codex-home", type=Path, help="optional isolated test directory")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        action = "install" if args.action == "preview" else args.action
        result = apply(action, args.template, args.codex_home,
                       confirmed=args.apply and args.action != "preview")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result["state"] in ("FAIL", "conflict_modified"):
            return 1
        return 0
    except (OSError, ValueError, UnicodeError) as e:
        print(json.dumps({"status": "FAIL", "error_type": type(e).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
