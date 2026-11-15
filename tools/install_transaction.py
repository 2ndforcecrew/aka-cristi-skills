"""Consent-first local GUI transaction. No downloads, dependencies or live calls.

Journals contain private local configuration backups. Never publish a journal.
Rollback refuses if managed paths changed after installation. It cannot lock out
other programs editing configuration concurrently; close other installers first.
"""
import base64
import difflib
import hashlib
import json
import itertools
import os
import re
import stat
import uuid
from pathlib import Path

from tools import chef_global_rules, codex_subagents, skill_installer

SKILLS = ("chef-orchestrator", "verified-change-loop", "feature-journey-map", "skill-evaluation-gate")
MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 2000


class TransactionError(ValueError):
    pass


class Cancelled(Exception):
    pass


def _safe(path):
    p = Path(path).expanduser().absolute()
    for parent in (p, *p.parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise TransactionError("Linked filesystem paths are not supported")
        if parent.exists():
            info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise TransactionError("Linked filesystem paths are not supported")
    return p


def _roots(home, skills):
    home, skills = _safe(home), _safe(skills)
    if home == skills or home in skills.parents or skills in home.parents:
        raise TransactionError("Codex and Skills roots must be separate directories")
    return {"home": home, "skills": skills}


def _scopes(roots):
    return [roots["home"] / "AGENTS.md", roots["home"] / ".aka-chef-backups",
            roots["home"] / ".aka-chef-subagents",
            *(roots["home"] / "agents" / (x + ".toml") for x in codex_subagents.ROLE_NAMES),
            roots["skills"] / skill_installer.STATE,
            *(roots["skills"] / x for x in SKILLS)]


def _key(path, roots):
    for name, root in roots.items():
        if path.is_relative_to(root):
            return name + "/" + path.relative_to(root).as_posix()
    raise TransactionError("Unexpected transaction path")


def _snapshot(roots):
    files = {}
    total = 0
    for scope in _scopes(roots):
        _safe(scope)
        if not scope.exists():
            continue
        paths = itertools.chain((scope,), scope.rglob("*") if scope.is_dir() else ())
        for path in paths:
            _safe(path)
            if len(files) >= MAX_FILES:
                raise TransactionError("Configuration backup exceeds safe size limits")
            if path.is_dir():
                files[_key(path, roots)] = {"directory": True, "mode": stat.S_IMODE(path.stat().st_mode)}
                continue
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                raise TransactionError("Unsupported or oversized configuration file")
            data = path.read_bytes()
            total += len(data)
            if total > MAX_BYTES or len(files) >= MAX_FILES:
                raise TransactionError("Configuration backup exceeds safe size limits")
            files[_key(path, roots)] = {
                "data": base64.b64encode(data).decode("ascii"),
                "mode": stat.S_IMODE(path.stat().st_mode),
            }
    return files


def _fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def _source_fingerprint(source):
    paths = [source / "templates" / "AGENTS.global.md",
             *(source / "agents" / (x + ".toml") for x in codex_subagents.ROLE_NAMES)]
    for name in SKILLS:
        paths.extend(sorted((source / "skills" / name).rglob("*")))
    h = hashlib.sha256()
    for path in paths:
        _safe(path)
        if path.is_dir():
            continue
        if not path.is_file():
            raise TransactionError("Local source is incomplete; obtain a complete verified release")
        h.update(path.relative_to(source).as_posix().encode() + b"\0" + path.read_bytes())
    return h.hexdigest()


def preview(source, home, skills):
    source = _safe(source)
    roots = _roots(home, skills)
    template = source / "templates" / "AGENTS.global.md"
    source_hash = _source_fingerprint(source)
    global_plan = chef_global_rules.plan("install", template, roots["home"])
    role_plans = [codex_subagents.plan(x, roots["home"], source / "agents")
                  for x in codex_subagents.ROLE_NAMES]
    skill_plans = [skill_installer.inspect(source / "skills" / x, "directory", roots["skills"])
                   for x in SKILLS]
    if global_plan["state"] == "conflict_modified" or any(
            str(p.get("action", "")).lower().startswith("conflict")
            for p in role_plans + skill_plans):
        raise TransactionError("Existing edited or unmanaged configuration conflicts; nothing was changed")
    old = chef_global_rules.read_old(roots["home"] / "AGENTS.md")
    block = chef_global_rules.managed_block(template)
    new = old if global_plan["state"] == "already_installed" else (
        chef_global_rules.append_block(old, block))
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                     fromfile="AGENTS.md before", tofile="AGENTS.md after"))
    return {"source": str(source), "home": str(roots["home"]), "skills": str(roots["skills"]),
            "fingerprint": _fingerprint(_snapshot(roots)), "source_fingerprint": source_hash,
            "rules_diff": diff or "No AGENTS.md change required.\n", "rules_after": new,
            "additions": role_plans + skill_plans, "activation": "NOT_RUN"}


def _save(path, value):
    _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    _safe(temp)
    with open(temp, "w", encoding="utf-8") as f:
        if os.name != "nt":
            os.chmod(temp, 0o600)
        json.dump(value, f, indent=2, sort_keys=True)
    os.replace(temp, path)


