"""``aka-skills`` command-line interface.

Thin wrappers only: every subcommand delegates to the existing functions in
``tools.*`` (``full_setup``, ``quick_install``, ``skill_installer``,
``skill_validator``, ``chef_global_rules``, ``codex_subagents``) — no
install/verify logic is reimplemented here. The CLI adds argument parsing,
output formatting and exit codes, nothing else.

Output is JSON on stdout by default (the same report dicts the ``tools.*``
functions return); ``--json`` is accepted everywhere for explicitness.
A one-line human summary goes to stderr in non-``--json`` mode. Errors
print ``{"status": "FAIL", "error_type": ...}`` on ``--json`` and a one-line
message to stderr otherwise.

Notes / deliberate limits (PLAN.md §4):

- Default ``install`` (no flags) is preview-only and writes nothing.
- ``--interactive`` prompts for a literal ``YES`` via
  ``tools.full_setup._approve``; anything else cancels (``CANCELLED``,
  exit 0). ``--apply`` and ``--interactive`` are mutually exclusive.
- ``--workspace`` is NOT a CLI flag: cloud workspace setup still goes
  through ``python -m tools.full_setup --workspace``.
- ``verify`` mirrors ``tools.quick_install.execute``'s target logic: the
  ``directory`` target (with ``--skills-root``) or the ``codex`` target
  (without it). ``--codex-home`` only steers the global-rules and role
  checks; the skill check uses ``skill_installer``'s own target rules.
- ``update`` pulls latest main and re-syncs installed hosts; default is
  preview-only, ``--apply`` executes, ``--interactive`` asks for a
  literal ``YES``. Its ``--scope`` default is ``user`` (unlike
  install's ``project``); ``--skills-root`` overrides the ``--host``
  given (workbuddy/hermes/codex) and needs ``--host`` to take effect.
- No ``uninstall``/``rollback`` subcommands in v1 (destructive ops need a
  separate decision).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from aka_skills import __version__
from aka_skills import repo as repo_mod
from aka_skills.repo import RepoRootError
from tools import (
    chef_global_rules,
    codex_subagents,
    full_setup,
    quick_install,
    repo_update,
    skill_installer,
    skill_validator,
    universal_chef,
)

_OK_CORE_INSTALL = ("PREVIEW_ONLY", "CANCELLED", "FILES_VERIFIED")


def _emit(result: object, as_json: bool, summary: str | None = None) -> None:
    """Print a result dict as JSON on stdout; human summary goes to stderr."""
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not as_json and summary:
        print(summary, file=sys.stderr)


def _fail(exc: BaseException, as_json: bool) -> int:
    """Report a user-facing error (JSON on --json, one line on stderr)."""
    if as_json:
        print(json.dumps(
            {"status": "FAIL", "error_type": type(exc).__name__, "message": str(exc)},
            ensure_ascii=False,
        ))
    else:
        print(f"aka-skills: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 1


def _cmd_install(args: argparse.Namespace) -> int:
    try:
        # input_fn=input is looked up at call time (not bound at def time),
        # so tests can mock builtins.input and interactive prompts stay
        # testable; installer semantics are unchanged.
        result = full_setup.run(
            apply=args.apply,
            interactive=args.interactive,
            workspace=False,
            codex_home=args.codex_home,
            skills_root=args.skills_root,
            host=args.host,
            project=args.project,
            scope=args.scope,
            workbuddy_skills_root=args.workbuddy_skills_root,
            input_fn=input,
        )
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        return _fail(exc, args.json)
    _emit(result, args.json, f"core_install: {result.get('core_install')}")
    return 0 if result.get("core_install") in _OK_CORE_INSTALL else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        root = repo_mod.resolve_repo_root(args.repo_root)
        target = "directory" if args.skills_root is not None else "codex"
        rules = chef_global_rules.apply(
            "verify", quick_install.TEMPLATE, args.codex_home
        )
        roles = {
            role: codex_subagents.verify(role, args.codex_home)["integrity"]
            for role in codex_subagents.ROLE_NAMES
        }
        skills: dict[str, str] = {}
        for name in quick_install.SKILLS:
            try:
                skills[name] = skill_installer.verify(
                    name, target, args.skills_root
                )["integrity"]
            except ValueError:
                # Not installed by this tool (or externally modified).
                skills[name] = "FAIL"
        validation = {
            skill["name"]: skill_validator.validate_skill(Path(skill["path"]))
            for skill in repo_mod.list_skills(root)
        }
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        return _fail(exc, args.json)
    passed = (
        rules["state"] == "PASS"
        and all(state == "PASS" for state in roles.values())
        and all(state == "PASS" for state in skills.values())
        and all(v["status"] != "FAILED" for v in validation.values())
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "rules": rules["state"],
        "roles": roles,
        "skills": skills,
        "validation": validation,
    }
    _emit(result, args.json, f"verify: {result['status']}")
    return 0 if passed else 1


def _cmd_status(args: argparse.Namespace) -> int:
    try:
        result = {
            "preflight": full_setup.dependency_status(),
            "preview": quick_install.execute(
                codex_home=args.codex_home, skills_root=args.skills_root
            ),
        }
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        return _fail(exc, args.json)
    _emit(result, args.json, "status: OK (preview only, nothing written)")
    return 0


def _cmd_list_skills(args: argparse.Namespace) -> int:
    try:
        skills = repo_mod.list_skills(repo_mod.resolve_repo_root(args.repo_root))
    except (OSError, ValueError, UnicodeError) as exc:
        return _fail(exc, args.json)
    if args.json:
        print(json.dumps(skills, ensure_ascii=False, indent=2))
    else:
        for skill in skills:
            source = f" [{skill['source']}]" if skill.get("source") == "vendor" else ""
            print(f"{skill['name']} — {skill['description']}{source}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        root = repo_mod.resolve_repo_root(args.repo_root)
        result = skill_validator.validate_skill(
            repo_mod.resolve_skill_dir(root, args.skill)
        )
    except (OSError, ValueError, UnicodeError) as exc:
        return _fail(exc, args.json)
    _emit(result, args.json, f"validate: {result['status']}")
    return 0 if result["status"] != "FAILED" else 1


def _mcp_sdk_available() -> bool:
    """True when the optional ``mcp`` SDK is importable.

    Checked explicitly (rather than relying on ``ImportError`` from
    importing ``aka_skills.mcp_server``, which never imports ``mcp`` at
    module level): ``from aka_skills import mcp_server`` succeeds whenever
    the module was already imported in this process, so a bare
    ``try/except ImportError`` cannot simulate — or detect — a missing SDK.
    """
    return importlib.util.find_spec("mcp") is not None


def _cmd_serve(args: argparse.Namespace) -> int:
    if not _mcp_sdk_available():
        print(
            "aka-skills serve requires the MCP SDK, which is an optional extra: "
            "pip install 'aka-cristi-skills[mcp]' (or pip install '.[mcp]' "
            "from a checkout).",
            file=sys.stderr,
        )
        return 1
    try:
        from aka_skills import mcp_server
    except ImportError:
        print(
            "aka-skills serve requires the MCP SDK, which is an optional extra: "
            "pip install 'aka-cristi-skills[mcp]' (or pip install '.[mcp]' "
            "from a checkout).",
            file=sys.stderr,
        )
        return 1
    return mcp_server.serve(repo_root=args.repo_root)


def _update_kwargs(args: argparse.Namespace) -> dict:
    return {
        "repo_root": getattr(args, "repo_root", None) or getattr(args, "repo", None),
        "hosts": [args.host] if args.host else None,
        "scope": args.scope,
        "project": args.project,
        "skills_root": args.skills_root,
        "no_pull": args.no_pull,
    }


def _cmd_update(args: argparse.Namespace) -> int:
    try:
        if args.apply:
            report = repo_update.apply_update(**_update_kwargs(args))
            _emit(report, args.json, f"update: {report.get('status')}")
            return repo_update.exit_for_report(report)
        preview = repo_update.preview_update(**_update_kwargs(args))
        if args.interactive:
            _emit(preview, args.json, f"update: {preview.get('status')}")
            if not repo_update.approve("Apply the update", input):
                cancelled = dict(preview)
                cancelled["status"] = "CANCELLED"
                _emit(cancelled, args.json, "update: CANCELLED")
                return 0
            report = repo_update.apply_update(**_update_kwargs(args))
            _emit(report, args.json, f"update: {report.get('status')}")
            return repo_update.exit_for_report(report)
        _emit(preview, args.json, f"update: {preview.get('status')}")
        return repo_update.exit_for_report(preview)
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        return _fail(exc, args.json)


def _add_global_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="override repo-root/content location (default: auto-discovery)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="machine-readable JSON output (output is JSON by default; "
        "this flag only makes it explicit)",
    )


def _add_shared_flags(parser: argparse.ArgumentParser) -> None:
    # Same flags as the top level, but with SUPPRESS defaults so a value
    # given before the subcommand is not overwritten by the subparser.
    parser.add_argument(
        "--repo-root", type=Path, default=argparse.SUPPRESS,
        help="override repo-root/content location (default: auto-discovery)",
    )
    parser.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS,
        help="machine-readable JSON output",
    )


def _add_sandbox_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--codex-home", type=Path, default=None,
                        help="Codex home directory (default: ~/.codex)")
    parser.add_argument("--skills-root", type=Path, default=None,
                        help="explicit skills directory (uses the directory "
                        "install target instead of the Codex target)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aka-skills",
        description="AKA.CRISTI Skills installer CLI (preview-first, "
        "Codex-first). Wraps tools.full_setup / tools.quick_install.",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    _add_global_flags(parser)
    sub = parser.add_subparsers(dest="command")

    p_install = sub.add_parser(
        "install",
        help="preview (default) or install the 31 Skills (6 native + "
        "25 vendored from Addy Osmani agent-skills; vendored "
        "interview-me excluded), global rules and 4 roles",
        description="Preview (default) or install the 31 Skills (6 native "
        "+ 25 vendored from Addy Osmani agent-skills; vendored "
        "interview-me is reference-only and excluded), global rules "
        "and 4 roles. Hooks are never installed. Non-Codex hosts also "
        "install their upstream slash commands where one is defined "
        "(Claude Code .md, Gemini CLI .toml).",
    )
    mode = p_install.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true",
                      help="preview, then ask for a literal YES before writing")
    mode.add_argument("--apply", action="store_true",
                      help="install without prompting (explicit user choice)")
    p_install.add_argument("--host", choices=universal_chef.HOSTS, default="codex",
                           help="host-specific native configuration")
    p_install.add_argument("--scope", choices=("project", "user"),
                           default="project")
    p_install.add_argument("--project", type=Path, default=None,
                           help="existing target project (non-Codex hosts)")
    p_install.add_argument("--workbuddy-skills-root", type=Path, default=None,
                           help="explicit user WorkBuddy Skills directory "
                           "(default: ~/.workbuddy/skills)")
    _add_sandbox_flags(p_install)
    _add_shared_flags(p_install)
    p_install.set_defaults(func=_cmd_install)

    p_verify = sub.add_parser(
        "verify", help="read-only verification of the installed state")
    _add_sandbox_flags(p_verify)
    _add_shared_flags(p_verify)
    p_verify.set_defaults(func=_cmd_verify)

    p_status = sub.add_parser(
        "status", help="read-only environment preflight + install preview")
    _add_sandbox_flags(p_status)
    _add_shared_flags(p_status)
    p_status.set_defaults(func=_cmd_status)

    p_list = sub.add_parser(
        "list-skills", help="list the 31 installable Skills shipped in "
        "this repo (6 native + 25 vendored)",
        description="List the 31 installable Skills shipped in this repo "
        "(6 native + 25 vendored from Addy Osmani agent-skills; "
        "vendored interview-me is reference-only and excluded).",
    )
    _add_shared_flags(p_list)
    p_list.set_defaults(func=_cmd_list_skills)

    p_validate = sub.add_parser(
        "validate", help="read-only preflight check of one Skill")
    p_validate.add_argument(
        "skill", help="skill directory name (e.g. visual-design) or a path "
        "to a skill directory")
    _add_shared_flags(p_validate)
    p_validate.set_defaults(func=_cmd_validate)

    p_serve = sub.add_parser(
        "serve", help="start the MCP server on stdio (needs the .[mcp] extra)")
    _add_shared_flags(p_serve)
    p_serve.set_defaults(func=_cmd_serve)

    p_update = sub.add_parser(
        "update",
        help="pull latest main and re-sync installed hosts (preview by "
        "default; nothing is written without --apply or YES)",
    )
    mode = p_update.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true",
                      help="preview, then ask for a literal YES before writing")
    mode.add_argument("--apply", action="store_true",
                      help="pull and re-sync without prompting (explicit user choice)")
    p_update.add_argument("--host", choices=universal_chef.HOSTS, default=None,
                          help="limit the update to one host (default: all "
                          "installed hosts)")
    p_update.add_argument("--scope", choices=("project", "user"),
                          default="user",
                          help="scope for universal hosts (default: user; "
                          "differs from install, which defaults to project)")
    p_update.add_argument("--project", type=Path, default=None,
                          help="project root for project-scope targets; "
                          "also adds that project's hosts to the update")
    p_update.add_argument("--skills-root", type=Path, default=None,
                          help="explicit skills directory for the --host "
                          "given (workbuddy: overrides ~/.workbuddy/skills; "
                          "hermes: same as --hermes-skills-root; codex: "
                          "directory-target override). Needs --host to take "
                          "effect; ignored otherwise. Unlike install, where "
                          "--skills-root only affects codex.")
    p_update.add_argument("--repo", type=Path, default=None,
                          help="alias for --repo-root")
    p_update.add_argument("--no-pull", action="store_true",
                          help="skip git pull; sync from the local tree only")
    _add_shared_flags(p_update)
    p_update.set_defaults(func=_cmd_update)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    # Defaults for flags that subparsers define with SUPPRESS.
    args.json = getattr(args, "json", False)
    args.repo_root = getattr(args, "repo_root", None)
    # Installed-wheel fix (repo.bind_tools_to_root): point tools.* at the
    # resolved content root before dispatching. Best-effort: when no root
    # resolves, tools.* keep their __file__-based ROOT (checkout layout).
    try:
        repo_mod.bind_tools_to_root(repo_mod.resolve_repo_root(args.repo_root))
    except RepoRootError:
        pass
    try:
        return int(args.func(args))
    except RepoRootError as exc:
        return _fail(exc, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
