"""Tests for the `aka-skills` CLI (thin wrappers over tools.*).

All file-touching tests use tempfile sandboxes via --codex-home /
--skills-root and never touch the real ~/.codex. Style follows the
existing suite: stdlib unittest only.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aka_skills import __version__
from aka_skills.cli import main
from tools.quick_install import SKILLS

EXPECTED_SKILLS = {
    # Native (6).
    "chef-orchestrator",
    "verified-change-loop",
    "feature-journey-map",
    "skill-evaluation-gate",
    "visual-design",
    "interview-me",
    # Vendored (25). Vendored interview-me is reference-only and excluded.
    "accessibility-engineering",
    "api-and-interface-design",
    "browser-testing-with-devtools",
    "ci-cd-and-automation",
    "code-review-and-quality",
    "code-simplification",
    "constraint-driven-development",
    "context-engineering",
    "debugging-and-error-recovery",
    "deprecation-and-migration",
    "documentation-and-adrs",
    "doubt-driven-development",
    "frontend-ui-engineering",
    "git-workflow-and-versioning",
    "idea-refine",
    "incremental-implementation",
    "observability-and-instrumentation",
    "performance-optimization",
    "planning-and-task-breakdown",
    "security-and-hardening",
    "shipping-and-launch",
    "source-driven-development",
    "spec-driven-development",
    "test-driven-development",
    "using-agent-skills",
}
SUBCOMMANDS = ("install", "verify", "status", "list-skills", "validate", "serve")


def run_cli(argv):
    """Run cli.main(argv), capturing stdout; returns (exit_code, stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def tree(root: Path) -> set[str]:
    """Relative paths under root (empty set when root does not exist)."""
    if not root.exists():
        return set()
    return {str(p.relative_to(root)) for p in root.rglob("*")}


class CliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name).resolve()
        self.home = base / "codex"
        self.skills = base / "skills"
        self.sandbox = ["--codex-home", str(self.home),
                        "--skills-root", str(self.skills)]

    def test_help_lists_all_subcommands(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        for name in SUBCOMMANDS:
            self.assertIn(name, buf.getvalue())

    def test_no_subcommand_prints_help_and_exits_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([])
        self.assertEqual(code, 2)
        self.assertIn("install", buf.getvalue())

    def test_version_prints_package_version(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, buf.getvalue())

    def test_install_preview_writes_nothing(self):
        code, out = run_cli(["install", *self.sandbox])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["core_install"], "PREVIEW_ONLY")
        self.assertFalse(self.home.exists())
        self.assertFalse(self.skills.exists())

    def test_install_interactive_declined_writes_nothing(self):
        with patch("builtins.input", return_value="NO"):
            code, out = run_cli(["install", "--interactive", *self.sandbox])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["core_install"], "CANCELLED")
        self.assertFalse(self.home.exists())
        self.assertFalse(self.skills.exists())

    def test_install_interactive_yes_installs_into_sandbox(self):
        with patch("builtins.input", return_value="YES"):
            code, out = run_cli(["install", "--interactive", *self.sandbox])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["core_install"], "FILES_VERIFIED")
        self.assertTrue((self.home / "AGENTS.md").is_file())
        for skill in SKILLS:
            self.assertTrue((self.skills / skill / "SKILL.md").is_file())
        # Idempotent: a second identical run still verifies cleanly.
        code, out = run_cli(["install", "--apply", *self.sandbox])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["core_install"], "FILES_VERIFIED")

    def test_install_apply_and_interactive_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                main(["install", "--apply", "--interactive", *self.sandbox])
        self.assertEqual(ctx.exception.code, 2)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.skills.exists())

    def test_install_conflict_aborts_with_no_writes(self):
        role_folder = self.home / "agents"
        role_folder.mkdir(parents=True)
        untouched = role_folder / "research.toml"
        untouched.write_text("private content", encoding="utf-8")
        code, out = run_cli(["install", "--json", "--apply", *self.sandbox])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "FAIL")
        self.assertEqual(untouched.read_text(encoding="utf-8"), "private content")
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertFalse(self.skills.exists())

    def test_verify_pass_after_install_fail_on_empty_target(self):
        code, out = run_cli(["install", "--apply", *self.sandbox])
        self.assertEqual(code, 0)
        code, out = run_cli(["verify", *self.sandbox])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "PASS")
        # Empty target: nothing installed anywhere.
        with tempfile.TemporaryDirectory() as other:
            base = Path(other).resolve()
            code, out = run_cli(["verify", "--codex-home", str(base / "codex"),
                                 "--skills-root", str(base / "skills")])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "FAIL")

    def test_verify_fail_after_tampering(self):
        code, _ = run_cli(["install", "--apply", *self.sandbox])
        self.assertEqual(code, 0)
        code, out = run_cli(["verify", *self.sandbox])
        self.assertEqual(json.loads(out)["status"], "PASS")
        # Remove one installed skill: integrity can no longer verify.
        import shutil
        shutil.rmtree(self.skills / SKILLS[0])
        code, out = run_cli(["verify", *self.sandbox])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "FAIL")

    def test_status_exits_0_with_preflight_keys_and_no_writes(self):
        before = (tree(self.home), tree(self.skills))
        code, out = run_cli(["status", *self.sandbox])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(
            set(result["preflight"]),
            {"python", "git", "codex_cli", "workspace_keyring",
             "workspace_oauth_client_id"},
        )
        self.assertEqual(result["preview"]["status"], "PREVIEW")
        self.assertEqual((tree(self.home), tree(self.skills)), before)

    def test_list_skills_returns_all_thirty_one(self):
        code, out = run_cli(["list-skills", "--json"])
        self.assertEqual(code, 0)
        skills = json.loads(out)
        self.assertEqual({s["name"] for s in skills}, EXPECTED_SKILLS)
        for skill in skills:
            self.assertTrue(skill["description"])
            self.assertTrue(skill["path"])

    def test_validate_visual_design_passes(self):
        code, out = run_cli(["validate", "visual-design"])
        self.assertEqual(code, 0)
        self.assertNotEqual(json.loads(out)["status"], "FAILED")

    def test_validate_nonexistent_fails(self):
        code, out = run_cli(["validate", "no-such-skill"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "FAILED")

    def test_json_mode_parses_for_install_verify_status(self):
        code, out = run_cli(["install", "--json", *self.sandbox])
        self.assertEqual(code, 0)
        json.loads(out)
        code, out = run_cli(["verify", "--json", *self.sandbox])
        self.assertEqual(code, 1)  # empty sandbox: FAIL, still valid JSON
        json.loads(out)
        code, out = run_cli(["status", "--json", *self.sandbox])
        self.assertEqual(code, 0)
        json.loads(out)

    def test_status_recovers_when_tools_roots_point_elsewhere(self):
        # Regression test for the installed-wheel layout: in a wheel,
        # tools.* compute ROOT from __file__ (site-packages), where the
        # repo content does not live, so status/install used to fail with
        # FileNotFoundError outside a checkout. cli.main() must rebind
        # tools.* to the resolved repo root before dispatching.
        from tools import full_setup, quick_install, universal_chef

        broken = Path(tempfile.mkdtemp(prefix="aka-broken-root-")).resolve()
        saved = (
            full_setup.ROOT, full_setup.WORKSPACE_REQ,
            quick_install.ROOT, quick_install.TEMPLATE,
            universal_chef.ROOT,
        )
        self.addCleanup(
            lambda: (
                setattr(full_setup, "ROOT", saved[0]),
                setattr(full_setup, "WORKSPACE_REQ", saved[1]),
                setattr(quick_install, "ROOT", saved[2]),
                setattr(quick_install, "TEMPLATE", saved[3]),
                setattr(universal_chef, "ROOT", saved[4]),
            )
        )
        full_setup.ROOT = broken
        full_setup.WORKSPACE_REQ = broken / "requirements-workspace.txt"
        quick_install.ROOT = broken
        quick_install.TEMPLATE = broken / "templates" / "AGENTS.global.md"
        universal_chef.ROOT = broken
        code, out = run_cli(["status", *self.sandbox])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["preview"]["status"], "PREVIEW")
        # And install preview recovers the same way.
        code, out = run_cli(["install", *self.sandbox])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["core_install"], "PREVIEW_ONLY")

    def test_serve_without_sdk_fails_with_clear_error(self):
        # Simulate a missing SDK by patching the availability check.
        # (Patching sys.modules alone does NOT work: once any test module
        # has imported aka_skills.mcp_server, `from aka_skills import
        # mcp_server` succeeds via the package attribute and the real
        # server would start and block on stdio. This hung the full
        # suite in a venv with the SDK installed.)
        import aka_skills.cli as cli_mod

        with patch.object(cli_mod, "_mcp_sdk_available", return_value=False):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = main(["serve"])
        self.assertNotEqual(code, 0)
        self.assertIn(".[mcp]", err.getvalue())


if __name__ == "__main__":
    unittest.main()
