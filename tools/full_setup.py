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

from tools import quick_install

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


def run(*, apply=False, interactive=False, workspace=False, test_agents=False,
        codex_home=None, skills_root=None, input_fn=input):
    if apply and interactive:
        raise ValueError("Choose --interactive or --apply, not both")
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
            report["live_agents"] = (
                "REPORT_WRITTEN" if _call([
                    sys.executable, "-m", "tools.verify_four_agents",
                    "--timeout", "600", "--out", "four-agent-report.json",
                ]) else "PROBE_FAILED_OR_INCONCLUSIVE"
            )
            report["agent_evidence"] = "four-agent-report.json"
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
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--skills-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(apply=args.apply, interactive=args.interactive,
                     workspace=args.workspace, test_agents=args.test_agents,
                     codex_home=args.codex_home, skills_root=args.skills_root)
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