def _restore(roots, before, after):
    if _snapshot(roots) != after:
        raise TransactionError("Rollback blocked: installed files changed; preserve edits and inspect local backup")
    allowed_scopes = _scopes(roots)
    resolved = {}
    for key in set(before) | set(after):
        label, relative = key.split("/", 1)
        if label not in roots or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise TransactionError("Invalid rollback path")
        path = _safe(roots[label] / relative)
        if not any(path == s or s in path.parents for s in allowed_scopes):
            raise TransactionError("Unexpected rollback path")
        resolved[key] = path
    # Validate/decode the complete backup before making any restoration changes.
    decoded = {}
    for key, entry in before.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("mode"), int):
            raise TransactionError("Invalid rollback entry")
        if not entry.get("directory"):
            decoded[key] = base64.b64decode(entry["data"], validate=True)
    # Remove only files the installation created. Directories are removed only
    # when absent from the pre-install snapshot and empty.
    for key, path in resolved.items():
        if key not in before and not after[key].get("directory"):
            path.unlink()
    for key, path in sorted(resolved.items(), key=lambda pair: len(pair[1].parts), reverse=True):
        if key not in before and after[key].get("directory"):
            path.rmdir()
    for key, entry in sorted(before.items(), key=lambda pair: len(resolved[pair[0]].parts)):
        path = resolved[key]
        if entry.get("directory"):
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, entry["mode"])
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(".aka-gui-restore-" + uuid.uuid4().hex)
            tmp.write_bytes(decoded[key])
            os.chmod(tmp, entry["mode"])
            os.replace(tmp, path)


def _bytes(entry):
    return base64.b64decode(entry["data"], validate=True)


def _expect_file(expected, after, key, data):
    actual = after.get(key)
    if not isinstance(actual, dict) or actual.get("directory") or _bytes(actual) != data:
        raise TransactionError("Step output differs from expected contents")
    expected[key] = {"data": base64.b64encode(data).decode("ascii"), "mode": actual["mode"]}


def _expect_dir(expected, after, key):
    if key not in expected:
        if not after.get(key, {}).get("directory"):
            raise TransactionError("Expected managed directory missing")
        expected[key] = after[key]


def _guard_step(before, after, kind, name, result, source, plan, roots):
    """Allow only this operation's known outputs; unrelated edits block recovery."""
    if not result.get("applied"):
        if before != after:
            raise TransactionError("Unexpected concurrent configuration changes")
        return
    expected = dict(before)
    if kind == "rules":
        _expect_file(expected, after, "home/AGENTS.md", plan["rules_after"].encode("utf-8"))
        if result.get("backup"):
            key = _key(Path(result["backup"]), roots)
            if not key.startswith("home/.aka-chef-backups/AGENTS-"):
                raise TransactionError("Unexpected backup location")
            _expect_dir(expected, after, "home/.aka-chef-backups")
            _expect_file(expected, after, key, _bytes(before["home/AGENTS.md"]))
    elif kind == "skill":
        prefix = "skills/" + name
        old_tree = {key: value for key, value in before.items() if key == prefix or key.startswith(prefix + "/")}
        for key in old_tree:
            expected.pop(key)
        src = source / "skills" / name
        _expect_dir(expected, after, prefix)
        for path in src.rglob("*"):
            key = prefix + "/" + path.relative_to(src).as_posix()
            if path.is_dir():
                _expect_dir(expected, after, key)
            else:
                _expect_file(expected, after, key, path.read_bytes())
        state_dir = "skills/" + skill_installer.STATE
        _expect_dir(expected, after, state_dir)
        _expect_dir(expected, after, state_dir + "/backups")
        state_key = state_dir + "/state.json"
        state = json.loads(_bytes(before[state_key])) if state_key in before else {"version": 1, "installed": {}}
        backup = result.get("backup")
        if backup:
            if not re.fullmatch(re.escape(name) + r"-[a-f0-9]{32}", backup):
                raise TransactionError("Unexpected backup name")
            for key, entry in old_tree.items():
                backup_key = state_dir + "/backups/" + backup + key[len(prefix):]
                if entry.get("directory"):
                    _expect_dir(expected, after, backup_key)
                else:
                    _expect_file(expected, after, backup_key, _bytes(entry))
        state["installed"][name] = {"sha256": result["sha256"], "backup": backup}
        if json.loads(_bytes(after[state_key])) != state:
            raise TransactionError("Unexpected installer state change")
        _expect_file(expected, after, state_key, _bytes(after[state_key]))
    else:
        target = "home/agents/" + name + ".toml"
        raw = codex_subagents.source_for(name, source / "agents")
        _expect_file(expected, after, target, raw.replace("\n", os.linesep).encode("utf-8"))
        state_dir = "home/" + codex_subagents.STATE
        _expect_dir(expected, after, state_dir)
        state_key = state_dir + "/state.json"
        state = json.loads(_bytes(before[state_key])) if state_key in before else {"version": 1, "installed": {}}
        state["installed"][name] = codex_subagents.digest(raw)
        if json.loads(_bytes(after[state_key])) != state:
            raise TransactionError("Unexpected role state change")
        _expect_file(expected, after, state_key, _bytes(after[state_key]))
        if result.get("backup"):
            key = _key(Path(result["backup"]), roots)
            if not re.fullmatch(re.escape(state_dir + "/" + name + "-") + r"[a-f0-9]{32}\.toml", key):
                raise TransactionError("Unexpected role backup")
            _expect_file(expected, after, key, _bytes(before[target]))
    if expected != after:
        raise TransactionError("Unrecognized concurrent change; rollback requires manual review")


