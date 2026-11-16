"""One documented setup entry point for the actual shipped Codex-first features.

Local config requires confirmation. Cloud workspace and quota-consuming runtime
checks each require distinct explicit consent. Unavailable features remain NOT_RUN.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tools import quick_install, universal_chef, chef_runtime_dispatch

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_REQ = ROOT / "requirements-workspace.txt"


def dependency_status():
    return {
        "python": sys.version.split()[0],
        "git": "AVAILABLE" if shutil.which("git") else "MISSING",
        "codex_cli": "AVAILABLE" if shutil.which("codex") else "MISSING",
        "workspace_keyring": "AVAILABLE" if importlib.util.find_spec("keyring") else "MISSING",
        "workspace_oauth_client_id": (
            "CONFIGURED" if os.getenv("AKA_WORKSPACE_OAUTH_CLIENT_ID") else "NOT_CONFIGURED"
        ),
    }


def _call(args):
    try:
        cp = subprocess.run(args, cwd=ROOT, check=False, timeout=900)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return cp.returncode == 0


def _approve(question, input_fn):
    try:
        return input_fn(question + " [type YES]: ").strip() == "YES"
    except (EOFError, KeyboardInterrupt):
        return False


def _run_portable_host(*, host, project, apply, interactive, workspace,
                       test_agents, hermes_skills_root, scope, input_fn):
    """Install native project rules + Skills + roles, never fake runtime activation."""
    plan = universal_chef.inspect(host, project, hermes_skills_root, scope=scope)
    report = {
        "host": host,
        "preflight": dependency_status(),
        "preview": plan,
        "core_install": "PREVIEW_ONLY",
        "workspace": "NOT_RUN",
        "live_agents": "NOT_RUN",
        "dual_engine": "CODEX_CLI_BACKEND_ONLY",
    }
    if plan["status"] == "CONFLICT":
        report["core_install"] = "CONFLICT"
        return report
    if not (apply or interactive):
        return report
    if interactive and not _approve(
        "Install native CHEF project rules, four role definitions and four Skills?",
        input_fn,
    ):
        report["core_install"] = "CANCELLED"
        return report
    installed = universal_chef.install(
        host, project, apply=True, hermes_skills_root=hermes_skills_root,
        scope=scope,
    )
    report["core_install"] = installed["status"]
    report["host_file_verification"] = installed
    if workspace:
        report["workspace"] = "CODEX_ONBOARDING_ONLY"
    if test_agents:
        if host not in ("workbuddy", "claude"):
            report["live_agents"] = "NO_VERIFIED_NON_CODEX_HOST_RUNTIME"
        elif not interactive:
            report["live_agents"] = "SEPARATE_CONSENT_REQUIRED"
        elif not _approve(
            "Run four independent, read-only host CLI sessions? This uses model quota; it does NOT verify native subagents.",
            input_fn,
        ):
            report["live_agents"] = "CANCELLED"
        else:
            cli = "codebuddy" if host == "workbuddy" else "claude"
            active_project = project if project is not None else Path.cwd()
            result = chef_runtime_dispatch.run(
                cli, "four-roles", "Review the CHEF Research/Coding/QA/Automation collaboration methodology. 
                "Do not inspect private data, run tools, or modify files.",
                active_project, allow_quota=True, timeout=180,
            )
            report["live_agents"] = result["status"]
            report["cli_session_evidence"] = result
            report["native_subagents"] = "NOT_VERIFIED"
    report["next_action"] = (
        "Open a NEW host session in the selected project; inspect its loaded "
        "rules/Skills/roles and perform a separately authorized real subagent "
        "handoff test. File installation is not runtime activation."
    )
    return report


def run(*, apply=False, interactive=False, workspace=False, test_agents=False,
        codex_home=None, skills_root=None, input_fn=input, host="codex",
        project=None, hermes_skills_root=None, scope="project"):
    if apply and interactive:
        raise ValueError("Choose --interactive or --apply, not both")
    if host != "codex":
        return _run_portable_host(
            host=host, project=project, apply=apply, interactive=interactive,
            workspace=workspace, test_agents=test_agents,
            hermes_skills_root=hermes_skills_root, scope=scope,
            input_fn=input_fn,
        )
    before = dependency_status()
    preview = quick_install.execute(codex_home=codex_home, skills_root=skills_root)
    report = {
        "version": "main checkout (inspect commit before running)",
        "preflight": before,
        "preview": preview,
        "core_install": "PREVIEW_ONLY",
        "workspace": "NOT_RUN",
        "live_agents": "NOT_RUN",
    }
    if not (apply or interactive):
        return report
    if interactive and not _approve("Install managed CHEF rules, 4 Skills and 4 Codex role files?", input_fn):
        report["core_install"] = "CANCELLED"
        return report
    core = quick_install.execute(apply=True, codex_home=codex_home, skills_root=skills_root)
    report["core_install"] = core["status"]
    report["core_evidence"] = {
        "rules": core["rules"], "roles": core["roles"], "skills": core["skills"]
    }
    if core["status"] != "FILES_VERIFIED":
        return report
    # Basic CLI/login probes do not spend model quota or change config.
    if before["codex_cli"] == "AVAILABLE":
        report["codex_login"] = (
            "SIGNED_IN" if _call(["codex", "login", "status"]) else "SIGN_IN_REQUIRED"
        )
        report["next_codex_action"] = (
            "Open a NEW Codex session to load installed roles and Skills"
        )
    else:
        report["codex_login"] = "CODEX_CLI_MISSING"
        report["next_codex_action"] = "Install official Codex CLI and sign in"
    if workspace:
        # Remote writes are separately authorized. Failure in this optional
        # stage must not prevent an independent Codex runtime diagnostic.
        ready = before["workspace_keyring"] == "AVAILABLE"
        if not ready:
            if interactive and _approve(
                "Install optional keyring dependency from pinned requirements file?",
                input_fn,
            ):
                ready = _call([sys.executable, "-m", "pip", "install",
                               "-r", str(WORKSPACE_REQ)])
                if not ready:
                    report["workspace"] = "DEPENDENCY_INSTALL_FAILED"
            else:
                report["workspace"] = "DEPENDENCY_REQUIRED"
        if ready and not os.getenv("AKA_WORKSPACE_OAUTH_CLIENT_ID"):
            report["workspace"] = "OAUTH_CLIENT_ID_REQUIRED"
            report["workspace_next_action"] = (
                "Configure the public GitHub OAuth App Client ID; "
                "no third-party account is connected automatically"
            )
        elif ready and not interactive:
            report["workspace"] = "SEPARATE_CONFIRMATION_REQUIRED"
        elif ready and not _approve(
            "Authorize GitHub device flow and private workspace setup? Cloud operations may write to your GitHub account.",
            input_fn,
        ):
            report["workspace"] = "CANCELLED"
        elif ready:
            report["workspace"] = (
                "SETUP_ATTEMPT_COMPLETE" if _call([
                    sys.executable, "-m", "tools.personal_workspace",
                    "one-click", "--apply",
                ]) else "SETUP_STOPPED"
            )
    if test_agents:
        if before["codex_cli"] != "AVAILABLE":
            report["live_agents"] = "CODEX_CLI_MISSING"
        elif interactive and _approve(
            "Run real four-agent Codex acceptance? This consumes Codex quota.",
            input_fn,
        ):
            _call([
                sys.executable, "-m", "tools.verify_four_agents",
                "--timeout", "600", "--out", "four-agent-report.json",
            ])
            evidence = ROOT / "four-agent-report.json"
            if evidence.is_file():
                try:
                    payload = json.loads(evidence.read_text(encoding="utf-8"))
                    state = payload.get("status", "INCONCLUSIVE")
                    report["live_agents"] = state if state in (
                        "PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"
                    ) else "INCONCLUSIVE"
                except (OSError, ValueError, UnicodeError):
                    report["live_agents"] = "INCONCLUSIVE"
                report["agent_evidence"] = str(evidence)
            else:
                report["live_agents"] = "PROBE_FAILED_NO_REPORT"
        else:
            report["live_agents"] = "SEPARATE_CONSENT_REQUIRED"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="AKA.CRISTI full available-feature setup (preview-first, Codex-first)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--interactive", action="store_true",
                       help="request explicit approval before local writes")
    group.add_argument("--apply", action="store_true",
                       help="explicitly install local Codex core only")
    parser.add_argument("--workspace", action="store_true",
                        help="optionally prepare private workspace; cloud changes require interactive approval")
    parser.add_argument("--test-agents", action="store_true",
                        help="optionally test real four-role invocation with separate consent")
    parser.add_argument("--host", choices=universal_chef.HOSTS, default="codex",
                        help="host-specific native configuration; Codex remains user-scoped")
    parser.add_argument("--scope", choices=("project", "user"), default="project")
    parser.add_argument("--project", type=Path,
                        help="existing target project required for non-Codex hosts")
    parser.add_argument("--hermes-skills-root", type=Path,
                        help="explicit user Hermes Skills directory when authorized")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--skills-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(apply=args.apply, interactive=args.interactive,
                     workspace=args.workspace, test_agents=args.test_agents,
                     codex_home=args.codex_home, skills_root=args.skills_root,
                     host=args.host, project=args.project,
                     hermes_skills_root=args.hermes_skills_root, scope=args.scope)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1 if result.get("core_install") not in (
            "PREVIEW_ONLY", "CANCELLED", "FILES_VERIFIED",
        ) else 0
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__},
                         ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
