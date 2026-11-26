"""Tests for aka_skills.mcp_server (MCP part, PLAN.md §7).

(a) In-process tool-function tests: need no MCP SDK.
(b) Protocol smoke test: skipped when ``mcp`` is not importable.

Repo root is passed explicitly via AKA_SKILLS_REPO_ROOT (the worktree has no
pyproject.toml yet, so checkout discovery cannot resolve it on its own).
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))

from aka_skills import mcp_server  # noqa: E402

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
EXPECTED_STYLES = {
    "glassmorphism",
    "flat-information-graphics",
    "giant-type-posters",
    "experimental-posters",
    "colorful-commercial-posters",
    "giant-type-web-design",
}
EXPECTED_TOOLS = {
    "list_skills",
    "read_skill",
    "list_design_cases",
    "read_design_case",
    "install_preview",
    "validate_skill",
    "check_status",
}
PREFLIGHT_KEYS = {
    "python",
    "git",
    "codex_cli",
    "workspace_keyring",
    "workspace_oauth_client_id",
}


def _snapshot(directory: Path) -> set[Path]:
    return {p for p in directory.rglob("*") if p.is_file() or p.is_symlink()}


class ToolFunctionTests(unittest.TestCase):
    def setUp(self):
        self._old_env = os.environ.get("AKA_SKILLS_REPO_ROOT")
        os.environ["AKA_SKILLS_REPO_ROOT"] = str(REPO_ROOT)

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("AKA_SKILLS_REPO_ROOT", None)
        else:
            os.environ["AKA_SKILLS_REPO_ROOT"] = self._old_env

    def test_list_skills_returns_thirty_one_skills(self):
        result = mcp_server.list_skills()
        self.assertNotIn("status", result)
        names = {s["name"] for s in result["skills"]}
        self.assertEqual(names, EXPECTED_SKILLS)
        for skill in result["skills"]:
            self.assertTrue(skill["description"], skill["name"])
            self.assertTrue(skill["path"].endswith("SKILL.md"))

    def test_read_skill_visual_design(self):
        result = mcp_server.read_skill("visual-design")
        self.assertNotIn("status", result)
        self.assertEqual(result["name"], "visual-design")
        self.assertIn("name: visual-design", result["content"])
        self.assertTrue(result["path"].endswith("skills/visual-design/SKILL.md"))

    def test_read_skill_traversal_and_unknown_are_errors(self):
        for bad in ("../x", "..\\x", "a/b", "a\\b", ""):
            with self.subTest(name=bad):
                result = mcp_server.read_skill(bad)
                self.assertEqual(result.get("status"), "ERROR")
                self.assertIn("error", result)
                self.assertNotIn("content", result)
        result = mcp_server.read_skill("nope")
        self.assertEqual(result.get("status"), "ERROR")
        self.assertIn("unknown skill: nope", result["error"])

    def test_list_design_cases_returns_styles_and_cases(self):
        result = mcp_server.list_design_cases()
        style_names = {s["name"] for s in result["styles"]}
        self.assertEqual(style_names, EXPECTED_STYLES)
        self.assertTrue(result["cases"], "expected at least one case")
        case_names = {c["name"] for c in result["cases"]}
        self.assertIn("beauty-class-poster", case_names)
        for entry in result["styles"] + result["cases"]:
            self.assertTrue(entry["title"], entry["name"])
            self.assertTrue(entry["path"].endswith(".md"))
        self.assertNotIn("INDEX.md", [s["name"] for s in result["styles"]])
        self.assertIsNotNone(result.get("styles_index"))

        styles_only = mcp_server.list_design_cases("style")
        self.assertEqual({s["name"] for s in styles_only["styles"]}, EXPECTED_STYLES)
        self.assertEqual(styles_only["cases"], [])
        cases_only = mcp_server.list_design_cases("case")
        self.assertEqual(cases_only["styles"], [])
        self.assertIn("beauty-class-poster", {c["name"] for c in cases_only["cases"]})

    def test_list_design_cases_invalid_kind(self):
        result = mcp_server.list_design_cases("bogus")
        self.assertEqual(result.get("status"), "ERROR")

    def test_read_design_case_round_trips_style_and_case(self):
        style = mcp_server.read_design_case("style", "glassmorphism")
        self.assertNotIn("status", style)
        self.assertEqual(style["kind"], "style")
        self.assertEqual(style["name"], "glassmorphism")
        on_disk = (
            REPO_ROOT
            / "skills/visual-design/references/styles/glassmorphism.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(style["content"], on_disk)

        case = mcp_server.read_design_case("case", "beauty-class-poster")
        self.assertNotIn("status", case)
        on_disk = (
            REPO_ROOT / "skills/visual-design/references/cases/beauty-class-poster.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(case["content"], on_disk)

    def test_read_design_case_traversal_and_unknown_are_errors(self):
        for kind, name in (
            ("style", "../x"),
            ("case", "a/b"),
            ("style", "nope"),
            ("bogus", "glassmorphism"),
        ):
            with self.subTest(kind=kind, name=name):
                result = mcp_server.read_design_case(kind, name)
                self.assertEqual(result.get("status"), "ERROR")
                self.assertNotIn("content", result)

    def test_install_preview_is_preview_only_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            before = _snapshot(sandbox)
            result = mcp_server.install_preview(
                codex_home=sandbox / "codex",
                skills_root=sandbox / "skills",
            )
            after = _snapshot(sandbox)
            self.assertEqual(result.get("core_install"), "PREVIEW_ONLY")
            self.assertIs(result.get("writes"), False)
            self.assertEqual(result.get("workspace"), "NOT_RUN")
            self.assertEqual(result.get("live_agents"), "NOT_RUN")
            self.assertEqual(before, after, "install_preview must not create files")

    def test_install_preview_under_symlinked_parent(self):
        # Regression: macOS temp dirs live under /var, a symlink to
        # /private/var, so an unresolved temp path tripped the installer's
        # symlink guard and install_preview returned ERROR instead of a
        # preview (macOS CI failure on PR #62). A symlinked *parent* must
        # not block a preview; a symlinked target itself is still refused
        # by the guard (tests/test_filesystem_security.py).
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp).resolve()
            link = real.parent / f"alias-{real.name}"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks unsupported")
            try:
                sandbox = link / f"sb-{real.name}"
                before = _snapshot(real)
                result = mcp_server.install_preview(
                    codex_home=sandbox / "codex",
                    skills_root=sandbox / "skills",
                )
                after = _snapshot(real)
                self.assertEqual(result.get("core_install"), "PREVIEW_ONLY")
                self.assertIs(result.get("writes"), False)
                self.assertEqual(before, after, "install_preview must not create files")
            finally:
                link.unlink(missing_ok=True)

    def test_install_preview_invalid_host_and_scope(self):
        self.assertEqual(
            mcp_server.install_preview(host="bogus").get("status"), "ERROR"
        )
        self.assertEqual(
            mcp_server.install_preview(scope="bogus").get("status"), "ERROR"
        )

    def test_validate_skill_returns_validator_shape(self):
        result = mcp_server.validate_skill("visual-design")
        for key in (
            "schema_version",
            "skill_path",
            "status",
            "runtime_verified",
            "host_compatibility_verified",
            "findings",
        ):
            self.assertIn(key, result, f"missing key {key}")
        self.assertIn(result["status"], ("PREFLIGHT_ONLY", "FAILED"))
        self.assertIs(result["runtime_verified"], False)
        self.assertIsInstance(result["findings"], list)

    def test_check_status_contains_preflight_keys(self):
        result = mcp_server.check_status()
        self.assertNotIn("status", result)
        self.assertEqual(set(result["preflight"]), PREFLIGHT_KEYS)
        self.assertIn("preview", result)
        self.assertEqual(result["repo_root"], str(REPO_ROOT))

    def test_missing_repo_root_fails_closed(self):
        os.environ.pop("AKA_SKILLS_REPO_ROOT", None)
        with tempfile.TemporaryDirectory() as tmp:
            # No pyproject.toml / skills/ here, and no bundled data.
            os.chdir(tmp)
            try:
                self.assertIsNone(mcp_server.resolve_repo_root())
                self.assertEqual(
                    mcp_server.list_skills().get("status"), "ERROR"
                )
            finally:
                os.chdir(REPO_ROOT)


@unittest.skipUnless(
    importlib.util.find_spec("mcp") is not None, "mcp SDK not installed"
)
class ProtocolSmokeTests(unittest.TestCase):
    def test_initialize_list_tools_and_call_tools(self):
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        env = dict(os.environ)
        env["AKA_SKILLS_REPO_ROOT"] = str(REPO_ROOT)

        async def _run():
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "aka_skills.mcp_server"],
                env=env,
                cwd=str(REPO_ROOT),
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    self.assertEqual(
                        {t.name for t in listed.tools}, EXPECTED_TOOLS
                    )
                    result = await session.call_tool("list_skills", {})
                    self.assertFalse(result.isError)
                    payload = json.loads(result.content[0].text)
                    self.assertEqual(
                        {s["name"] for s in payload["skills"]}, EXPECTED_SKILLS
                    )
                    result = await session.call_tool(
                        "read_skill", {"name": "visual-design"}
                    )
                    self.assertFalse(result.isError)
                    payload = json.loads(result.content[0].text)
                    self.assertIn("name: visual-design", payload["content"])

        asyncio.run(asyncio.wait_for(_run(), timeout=120))


if __name__ == "__main__":
    unittest.main()
