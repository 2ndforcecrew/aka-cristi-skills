"""``aka-skills update``: pull latest main, re-sync installed hosts.

Solves the snapshot problem: a one-time install goes stale when the repo
updates. ``update`` pulls the repo to latest ``main`` (``git pull
--ff-only``) and re-syncs every host that was already installed.

Design (see the plan in the repo review notes, 2026-11-25):

- Preview-first, like ``install``: no flags means a read-only preview
  report (zero writes). ``--apply`` executes; ``--interactive`` asks for
  a literal ``YES`` after the preview. Read-only git commands only in
  preview (``rev-parse``, ``status --porcelain``); ``git pull`` runs
  only in the apply phase, after approval.
- Discovery reuses the two existing receipt mechanisms — the skill
  state file (``<skills-root>/.aka-skill-installer/state.json``) and the
  host state file (``<project>/.aka-chef-install/<host>.json``). No
  third receipt format is invented.
- Adoption (D3): a WorkBuddy skills root with no state file but
  byte-identical content (SHA-256 match per skill) is treated as ours:
  ``--apply`` writes the state record first (adopt, no file rewrite),
  then upgrades normally. Mismatched content is ``conflict_unmanaged``
  and is never silently overwritten.
- Legacy (D1): a ``.codebuddy`` install is reported only
  (``legacy_codebuddy_install``) — never read as a source, never
  written, never deleted. A state file whose recorded paths start with
  ``.codebuddy/`` does not count as proof of install for the new
  ``.workbuddy`` paths.
- Dirty tree / non-main branch / pull failure: hard stop, exit 1, no
  sync from a stale tree (a downgrade). No ``--force`` in v1.
- ``--no-pull`` skips git entirely and syncs from the local tree (for
  non-git source copies and offline use).
- WorkBuddy scope note: project-scope ``.codebuddy/`` paths are
  untouched in v1 (whether WorkBuddy reads them is unverified); only
  the user-level path moved to ``~/.workbuddy/*``.
- CLI-only in v1: no MCP update tool.
- This module holds the update logic; ``aka_skills.cli`` only parses
  arguments and prints the report (thin-wrapper architecture).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from aka_skills import repo as repo_mod
from tools import quick_install, skill_installer, universal_chef

BRANCH = "main"
REMOTE = "origin"
GIT_TIMEOUT = 900

_RESTART_APP = "APP_RESTART_REQUIRED"
_RESTART_SESSION = "SESSION_RESTART"


class UpdateError(ValueError):
    """Fatal update error (git pre-checks, pull failure, bad usage)."""


# ---------------------------------------------------------------- git layer

def git_available() -> bool:
    return shutil.which("git") is not None


def _git(root: Path, args: list[str], timeout: int = GIT_TIMEOUT):
    """Run git with an argv list (never shell=True), capturing output."""
    return subprocess.run(
        ["git", *args], cwd=str(root),
        capture_output=True, text=True, timeout=timeout,
    )


def _head_sha(root: Path) -> str | None:
    try:
        cp = _git(root, ["rev-parse", "HEAD"], timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return cp.stdout.strip() if cp.returncode == 0 else None


def _current_branch(root: Path) -> str | None:
    try:
        cp = _git(root, ["rev-parse", "--abbrev-ref", "HEAD"], timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return cp.stdout.strip() if cp.returncode == 0 else None


def _tracked_modified(root: Path) -> list[str]:
    """Tracked files with staged/unstaged changes (untracked ``??`` excluded)."""
    try:
        cp = _git(root, ["status", "--porcelain"], timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"git status failed: {exc}")
    if cp.returncode != 0:
        raise UpdateError(f"git status failed: {cp.stderr.strip()}")
    return [
        line for line in cp.stdout.splitlines()
        if line and not line.startswith("??") and not line.startswith("!!")
    ]


def precheck(root: Path, branch: str = BRANCH, no_pull: bool = False) -> dict:
    """Read-only git pre-checks. Returns branch/HEAD info.

    Raises UpdateError on: git missing (unless --no-pull), not a git
    checkout (unless --no-pull), non-main branch, dirty tracked tree.
    Never writes to the repo.
    """
    root = Path(root).resolve()
    if not git_available():
        if no_pull:
            return {"branch": None, "before": None, "is_checkout": False}
        raise UpdateError(
            "GIT_MISSING: git is not on PATH; install git or re-run with "
            "--no-pull to sync from the local tree"
        )
    cp = _git(root, ["rev-parse", "--show-toplevel"], timeout=30)
    if cp.returncode != 0:
        if no_pull:
            return {"branch": None, "before": None, "is_checkout": False}
        raise UpdateError(
            "NOT_A_GIT_CHECKOUT: this repo root is not a git checkout; "
            "git clone the repo and run update there, or use --no-pull "
            "to sync from the local tree"
        )
    current = _current_branch(root)
    if current != branch:
        raise UpdateError(
            f"NOT_ON_MAIN: current branch is {current!r}; run "
            f"`git checkout {branch}` first (update never switches "
            "branches automatically)"
        )
    modified = _tracked_modified(root)
    if modified:
        raise UpdateError(
            f"DIRTY_TREE: {len(modified)} tracked file(s) modified "
            f"({modified[0][:80]}...); commit or stash before updating "
            "(update has no --force)"
        )
    return {"branch": current, "before": _head_sha(root), "is_checkout": True}


def pull_repo(root: Path, remote: str = REMOTE, branch: str = BRANCH) -> dict:
    """Pull latest branch (write phase only). Raises on any failure."""
    before = _head_sha(root)
    try:
        cp = _git(root, ["pull", "--ff-only", remote, branch])
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"git pull failed: {exc}; not syncing from a stale tree")
    if cp.returncode != 0:
        raise UpdateError(
            "git pull failed; not syncing from a stale tree:\n"
            + cp.stderr.strip()
        )
    after = _head_sha(root)
    return {
        "pull": "UPDATED" if before != after else "ALREADY_UP_TO_DATE",
        "before": before,
        "after": after,
    }


# ------------------------------------------------------------- legacy (D1)

def _state_is_legacy(state_path: Path) -> bool:
    """True when a host state file records ``.codebuddy/`` paths."""
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return False
    files = data.get("files", {}) if isinstance(data, dict) else {}
    return any(
        isinstance(p, str) and p.startswith(".codebuddy/") for p in files
    )


def detect_legacy(home: Path | None = None) -> dict | None:
    """Report a legacy ``.codebuddy`` install.

    Only the two state files are read (existence + recorded skill
    names); legacy skill content is never hashed, used, written, or
    deleted.
    """
    home = Path(home) if home is not None else Path.home()
    paths: list[str] = []
    skills: list[str] = []
    state_path = home / ".aka-chef-install" / "workbuddy.json"
    if state_path.is_file():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            files = data.get("files", {}) if isinstance(data, dict) else {}
            legacy_rels = sorted(
                p for p in files
                if isinstance(p, str) and p.startswith(".codebuddy/")
            )
        except (OSError, ValueError, UnicodeError):
            legacy_rels = []
            paths.append(str(state_path))
        if legacy_rels:
            paths.append(str(state_path))
            for rel in legacy_rels:
                parts = rel.split("/")
                if len(parts) >= 3 and parts[1] == "skills":
                    skills.append(parts[2])
    skill_state = home / ".codebuddy" / "skills" / ".aka-skill-installer" / "state.json"
    if skill_state.is_file():
        paths.append(str(skill_state))
        try:
            data = json.loads(skill_state.read_text(encoding="utf-8"))
            installed = data.get("installed", {}) if isinstance(data, dict) else {}
            skills.extend(sorted(installed))
        except (OSError, ValueError, UnicodeError):
            pass
    if not paths:
        return None
    return {
        "paths": paths,
        "skills": sorted(set(skills)),
        "note": (
            "Legacy .codebuddy install detected. Only the two state "
            "files are read (existence + recorded skill names); legacy "
            "skill content is never hashed, used, written, or deleted. "
            "After confirming the "
            f".workbuddy install works, you may manually delete the "
            f"aka-chef managed files under {home / '.codebuddy'} "
            "(or leave them alone)."
        ),
    }


# ------------------------------------------------------------ adoption (D3)

def _adoption_check(source: Path, skills_root: Path) -> str:
    """Read-only adoption check for one skill.

    Returns "adopted" when the installed directory exists with no state
    record but byte-identical content, "conflict_unmanaged" when the
    content differs, "install" when absent, "already_installed" when a
    state record already exists. Writes nothing.
    """
    info = skill_installer.package(source)
    destination = skill_installer.root_for("directory", skills_root)
    state = skill_installer.load_state(destination)
    name = info["name"]
    installed = destination / name
    if installed.is_symlink():
        raise skill_installer.InstallError("symlink installed skill")
    if not installed.exists():
        return "install"
    if state["installed"].get(name):
        return "already_installed"
    if skill_installer.package(installed)["sha256"] != info["sha256"]:
        return "conflict_unmanaged"
    return "adopted"


# ------------------------------------------------------------- discovery

def _target_key(host: str, scope: str, project: Path | None) -> str:
    key = f"{host}:{scope}"
    if project is not None:
        key += f":{project}"
    return key


def _codex_preview(skills_root: Path | None = None) -> dict:
    """Codex install preview, built from the primitive plans.

    Mirrors quick_install.execute()'s planning (including the resolve()
    of caller-supplied paths) but never raises on conflicts, so the
    caller can report them per target instead of aborting discovery.
    """
    if skills_root is not None:
        skills_root = Path(skills_root).resolve()
    target = "directory" if skills_root is not None else "codex"
    from tools import chef_global_rules, codex_subagents

    return {
        "global_rules": chef_global_rules.plan(
            "install", quick_install.TEMPLATE, None
        ),
        "agents": [
            codex_subagents.plan(role, None)
            for role in codex_subagents.ROLE_NAMES
        ],
        "skills": [
            skill_installer.inspect(
                quick_install.ROOT / "skills" / skill, target, skills_root
            )
            for skill in quick_install.SKILLS
        ],
    }


def _codex_status(plan: dict) -> str:
    """Derive a codex target status from its preview plans."""
    rules_state = plan["global_rules"]["state"]
    agent_actions = [a["action"] for a in plan["agents"]]
    skill_actions = [s["action"] for s in plan["skills"]]
    if (
        rules_state == "conflict_modified"
        or any(a.startswith("CONFLICT") for a in agent_actions)
        or any(a.startswith("conflict") for a in skill_actions)
    ):
        return "CONFLICT"
    installed = (
        rules_state == "already_installed"
        or any(a in ("ALREADY_INSTALLED", "UPGRADE") for a in agent_actions)
        or any(a in ("already_installed", "upgrade") for a in skill_actions)
    )
    if not installed:
        return "NOT_INSTALLED"
    if (
        rules_state == "already_installed"
        and all(a == "ALREADY_INSTALLED" for a in agent_actions)
        and all(a == "already_installed" for a in skill_actions)
    ):
        return "NO_CHANGE"
    return "UPDATED"


def _universal_preview(host: str, scope: str, project: Path | None,
                       repo_root: Path, skills_root: Path | None,
                       workbuddy_skills_root: Path | None) -> dict:
    """Inspect one universal host; applies the workbuddy adoption check.

    Returns {"status", "skills", "adopted", "inspect"}.
    """
    hermes_root = skills_root if host == "hermes" else None
    wb_root = (
        skills_root if (host == "workbuddy" and skills_root is not None)
        else workbuddy_skills_root
    )
    plan = universal_chef.inspect(
        host, project, hermes_root, scope,
        workbuddy_skills_root=wb_root,
    )
    skills = {name: detail["action"] for name, detail in plan["skills"].items()}
    adopted: list[str] = []
    if host == "workbuddy" and plan["skills_root"]:
        root = Path(plan["skills_root"])
        for name, action in list(skills.items()):
            if action != "conflict_unmanaged":
                continue
            check = _adoption_check(repo_root / "skills" / name, root)
            if check == "adopted":
                skills[name] = "adopted"
                adopted.append(name)
            # Any other outcome keeps conflict_unmanaged.
    conflicts = list(plan["conflicts"])
    if adopted:
        conflicts = [
            c for c in conflicts
            if not any(c.startswith(name + ":") for name in adopted)
        ]
    file_actions = [d["action"] for d in plan["files"].values()]
    if conflicts:
        status = "CONFLICT"
    elif (
        all(a == "INSTALL" for a in file_actions)
        and all(a == "install" for a in skills.values())
        and not adopted
    ):
        status = "NOT_INSTALLED"
    elif (
        all(a == "ALREADY_INSTALLED" for a in file_actions)
        and all(a == "already_installed" for a in skills.values())
        and not adopted
    ):
        status = "NO_CHANGE"
    else:
        status = "UPDATED"
    return {
        "status": status, "skills": skills, "adopted": adopted,
        "inspect": plan, "conflicts": conflicts,
    }


def discover_targets(repo_root: Path, hosts: list[str] | None = None,
                     scope: str = "user", project: Path | None = None,
                     skills_root: Path | None = None,
                     workbuddy_skills_root: Path | None = None) -> tuple[list[dict], dict | None]:
    """Find installed targets. Returns (targets, legacy).

    - codex: fixed location, always a candidate (reported
      NOT_INSTALLED when nothing is there).
    - user scope: ``~/.aka-chef-install/*.json`` host states plus the
      default ``~/.workbuddy/skills`` content/state check.
    - project scope: only when ``--project`` is given; scans
      ``<project>/.aka-chef-install/*.json``. Project discovery is not
      filtered by ``--host`` (``--host codex --project P`` updates codex
      plus every host found in P).
    - A legacy ``.codebuddy`` state never counts as install proof.
    """
    home = Path.home()
    legacy = detect_legacy(home)
    wanted = set(hosts) if hosts else None
    targets: list[dict] = []
    if scope not in ("project", "user"):
        raise UpdateError(f"Invalid scope: {scope!r}")
    if scope == "project" and project is None:
        raise UpdateError("Project-scoped update requires --project")

    # --- codex (fixed location) ---
    if wanted is None or "codex" in wanted:
        codex_root = skills_root if wanted == {"codex"} else None
        try:
            plan = _codex_preview(codex_root)
            status = _codex_status(plan)
            skills = {s["name"]: s["action"] for s in plan["skills"]}
            error = None
        except (OSError, ValueError, UnicodeError) as exc:
            plan, status, skills = None, "FAIL", {}
            error = f"{type(exc).__name__}: {exc}"
        targets.append({
            "key": "codex:user", "host": "codex", "scope": "user",
            "project": None,
            "skills_root": str(codex_root) if codex_root is not None else None,
            "kind": "codex",
            "status": status, "skills": skills, "adopted": [],
            "verification": "NOT_RUN",
            "restart": _RESTART_SESSION,
            "error": error, "_preview": plan,
        })

    # --- user-scope universal hosts ---
    if scope == "user":
        state_dir = home / universal_chef.STATE_DIR
        state_hosts: list[str] = []
        if state_dir.is_dir():
            state_hosts = sorted(
                p.stem for p in state_dir.glob("*.json")
                if p.stem in universal_chef.USER_FILES and p.stem != "codex"
            )
        for host in state_hosts:
            if wanted is not None and host not in wanted:
                continue
            state_path = state_dir / (host + ".json")
            if host == "workbuddy" and _state_is_legacy(state_path):
                continue  # legacy state is not proof (D1); adoption below decides
            targets.append(_universal_target(
                repo_root, host, "user", None, skills_root,
                workbuddy_skills_root,
            ))
        # Default workbuddy root (manual sync without a state file).
        if (wanted is None or "workbuddy" in wanted) and not any(
            t["host"] == "workbuddy" and t["scope"] == "user" for t in targets
        ):
            wb_root = workbuddy_skills_root or (home / ".workbuddy" / "skills")
            if wb_root.is_dir() and any(
                (wb_root / skill).exists() for skill in quick_install.SKILLS
            ):
                targets.append(_universal_target(
                    repo_root, "workbuddy", "user", None, skills_root,
                    workbuddy_skills_root,
                ))

    # --- project-scope universal hosts ---
    if project is not None:
        project = Path(project)
        state_dir = project / universal_chef.STATE_DIR
        if state_dir.is_dir():
            for state_path in sorted(state_dir.glob("*.json")):
                host = state_path.stem
                if host not in universal_chef.HOSTS or host == "codex":
                    continue
                if host == "workbuddy" and _state_is_legacy(state_path):
                    continue
                targets.append(_universal_target(
                    repo_root, host, "project", project, skills_root,
                    workbuddy_skills_root,
                ))
    return targets, legacy


def _universal_target(repo_root: Path, host: str, scope: str,
                      project: Path | None, skills_root: Path | None,
                      workbuddy_skills_root: Path | None) -> dict:
    """Build one universal-host target with its preview attached."""
    try:
        preview = _universal_preview(
            host, scope, project, repo_root, skills_root,
            workbuddy_skills_root,
        )
        status, skills = preview["status"], preview["skills"]
        adopted, error = preview["adopted"], None
    except (OSError, ValueError, UnicodeError) as exc:
        preview, status = None, "FAIL"
        skills, adopted = {}, []
        error = f"{type(exc).__name__}: {exc}"
    skills_root_out = None
    if preview is not None and preview["inspect"].get("skills_root"):
        skills_root_out = preview["inspect"]["skills_root"]
    return {
        "key": _target_key(host, scope, project),
        "host": host, "scope": scope,
        "project": str(project) if project is not None else None,
        "skills_root": skills_root_out, "kind": "universal",
        "status": status, "skills": skills, "adopted": adopted,
        "verification": "NOT_RUN",
        "restart": (
            _RESTART_APP if host == "workbuddy" else _RESTART_SESSION
        ),
        "error": error, "_preview": preview,
    }


# ------------------------------------------------------------- apply phase

def _sync_codex(target: dict) -> None:
    """Apply the codex target; updates status/verification in place."""
    skills_root = None
    if target.get("skills_root"):
        skills_root = Path(target["skills_root"])
    try:
        result = quick_install.execute(apply=True, skills_root=skills_root)
    except (OSError, ValueError, UnicodeError) as exc:
        target["status"] = "FAIL"
        target["error"] = f"{type(exc).__name__}: {exc}"
        target["verification"] = "FAIL"
        return
    target["verification"] = (
        "FILES_VERIFIED" if result["status"] == "FILES_VERIFIED" else "FAIL"
    )
    if result["status"] != "FILES_VERIFIED":
        target["status"] = "FAIL"
        return
    actions = target["skills"]
    target["status"] = (
        "UPDATED" if any(a in ("install", "upgrade") for a in actions.values())
        else "NO_CHANGE"
    )


def _sync_universal(target: dict, repo_root: Path,
                    skills_root: Path | None,
                    workbuddy_skills_root: Path | None) -> None:
    """Adopt (workbuddy) then install one universal host target."""
    host, scope = target["host"], target["scope"]
    project = Path(target["project"]) if target["project"] else None
    # 1. Adoption first: write state records for hash-matching content.
    if target["adopted"]:
        root = Path(target["skills_root"])
        for name in target["adopted"]:
            try:
                adopted = skill_installer.adopt(
                    repo_root / "skills" / name, root=root
                )
            except (OSError, ValueError, UnicodeError) as exc:
                target["status"] = "FAIL"
                target["error"] = f"{type(exc).__name__}: {exc}"
                target["verification"] = "FAIL"
                return
            if not adopted["adopted"]:
                target["status"] = "CONFLICT"
                target["error"] = (
                    f"skill {name} changed between preview and apply; "
                    "refusing to overwrite"
                )
                target["verification"] = "NOT_RUN"
                return
    # 2. Install (re-inspects, refuses conflicts, verifies at the end).
    try:
        result = universal_chef.install(
            host, project, apply=True,
            hermes_skills_root=skills_root if host == "hermes" else None,
            scope=scope,
            workbuddy_skills_root=(
                skills_root if (host == "workbuddy" and skills_root is not None)
                else workbuddy_skills_root
            ),
        )
    except (OSError, ValueError, UnicodeError) as exc:
        target["status"] = "FAIL"
        target["error"] = f"{type(exc).__name__}: {exc}"
        target["verification"] = "FAIL"
        return
    status = result.get("status")
    if status == "CONFLICT":
        target["status"] = "CONFLICT"
        target["verification"] = "NOT_RUN"
        return
    if status == "FILES_VERIFIED":
        target["verification"] = "FILES_VERIFIED"
    elif status == "NOT_INSTALLED":
        target["verification"] = "NOT_INSTALLED"
    else:
        target["verification"] = "FAIL"
    if target["verification"] != "FILES_VERIFIED":
        target["status"] = "FAIL"
        return
    actions = target["skills"]
    target["status"] = (
        "UPDATED"
        if target["adopted"]
        or any(a in ("install", "upgrade") for a in actions.values())
        else "NO_CHANGE"
    )


# ------------------------------------------------------------ report flow

def _public_target(target: dict) -> dict:
    out = {k: v for k, v in target.items() if not k.startswith("_")}
    if out.get("error") is None:
        out.pop("error", None)
    return out


def _next_steps(targets: list[dict], legacy: dict | None) -> str:
    parts: list[str] = []
    if any(t["host"] == "workbuddy" for t in targets):
        parts.append(
            "Restart the WorkBuddy app (quit the whole application and "
            "reopen it; a new session is not enough — the skill list "
            "cache only refreshes on app restart). WorkBuddy HotReload "
            "logs file changes, but the skill list still needs an app "
            "restart. Rules/agents synced to ~/.workbuddy are NOT_RUN — "
            "verify after restart whether WorkBuddy loads them."
        )
    if any(t["host"] == "codex" for t in targets):
        parts.append("Open a NEW Codex session to load the updated rules and Skills.")
    other = [t["host"] for t in targets if t["host"] not in ("workbuddy", "codex")]
    if other:
        parts.append(
            "Open a NEW session in each updated host "
            f"({', '.join(sorted(set(other)))}) and verify the updated "
            "rules/Skills/roles loaded."
        )
    if legacy is not None:
        parts.append(legacy["note"])
    if not targets:
        parts.append(
            "No installed hosts found — run `aka-skills install --host "
            "<host> --scope user --interactive` first."
        )
    return " ".join(parts)


def _assemble(status: str, repo_info: dict, targets: list[dict],
              legacy: dict | None, note: str | None = None) -> dict:
    report: dict = {
        "status": status,
        "repo": repo_info,
        "targets": {t["key"]: _public_target(t) for t in targets},
        "legacy_codebuddy_install": legacy,
        "next": _next_steps(targets, legacy),
    }
    if note:
        report["note"] = note
    return report


def exit_for_report(report: dict) -> int:
    """Exit code for an update report (see the plan's exit-code table)."""
    if report["status"] in ("UPDATED", "NO_CHANGE", "PREVIEW_ONLY",
                            "CANCELLED", "NO_TARGETS"):
        bad = [
            t for t in report["targets"].values()
            if t["status"] in ("CONFLICT", "FAIL")
        ]
        return 1 if bad else 0
    return 1


def _resolve_root(repo_root) -> Path:
    root = repo_mod.resolve_repo_root(repo_root)
    repo_mod.bind_tools_to_root(root)
    return Path(root).resolve()


def preview_update(*, repo_root=None, hosts=None, scope="user",
                   project=None, skills_root=None,
                   workbuddy_skills_root=None, no_pull=False) -> dict:
    """Read-only update preview. Zero writes (git or filesystem).

    Raises UpdateError on fatal git pre-check failures.
    """
    root = _resolve_root(repo_root)
    pre = precheck(root, no_pull=no_pull)
    targets, legacy = discover_targets(
        root, hosts, scope, project, skills_root, workbuddy_skills_root,
    )
    repo_info = {
        "path": str(root),
        "branch": pre["branch"],
        "pull": "SKIPPED_NO_PULL" if no_pull else "PREVIEW",
        "before": pre["before"],
        "after": pre["before"] if pre["before"] else "NO_GIT",
    }
    if not targets:
        status = "NO_TARGETS"
    elif any(t["status"] in ("CONFLICT", "FAIL") for t in targets):
        status = "FAIL"
    else:
        status = "PREVIEW_ONLY"
    return _assemble(status, repo_info, targets, legacy,
                     note=_skills_root_note(skills_root, hosts))


def apply_update(*, repo_root=None, hosts=None, scope="user",
                 project=None, skills_root=None,
                 workbuddy_skills_root=None, no_pull=False) -> dict:
    """Pull latest main and re-sync installed targets.

    Raises UpdateError on fatal git pre-check / pull failures (nothing
    is synced in that case). Per-target failures are reported in the
    report, not raised.
    """
    root = _resolve_root(repo_root)
    pre = precheck(root, no_pull=no_pull)
    targets, legacy = discover_targets(
        root, hosts, scope, project, skills_root, workbuddy_skills_root,
    )
    if no_pull:
        repo_info = {
            "path": str(root),
            "branch": pre["branch"],
            "pull": "SKIPPED_NO_PULL",
            "before": pre["before"],
            "after": pre["before"] if pre["before"] else "NO_GIT",
        }
    else:
        pulled = pull_repo(root)
        repo_info = {
            "path": str(root),
            "branch": pre["branch"],
            **pulled,
        }
    # Re-preview against the (possibly just pulled) tree so the report
    # reflects the content actually synced, not the pre-pull tree.
    targets, legacy = discover_targets(
        root, hosts, scope, project, skills_root, workbuddy_skills_root,
    )
    for target in targets:
        if target["status"] in ("NOT_INSTALLED", "CONFLICT", "FAIL"):
            continue
        if target["kind"] == "codex":
            _sync_codex(target)
        else:
            _sync_universal(target, root, skills_root, workbuddy_skills_root)
    if not targets:
        status = "NO_TARGETS"
    elif any(t["status"] in ("CONFLICT", "FAIL") for t in targets):
        status = "FAIL"
    elif any(t["status"] == "UPDATED" for t in targets):
        status = "UPDATED"
    else:
        status = "NO_CHANGE"
    return _assemble(status, repo_info, targets, legacy,
                     note=_skills_root_note(skills_root, hosts))


def _skills_root_note(skills_root, hosts) -> str | None:
    """--skills-root only takes effect with --host; say so, don't ignore silently."""
    if skills_root is not None and not hosts:
        return (
            "--skills-root was ignored: it overrides the skills directory "
            "of the --host given only; re-run with --host <host> to use it."
        )
    return None


def approve(question: str, input_fn=input) -> bool:
    """Literal YES approval (same semantics as full_setup._approve)."""
    try:
        return input_fn(question + " [type YES]: ").strip() == "YES"
    except (EOFError, KeyboardInterrupt):
        return False
