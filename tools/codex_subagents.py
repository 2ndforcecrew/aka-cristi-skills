"""Preview-first installer for public, official-format Codex custom agent TOML.

Creates ONLY new, owned files in CODEX_HOME/agents. Never replaces unrelated roles.
No agent execution or activation claim is made by this tool.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

ROLE_NAMES = ("research", "coding", "qa", "automation")
STATE = ".aka-chef-subagents"


class AgentInstallError(ValueError):
    pass


def home_path(home=None):
    return Path(home if home is not None else os.environ.get("CODEX_HOME",
                str(Path.home() / ".codex"))).expanduser().absolute()


def safe(path):
    p = Path(path)
    if p.is_symlink():
        raise AgentInstallError("symlink is forbidden: " + p.name)
    if p.exists() and not p.is_file() and not p.is_dir():
        raise AgentInstallError("unsupported filesystem entry")
    return p


def source_for(name, root=None):
    if name not in ROLE_NAMES:
        raise AgentInstallError("unknown role")
    base = Path(root) if root else Path(__file__).resolve().parents[1] / "agents"
    source = safe(base / (name + ".toml"))
    if not source.is_file():
        raise AgentInstallError("role source missing")
    raw = source.read_text(encoding="utf-8")
    # Python 3.11+, strict public expected keys and no external commands.
    import tomllib
    data = tomllib.loads(raw)
    if set(data) != {"name", "description", "developer_instructions"}:
        raise AgentInstallError("unsupported TOML keys")
    if data["name"] != "aka_" + name:
        raise AgentInstallError("role name mismatch")
    if not all(isinstance(data[k], str) and data[k].strip() for k in data):
        raise AgentInstallError("invalid role metadata")
    return raw


def digest(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def locations(home):
    base = home_path(home)
    safe(base)
    agents = safe(base / "agents")
    state_dir = safe(base / STATE)
    state_file = safe(state_dir / "state.json")
    return agents, state_dir, state_file


def read_state(state_file):
    if not state_file.exists():
        return {"version": 1, "installed": {}}
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if (not isinstance(state, dict) or state.get("version") != 1 or
            not isinstance(state.get("installed"), dict)):
        raise AgentInstallError("unknown state format")
    return state


def plan(name, home=None, root=None):
    raw = source_for(name, root)
    agents, _, state_file = locations(home)
    destination = safe(agents / (name + ".toml"))
    state = read_state(state_file)
    recorded = state["installed"].get(name)
    if destination.exists():
        if not destination.is_file():
            raise AgentInstallError("target is not regular file")
        current = digest(destination.read_text(encoding="utf-8"))
        if recorded is None:
            action = "CONFLICT_UNMANAGED"
        elif current != recorded:
            action = "CONFLICT_MODIFIED"
        elif current == digest(raw):
            action = "ALREADY_INSTALLED"
        else:
            action = "UPGRADE"
    else:
        action = "CONFLICT_MISSING" if recorded is not None else "INSTALL"
    return {"role": name, "target": str(destination), "action": action,
            "expected_sha256": digest(raw), "applied": False}


def save_state(state_file, state):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="state-", dir=state_file.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, sort_keys=True, indent=2)
        os.replace(tmp, state_file)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def install(name, home=None, root=None, apply=False):
    result = plan(name, home, root)
    if not apply or result["action"] == "ALREADY_INSTALLED":
        return result
    if result["action"] not in ("INSTALL", "UPGRADE"):
        raise AgentInstallError("refuse to overwrite unowned or edited role")
    raw = source_for(name, root)
    agents, state_dir, state_file = locations(home)
    agents.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix="agent-", dir=agents)
    backup = None
    target = agents / (name + ".toml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(raw)
        if digest(Path(staged).read_text(encoding="utf-8")) != digest(raw):
            raise AgentInstallError("staged content mismatch")
        if target.exists():
            backup = state_dir / (name + "-" + uuid.uuid4().hex + ".toml")
            os.replace(target, backup)
        try:
            os.replace(staged, target)
            state = read_state(state_file)
            state["installed"][name] = digest(raw)
            save_state(state_file, state)
        except Exception:
            if target.exists():
                target.unlink()
            if backup and backup.exists():
                os.replace(backup, target)
            raise
    finally:
        if os.path.exists(staged):
            os.unlink(staged)
    return {**result, "applied": True, "backup": str(backup) if backup else None,
            "activation": "NOT_RUN"}


def verify(name, home=None, root=None):
    result = plan(name, home, root)
    return {**result, "integrity": ("PASS" if result["action"] == "ALREADY_INSTALLED"
                else "NOT_INSTALLED" if result["action"] == "INSTALL" else "FAIL"),
            "agent_spawn": "NOT_RUN"}


def uninstall(name, home=None, root=None, apply=False):
    result = plan(name, home, root)
    if result["action"] not in ("ALREADY_INSTALLED", "UPGRADE"):
        if result["action"] == "INSTALL":
            return {**result, "action": "NOT_INSTALLED"}
        raise AgentInstallError("uninstall refuses externally changed or unowned role")
    if not apply:
        return {**result, "action": "UNINSTALL_PREVIEW"}
    agents, state_dir, state_file = locations(home)
    target = safe(agents / (name + ".toml"))
    old = target.read_text(encoding="utf-8")
    state = read_state(state_file)
    recorded = state["installed"].get(name)
    if recorded != digest(old):
        raise AgentInstallError("role modified during uninstall")
    archive = state_dir / (name + "-" + uuid.uuid4().hex + ".toml")
    os.replace(target, archive)
    del state["installed"][name]
    try:
        save_state(state_file, state)
    except Exception:
        os.replace(archive, target)
        raise
    return {"role": name, "action": "UNINSTALL", "applied": True,
            "archive": str(archive)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="AKA.CRISTI Codex Subagents Installer")
    parser.add_argument("action", choices=["preview", "install", "verify", "uninstall"])
    parser.add_argument("--role", choices=[*ROLE_NAMES, "all"], default="all")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    roles = ROLE_NAMES if args.role == "all" else (args.role,)
    results = []
    try:
        for role in roles:
            if args.action == "preview":
                results.append(plan(role, args.codex_home))
            elif args.action == "install":
                results.append(install(role, args.codex_home, apply=args.apply))
            elif args.action == "verify":
                results.append(verify(role, args.codex_home))
            else:
                results.append(uninstall(role, args.codex_home, apply=args.apply))
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(results, indent=2))
    return 0 if all(x.get("action") not in ("CONFLICT_UNMANAGED", "CONFLICT_MODIFIED",
                                           "CONFLICT_MISSING") and
                    x.get("integrity") not in ("FAIL",) for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