def install(plan, consent=False, cancel=None, progress=None):
    if not consent:
        raise TransactionError("Explicit consent is required")
    current = preview(plan["source"], plan["home"], plan["skills"])
    if current["fingerprint"] != plan["fingerprint"] or current["source_fingerprint"] != plan["source_fingerprint"]:
        raise TransactionError("Source or configuration changed since preview; preview again")
    roots = _roots(plan["home"], plan["skills"])
    before = _snapshot(roots)
    journal = roots["home"] / ".aka-chef-gui" / uuid.uuid4().hex / "journal.json"
    record = {"version": 1, "home": str(roots["home"]), "skills": str(roots["skills"]),
              "before": before, "after": before, "status": "INSTALLING"}
    def emit(event):
        if progress:
            progress(event)
    def checkpoint():
        if cancel is not None and cancel.is_set():
            raise Cancelled()
    _save(journal, record)
    source = Path(plan["source"])
    known_after = before
    def commit_step(kind, name, result):
        nonlocal known_after
        observed = _snapshot(roots)
        _guard_step(known_after, observed, kind, name, result, source, current, roots)
        known_after = observed
        record["after"] = known_after
        _save(journal, record)
    try:
        checkpoint()
        result = chef_global_rules.apply("install", source / "templates" / "AGENTS.global.md",
                                        roots["home"], confirmed=True)
        commit_step("rules", "", result)
        emit("rules_installed")
        for name in SKILLS:
            checkpoint()
            result = skill_installer.install(source / "skills" / name,
                                             "directory", roots["skills"], apply=True)
            commit_step("skill", name, result)
            emit("skill_installed:" + name)
        for name in codex_subagents.ROLE_NAMES:
            checkpoint()
            result = codex_subagents.install(name, roots["home"], source / "agents", apply=True)
            commit_step("role", name, result)
            emit("role_installed:" + name)
        checkpoint()
        if chef_global_rules.plan("verify", Path(plan["source"]) / "templates" / "AGENTS.global.md",
                                  roots["home"])["state"] != "PASS":
            raise TransactionError("Global rules verification failed")
        for name in SKILLS:
            skill_installer.verify(name, "directory", roots["skills"])
        for name in codex_subagents.ROLE_NAMES:
            if codex_subagents.verify(name, roots["home"], Path(plan["source"]) / "agents")["integrity"] != "PASS":
                raise TransactionError("Role verification failed")
        if _snapshot(roots) != known_after:
            raise TransactionError("Configuration changed during verification")
        record["after"] = known_after
        record["status"] = "FILES_VERIFIED"
        _save(journal, record)
        emit("files_verified_activation_not_run")
        return {"status": record["status"], "activation": "NOT_RUN", "journal": str(journal)}
    except Exception as exc:
        record["after"] = known_after
        record["status"] = "ROLLBACK_REQUIRED"
        _save(journal, record)
        try:
            if _snapshot(roots) != known_after:
                raise TransactionError("Unrecognized changes; preserve local backup")
            _restore(roots, before, known_after)
        except (ValueError, OSError):
            emit("blocked_rollback_required")
            return {"status": "BLOCKED_ROLLBACK_REQUIRED", "activation": "NOT_RUN",
                    "journal": str(journal), "error_type": type(exc).__name__}
        record["status"] = "CANCELLED_ROLLED_BACK" if isinstance(exc, Cancelled) else "FAILED_ROLLED_BACK"
        _save(journal, record)
        emit(record["status"].lower())
        return {"status": record["status"], "activation": "NOT_RUN", "journal": str(journal),
                "error_type": type(exc).__name__}


def rollback(journal, consent=False):
    if not consent:
        raise TransactionError("Explicit rollback consent is required")
    journal = _safe(journal)
    record = json.loads(journal.read_text(encoding="utf-8"))
    if record.get("version") != 1 or record.get("status") != "FILES_VERIFIED":
        raise TransactionError("Journal is not a completed, reversible installation")
    roots = _roots(record["home"], record["skills"])
    if journal.parent.parent != roots["home"] / ".aka-chef-gui" or journal.name != "journal.json":
        raise TransactionError("Unexpected journal location")
    _restore(roots, record["before"], record["after"])
    record["status"] = "ROLLED_BACK"
    _save(journal, record)
    return {"status": "ROLLED_BACK", "activation": "NOT_RUN", "journal": str(journal)}
