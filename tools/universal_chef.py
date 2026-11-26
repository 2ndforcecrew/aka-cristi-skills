"""CHEF portable project adapter: rules + 31 Skills + four role definitions.

Installs 6 native skills plus 25 vendored skills (Addy Osmani agent-skills,
MIT, vendored by PR #66) through the same path; vendored interview-me is
reference-only and never installed. Also installs the upstream slash
commands for the two hosts that define a commands directory (Claude Code:
.claude/commands/*.md, Gemini CLI: .gemini/commands/*.toml). Codex invokes
skills directly (@skill) and ships no commands; OpenCode has no upstream
command files; WorkBuddy/Hermes/generic have no upstream-defined command
format. Hooks are never installed or wired. Node validator scripts are
reference-only, never a runtime dependency.

An installed definition is NOT a live agent. Native host loading/dispatch require
a real runtime and separate acceptance. Never overwrites unmanaged configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from tools import quick_install, skill_installer
from tools.fs_safety import checked_path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = quick_install.SKILLS
VENDOR_DIRNAME = "addy-agent-skills"
# Hosts with an upstream-defined commands directory: host -> relative path
# used both under vendor/addy-agent-skills/ (source) and under the target
# project (destination). Claude ships .md commands, Gemini ships .toml
# commands; the plan-vs-planning naming difference is upstream's and is
# kept as-is (see docs/host-adaptation.md).
COMMANDS = {
    "claude": ".claude/commands",
    "gemini": ".gemini/commands",
}
ROLES = ("research", "coding", "qa", "automation")
HOSTS = ("codex", "workbuddy", "claude", "gemini", "opencode", "hermes", "generic")
FILES = {
    "workbuddy": (".codebuddy/rules/aka-chef.md", ".codebuddy/agents", ".codebuddy/skills"),
    "claude": (".claude/rules/aka-chef.md", ".claude/agents", ".claude/skills"),
    "gemini": ("GEMINI.md", ".gemini/agents", ".gemini/skills"),
    "opencode": ("AGENTS.md", ".opencode/agents", ".opencode/skills"),
    "hermes": ("AGENTS.md", ".aka-chef/role-templates", None),
    "generic": ("AGENTS.md", ".aka-chef/role-templates", ".agents/skills"),
}
USER_FILES = {
    "workbuddy": FILES["workbuddy"],
    "claude": FILES["claude"],
    "gemini": (".gemini/GEMINI.md", ".gemini/agents", ".gemini/skills"),
    "opencode": (".config/opencode/AGENTS.md",
                 ".config/opencode/agents", ".config/opencode/skills"),
}
APPEND_RULES = {"gemini", "opencode", "hermes", "generic"}
STATE_DIR = ".aka-chef-install"
MAX_RULE_BYTES = 128 * 1024


class InstallError(ValueError):
    pass


def _safe(path):
    return checked_path(path, InstallError)


def _vendor_root():
    """Vendored upstream pack root (read ROOT at call time: bind_tools_to_root)."""
    return ROOT / "vendor" / VENDOR_DIRNAME


def _command_plans(host, project, state):
    """Plan upstream slash-command files for hosts that define a commands dir.

    Returns {relative path: {"action", "sha256"}} using the same conflict
    rules as rules/roles. Empty for hosts without an upstream commands
    directory. Raises InstallError when the vendored commands directory
    is missing (fail closed: a checkout without vendor/ must not silently
    install zero commands).
    """
    rel_dir = COMMANDS.get(host)
    if rel_dir is None:
        return {}
    source_dir = _vendor_root() / rel_dir
    if not source_dir.is_dir():
        raise InstallError(f"vendored commands missing: {source_dir}")
    plans = {}
    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        rel = rel_dir + "/" + path.name
        expected = path.read_bytes()
        plans[rel] = {
            "action": _file_action(
                project / rel, _digest(expected), state["files"].get(rel)),
            "sha256": _digest(expected),
        }
    return plans


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _state_file(project, host):
    return _safe(project / STATE_DIR / (host + ".json"))


def _read_state(path):
    if not path.exists():
        return {"schema": 1, "files": {}, "rule": None}
    if not path.is_file() or path.stat().st_size > 128 * 1024:
        raise InstallError("Unsafe installer state")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != 1
            or not isinstance(data.get("files"), dict)
            or ("rule" in data and data["rule"] is not None and not isinstance(data["rule"], dict))):
        raise InstallError("Invalid installer state")
    return data


def _atomic_write(path, data):
    path = _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".aka-chef-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _role(name, host):
    import tomllib
    info = tomllib.loads((ROOT / "agents" / (name + ".toml")).read_text(encoding="utf-8"))
    if info.get("name") != "aka_" + name:
        raise InstallError("Invalid role source")
    description = info["description"]
    instructions = info["developer_instructions"]
    if any(x in description for x in ("\n", "\r", ": ", "\"")) or "---" in description:
        raise InstallError("Unsafe role frontmatter")
    front = ["---", "name: aka_" + name, "description: " + description]
    if host == "opencode":
        front.append("mode: subagent")
    elif host == "gemini":
        front.append("kind: local")
    if host in ("hermes", "generic"):
        return ("# AKA.CRISTI / " + info["name"] + "\n\n"
                + "> Manual handoff definition only; this file is NOT a native agent.\n\n"
                + instructions + "\n").encode("utf-8")
    return ("\n".join(front + ["---", "", "# " + info["name"], "", instructions, ""])).encode("utf-8")


def _rules():
    return (ROOT / "templates" / "AGENTS.global.md").read_bytes()


def _markers(host):
    return (("<!-- AKA.CRISTI CHEF " + host + " BEGIN -->").encode("ascii"),
            ("<!-- AKA.CRISTI CHEF " + host + " END -->").encode("ascii"))


def _rule_block(host):
    start, end = _markers(host)
    return start + b"\n" + _rules().rstrip(b"\n") + b"\n" + end + b"\n"


def _split_rule(data, host):
    start, end = _markers(host)
    if data.count(start) != 1 or data.count(end) != 1:
        raise InstallError("Managed rule markers missing or duplicated")
    a = data.index(start)
    b = data.index(end, a) + len(end)
    if b < len(data) and data[b:b + 1] == b"\n":
        b += 1
    return data[:a], data[a:b], data[b:]


def _file_action(path, expected, recorded):
    path = _safe(path)
    if path.exists():
        if not path.is_file() or path.stat().st_size > MAX_RULE_BYTES:
            raise InstallError("Non-regular or oversized target file")
        current = _digest(path.read_bytes())
        if recorded is None:
            return "CONFLICT_UNMANAGED"
        if current != recorded:
            return "CONFLICT_MODIFIED"
        return "ALREADY_INSTALLED" if expected == current else "UPGRADE"
    return "CONFLICT_MISSING" if recorded is not None else "INSTALL"


def inspect(host, project=None, hermes_skills_root=None, scope="project"):
    if host not in HOSTS:
        raise InstallError("Unknown host")
    if host == "codex":
        return {"host": host, "scope": "user", "status": "PREVIEW",
                "codex": quick_install.execute(), "activation": "NOT_RUN"}
    if scope not in ("project", "user"):
        raise InstallError("Invalid scope")
    if scope == "user":
        if host not in USER_FILES:
            raise InstallError("This host has no verified user-level CHEF rules path")
        if project is not None:
            raise InstallError("--project is incompatible with --scope user")
        project = Path.home()
        rule_rel, agent_dir, skills_dir = USER_FILES[host]
    else:
        if project is None:
            raise InstallError("Project-scoped install requires --project")
        rule_rel, agent_dir, skills_dir = FILES[host]
    project = _safe(Path(project).expanduser().absolute()).resolve(strict=True)
    if not project.is_dir():
        raise InstallError("Target root must already exist")
    if host == "hermes" and hermes_skills_root is not None:
        skills_dir = str(_safe(Path(hermes_skills_root).expanduser().resolve()))
    state_path = _state_file(project, host)
    state = _read_state(state_path)
    plans = {}
    for name in ROLES:
        rel = agent_dir + "/" + ("aka_" + name + ".md")
        expected = _role(name, host)
        plans[rel] = {
            "action": _file_action(project / rel, _digest(expected), state["files"].get(rel)),
            "sha256": _digest(expected),
        }
    rule_target = _safe(project / rule_rel)
    append = host in APPEND_RULES
    if append:
        existing = rule_target.read_bytes() if rule_target.exists() and rule_target.is_file() else None
        if existing is not None and len(existing) > MAX_RULE_BYTES:
            raise InstallError("Rule file too large")
        if rule_target.exists() and existing is None:
            raise InstallError("Rule target is not a regular file")
        recorded = state.get("rule")
        if existing is None:
            action = "CONFLICT_MISSING" if recorded is not None else "INSTALL"
        else:
            begin, end = _markers(host)
            if begin in existing or end in existing:
                if recorded is None:
                    action = "CONFLICT_UNMANAGED"
                else:
                    try:
                        _, segment, _ = _split_rule(existing, host)
                        if _digest(segment) != recorded.get("sha256"):
                            action = "CONFLICT_MODIFIED"
                        else:
                            action = ("ALREADY_INSTALLED" if segment == _rule_block(host)
                                      else "UPGRADE")
                    except (ValueError, InstallError):
                        action = "CONFLICT_MODIFIED"
            else:
                action = "CONFLICT_MODIFIED" if recorded is not None else "APPEND"
    else:
        action = _file_action(rule_target, _digest(_rules()), state["files"].get(rule_rel))
    plans[rule_rel] = {"action": action, "sha256": _digest(_rule_block(host) if append else _rules())}
    # Upstream slash commands (Claude .md / Gemini .toml only). They share
    # the files plan (same conflict rules, same state file) so verify() and
    # uninstall() cover them without extra machinery.
    plans.update(_command_plans(host, project, state))
    skill_plans = {}
    if skills_dir:
        target = _safe(Path(skills_dir) if host == "hermes" else project / skills_dir)
        for skill in SKILLS:
            skill_plans[skill] = skill_installer.inspect(
                quick_install.skill_source(skill), target="directory", root=target)
    problems = [f"{name}: {p['action']}" for name, p in plans.items()
                if p["action"].startswith("CONFLICT")]
    problems.extend(f"{name}: {p['action']}" for name, p in skill_plans.items()
                    if p["action"].startswith("conflict"))
    return {
        "host": host, "scope": scope, "project": str(project),
        "rule_path": str(rule_target), "role_format": (
            "native-markdown" if host not in ("hermes", "generic") else "handoff-reference"),
        "role_activation": "NOT_RUN",
        "skills_root": str(target) if skills_dir else None,
        "skills_status": "PREVIEW" if skills_dir else "REQUIRES_EXPLICIT_HERMES_SKILLS_ROOT",
        "files": plans, "skills": skill_plans,
        "conflicts": problems, "status": "CONFLICT" if problems else "PREVIEW",
    }


def install(host, project=None, apply=False, hermes_skills_root=None, scope="project"):
    if host == "codex":
        return quick_install.execute(apply=apply)
    plan = inspect(host, project, hermes_skills_root, scope)
    if not apply or plan["conflicts"]:
        return plan
    project = Path(plan["project"])
    rule_rel, agent_dir, _ = (USER_FILES[host] if scope == "user" else FILES[host])
    state_file = _state_file(project, host)
    state = _read_state(state_file)
    new_state = {"schema": 1, "files": dict(state["files"]), "rule": state.get("rule")}
    changed = []
    completed_skills = []
    try:
        for rel, detail in plan["files"].items():
            path = _safe(project / rel)
            action = detail["action"]
            if action == "ALREADY_INSTALLED":
                continue
            before = path.read_bytes() if path.exists() else None
            if rel == rule_rel and host in APPEND_RULES:
                if before is None:
                    data = _rule_block(host)
                elif action == "APPEND":
                    data = before + (b"" if before.endswith(b"\n") else b"\n") + _rule_block(host)
                else:
                    left, _, right = _split_rule(before, host)
                    data = left + _rule_block(host) + right
                new_state["rule"] = {"sha256": _digest(_rule_block(host))}
            else:
                if host in COMMANDS and rel.startswith(COMMANDS[host] + "/"):
                    # Upstream slash command: bytes come from the vendored
                    # pack, never generated. rel doubles as the vendored
                    # path under vendor/addy-agent-skills/.
                    data = (_vendor_root() / rel).read_bytes()
                else:
                    name = next((n for n in ROLES if rel.endswith("/aka_" + n + ".md")), None)
                    data = _rules() if rel == rule_rel else _role(name, host)
                new_state["files"][rel] = _digest(data)
            _atomic_write(path, data)
            changed.append((path, before))
        if plan["skills_root"]:
            skills_root = _safe(Path(plan["skills_root"]))
            for skill in SKILLS:
                action = plan["skills"][skill]["action"]
                if action == "already_installed":
                    continue
                skill_installer.install(quick_install.skill_source(skill),
                                        target="directory",
                                        root=skills_root, apply=True)
                completed_skills.append((skill, action))
        _atomic_write(state_file, (json.dumps(new_state, ensure_ascii=True,
                                               sort_keys=True, indent=2) + "\n").encode("utf-8"))
    except Exception:
        # Roll back our own file writes if any phase fails. Any skill rollback
        # failure must not be hidden; owned installer state remains inspectable.
        for skill, action in reversed(completed_skills):
            try:
                if action == "install":
                    skill_installer.remove(skill, target="directory",
                                           root=plan["skills_root"], apply=True)
                elif action == "upgrade":
                    skill_installer.rollback(skill, target="directory",
                                             root=plan["skills_root"], apply=True)
            except (OSError, ValueError):
                pass
        for path, before in reversed(changed):
            if before is None:
                if path.is_file():
                    path.unlink()
            else:
                _atomic_write(path, before)
        raise
    return verify(host, None if scope == "user" else project,
                  hermes_skills_root, scope=scope)


def verify(host, project=None, hermes_skills_root=None, scope="project"):
    if host == "codex":
        return {"host": host, "status": "USE_CODEX_NATIVE_VERIFY",
                "hint": "Run python -m tools.quick_install --interactive"}
    plan = inspect(host, project, hermes_skills_root, scope)
    if plan["status"] == "CONFLICT":
        return {"host": host, "status": "FAIL", "conflicts": plan["conflicts"]}
    if any(x["action"] != "ALREADY_INSTALLED" for x in plan["files"].values()):
        return {"host": host, "status": "NOT_INSTALLED", "activation": "NOT_RUN"}
    if plan["skills_root"]:
        if any(x["action"] != "already_installed" for x in plan["skills"].values()):
            return {"host": host, "status": "NOT_INSTALLED", "activation": "NOT_RUN"}
    return {"host": host, "status": "FILES_VERIFIED",
            "rules": "PASS", "roles": "FILES_PRESENT",
            "skills": ("PASS" if plan["skills_root"] else "NOT_INSTALLED"),
            "loaded": "NOT_RUN", "agent_spawn": "NOT_RUN",
            "dual_engine": "CODEX_ONLY_RUNTIME",
            "next": "Restart the host and verify native role selection and actual threads."}



def uninstall(host, project=None, apply=False, hermes_skills_root=None,
              scope="project"):
    """Remove only our verified files and managed rule block; archive owned Skills."""
    if host == "codex":
        raise InstallError("Use existing Codex component uninstall commands")
    plan = inspect(host, project, hermes_skills_root, scope)
    if plan["conflicts"]:
        return {"host": host, "status": "CONFLICT", "conflicts": plan["conflicts"]}
    if any(x["action"] != "ALREADY_INSTALLED" for x in plan["files"].values()):
        return {"host": host, "status": "NOT_INSTALLED"}
    if plan["skills_root"] and any(x["action"] != "already_installed"
                                    for x in plan["skills"].values()):
        return {"host": host, "status": "NOT_INSTALLED"}
    if not apply:
        return {"host": host, "status": "UNINSTALL_PREVIEW",
                "managed_paths": list(plan["files"]), "skills": list(plan["skills"])}
    root = Path(plan["project"])
    state_path = _state_file(root, host)
    rule_rel, _, _ = USER_FILES[host] if scope == "user" else FILES[host]
    before_state = state_path.read_bytes()
    changed = []
    uninstalled_skills = []
    try:
        for rel in plan["files"]:
            target = _safe(root / rel)
            before = target.read_bytes()
            if rel == rule_rel and host in APPEND_RULES:
                left, segment, right = _split_rule(before, host)
                after = left + right
                if not after:
                    target.unlink()
                else:
                    _atomic_write(target, after)
            else:
                target.unlink()
            changed.append((target, before))
        if plan["skills_root"]:
            for skill in SKILLS:
                skill_installer.remove(skill, target="directory",
                                       root=plan["skills_root"], apply=True)
                uninstalled_skills.append(skill)
        state_path.unlink()
    except Exception:
        for target, before in reversed(changed):
            _atomic_write(target, before)
        for skill in uninstalled_skills:
            try:
                skill_installer.install(quick_install.skill_source(skill),
                                        target="directory",
                                        root=plan["skills_root"], apply=True)
            except (OSError, ValueError):
                pass
        _atomic_write(state_path, before_state)
        raise
    return {"host": host, "status": "UNINSTALLED",
            "removed_managed_files": len(changed),
            "archived_skills": uninstalled_skills,
            "host_activation": "NOT_RUN"}


def main(argv=None):
    p = argparse.ArgumentParser(description="AKA.CRISTI universal host project adapter")
    p.add_argument("action", choices=("preview", "install", "verify", "uninstall"))
    p.add_argument("--host", choices=HOSTS, required=True)
    p.add_argument("--scope", choices=("project", "user"), default="project")
    p.add_argument("--project", type=Path)
    p.add_argument("--hermes-skills-root", type=Path,
                   help="Explicit authorized Hermes user skills folder (e.g. ~/.hermes/skills)")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--interactive", action="store_true")
    args = p.parse_args(argv)
    if args.interactive and args.apply:
        p.error("Choose --apply or --interactive")
    try:
        if args.action == "uninstall":
            preview = uninstall(args.host, args.project,
                                hermes_skills_root=args.hermes_skills_root,
                                scope=args.scope)
            if preview["status"] != "UNINSTALL_PREVIEW":
                report = preview
            elif args.apply or args.interactive:
                consent = args.apply
                if args.interactive:
                    print(json.dumps(preview, ensure_ascii=True, indent=2), flush=True)
                    try:
                        consent = input("Type UNINSTALL to remove CHEF managed config: ").strip() == "UNINSTALL"
                    except (EOFError, KeyboardInterrupt):
                        consent = False
                report = (uninstall(args.host, args.project, apply=True,
                                    hermes_skills_root=args.hermes_skills_root,
                                    scope=args.scope) if consent else {"status": "CANCELLED"})
            else:
                report = preview
        elif args.action == "verify":
            report = verify(args.host, args.project, args.hermes_skills_root,
                            scope=args.scope)
        else:
            plan = inspect(args.host, args.project, args.hermes_skills_root,
                           scope=args.scope)
            if plan.get("conflicts"):
                report = plan
            elif args.action == "preview" or not (args.apply or args.interactive):
                report = plan
            elif args.interactive:
                print(json.dumps(plan, ensure_ascii=True, indent=2), flush=True)
                try:
                    approved = input("Install CHEF managed rules, roles and Skills? Type INSTALL: ").strip()
                except (EOFError, KeyboardInterrupt):
                    approved = ""
                report = (install(args.host, args.project, apply=True,
                                  hermes_skills_root=args.hermes_skills_root,
                                  scope=args.scope)
                          if approved == "INSTALL" else {"status": "CANCELLED"})
            else:
                report = install(args.host, args.project, apply=True,
                                 hermes_skills_root=args.hermes_skills_root,
                                 scope=args.scope)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0 if report.get("status") not in ("CONFLICT", "FAIL", "NOT_INSTALLED") else 1
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__},
                         ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
