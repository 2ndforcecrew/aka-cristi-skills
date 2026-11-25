"""Evals regression tests; deterministic, no LLM, no network.

Two layers:

1. Fixture tests (green now): synthetic skills and orchestrator
   text prove the runner logic itself — section aliases, frontmatter
   parsing, routing matching, exit-code contract.

2. Final-state gates for the real repo: 6 skills, each with all six
   structure concepts, and every routing case resolved by
   chef-orchestrator. These gates are green on main; a failure here
   is a todo list, not a broken runner — do not weaken the
   assertions to force green.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from evals.run_evals import (
    EXPECTED_FINAL_SKILLS,
    check_routing,
    check_skill_structure,
    load_routing_cases,
    run_all,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "evals" / "routing-cases.json"

CONFORMING_SKILL = """---
name: demo-skill
description: Do demo work. Use when a demo is needed.
---

# Demo Skill

## Overview

Demo overview text.

## When to Use

When a demo is needed.

## Process

1. Do the demo.

## Common Rationalizations

| Rationalization | Rebuttal |
| --- | --- |
| Skip it | No. |

## Red Flags

- Skipping verification.

## Verification

- Tests pass.
"""

# Standard headings (docs/skill-format.md) but a description
# without "Use when" — the missing trigger language is a soft
# recommendation only, never a hard failure.
STANDARD_NO_USE_WHEN_SKILL = """---
name: demo-skill
description: Do demo work.
---

# Demo Skill

## Overview

Demo overview text.

## When to Use

When a demo is needed.

## Process

1. Do the demo.

## Common Rationalizations

| Rationalization | Rebuttal |
| --- | --- |
| Skip it | No. |

## Red Flags

- Skipping verification.

## Verification

- Tests pass.
"""


def make_skill(root, name, body):
    root = Path(root) / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(body, encoding="utf-8")
    return root


class RoutingCasesTests(unittest.TestCase):
    def test_cases_cover_all_six_skills_with_three_each(self):
        cases = load_routing_cases(CASES_PATH)
        by_skill = Counter(c["expected_skill"] for c in cases)
        for skill in EXPECTED_FINAL_SKILLS:
            self.assertGreaterEqual(by_skill.get(skill, 0), 3, skill)
        self.assertEqual(
            sorted(by_skill), sorted(EXPECTED_FINAL_SKILLS), "no unexpected skills"
        )

    def test_bad_cases_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "cases.json"
            bad.write_text(
                json.dumps(
                    [{"id": "x", "intent": "y", "expected_skill": "z"}]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_routing_cases(bad)


class StructureCheckFixtureTests(unittest.TestCase):
    def test_fully_conforming_skill_passes(self):
        with tempfile.TemporaryDirectory() as d:
            result = check_skill_structure(make_skill(d, "demo-skill", CONFORMING_SKILL))
        self.assertTrue(result["ok"])
        self.assertEqual(result["missing"], [])
        self.assertTrue(result["frontmatter"]["description_has_use_when"])

    def test_standard_headings_pass_and_missing_use_when_is_soft_only(self):
        with tempfile.TemporaryDirectory() as d:
            result = check_skill_structure(make_skill(d, "demo-skill", STANDARD_NO_USE_WHEN_SKILL))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["missing"], [])
        self.assertFalse(result["frontmatter"]["description_has_use_when"])
        self.assertEqual(len(result["recommendations"]), 1)

    def test_missing_sections_reported_exactly(self):
        body = CONFORMING_SKILL.replace("## Common Rationalizations\n\n| Rationalization | Rebuttal |\n| --- | --- |\n| Skip it | No. |\n\n", "").replace("## Red Flags\n\n- Skipping verification.\n\n", "")
        with tempfile.TemporaryDirectory() as d:
            result = check_skill_structure(make_skill(d, "demo-skill", body))
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["missing"], ["common-rationalizations", "red-flags"]
        )

    def test_missing_frontmatter_name_fails(self):
        body = CONFORMING_SKILL.replace("name: demo-skill\n", "")
        with tempfile.TemporaryDirectory() as d:
            result = check_skill_structure(make_skill(d, "demo-skill", body))
        self.assertFalse(result["ok"])
        self.assertFalse(result["frontmatter"]["name_ok"])

    def test_safety_gates_does_not_count_as_verification(self):
        # Deliberate alias-map decision: safety constraints are not
        # verification evidence (see evals/run_evals.py docstring).
        body = CONFORMING_SKILL.replace("## Verification\n\n- Tests pass.\n", "## Safety gates\n\n- Be careful.\n")
        with tempfile.TemporaryDirectory() as d:
            result = check_skill_structure(make_skill(d, "demo-skill", body))
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], ["verification"])

    def test_missing_skill_dir_reports_all_concepts_missing(self):
        with tempfile.TemporaryDirectory() as d:
            result = check_skill_structure(Path(d) / "nope")
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["missing"],
            ["overview", "when-to-use", "process", "common-rationalizations",
             "red-flags", "verification"],
        )


class RoutingCheckFixtureTests(unittest.TestCase):
    def _fixture(self, d):
        skills_dir = Path(d) / "skills"
        make_skill(skills_dir, "alpha-skill", CONFORMING_SKILL.replace("demo-skill", "alpha-skill"))
        make_skill(skills_dir, "beta-skill", CONFORMING_SKILL.replace("demo-skill", "beta-skill"))
        make_skill(skills_dir, "delta-skill", CONFORMING_SKILL.replace("demo-skill", "delta-skill"))
        orchestrator = Path(d) / "orchestrator.md"
        orchestrator.write_text(
            "## Suggested complementary Skills\n"
            "- `alpha-skill` for A.\n"
            "- `beta-skill` for B.\n",
            encoding="utf-8",
        )
        return skills_dir, orchestrator

    def test_mentioned_skill_passes_and_unmentioned_fails(self):
        with tempfile.TemporaryDirectory() as d:
            skills_dir, orchestrator = self._fixture(d)
            cases = [
                {"id": "c1", "intent": "a", "expected_skill": "alpha-skill", "notes": "n"},
                {"id": "c2", "intent": "b", "expected_skill": "delta-skill", "notes": "n"},
            ]
            results = check_routing(skills_dir, orchestrator, cases)
        self.assertTrue(results[0]["ok"])
        self.assertEqual(results[0]["reason"], "routed")
        self.assertFalse(results[1]["ok"])
        self.assertEqual(results[1]["reason"], "not-routed-by-chef-orchestrator")

    def test_unknown_skill_fails_as_not_found(self):
        with tempfile.TemporaryDirectory() as d:
            skills_dir, orchestrator = self._fixture(d)
            cases = [
                {"id": "c1", "intent": "g", "expected_skill": "ghost-skill", "notes": "n"},
            ]
            results = check_routing(skills_dir, orchestrator, cases)
        self.assertFalse(results[0]["ok"])
        self.assertEqual(results[0]["reason"], "skill-not-found")


class RunnerCliTests(unittest.TestCase):
    def _fixture_repo(self, d, with_red_flags=True):
        # A complete fixture repo: all six final skills, each fully
        # conforming. run_all hard-fails on an expected skill that is
        # absent, so a partial fixture would (correctly) exit 1.
        root = Path(d)
        skills_dir = root / "skills"
        for name in EXPECTED_FINAL_SKILLS:
            body = CONFORMING_SKILL.replace("demo-skill", name)
            if name == "chef-orchestrator":
                body = body.replace(
                    "## Overview\n\nDemo overview text.",
                    "## Overview\n\nRoute work; see `verified-change-loop` for fixes.",
                )
            if not with_red_flags:
                body = body.replace("## Red Flags\n\n- Skipping verification.\n\n", "")
            make_skill(skills_dir, name, body)
        cases = [
            {"id": "c1", "intent": "fix this bug and prove it",
             "expected_skill": "verified-change-loop", "notes": "n"},
        ]
        cases_path = root / "evals" / "routing-cases.json"
        cases_path.parent.mkdir(parents=True, exist_ok=True)
        cases_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        return root, cases_path

    def _run_cli(self, root, cases_path):
        return subprocess.run(
            [sys.executable, "-m", "evals.run_evals",
             "--root", str(root), "--cases", str(cases_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_cli_exits_zero_for_conforming_fixture_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root, cases_path = self._fixture_repo(d, with_red_flags=True)
            proc = self._run_cli(root, cases_path)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_cli_exits_one_when_red_flags_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root, cases_path = self._fixture_repo(d, with_red_flags=False)
            proc = self._run_cli(root, cases_path)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("red-flags", proc.stdout)


class RepoFinalStateTests(unittest.TestCase):
    """Final-state gates for the real repo.

    These must stay green. A failure here itemises exactly what is
    still missing, so a failure is a todo list, not a broken
    runner — do not weaken the assertions to force green.
    """

    def test_repo_structure_final_state(self):
        report = run_all(REPO_ROOT)
        failures = {
            s["skill"]: s["missing"] for s in report["structures"] if not s["ok"]
        }
        self.assertEqual(failures, {}, msg=f"structure gaps: {failures}")

    def test_repo_routing_final_state(self):
        report = run_all(REPO_ROOT)
        failures = [
            (r["id"], r["expected_skill"], r["reason"])
            for r in report["routing"]
            if not r["ok"]
        ]
        self.assertEqual(failures, [], msg=f"routing gaps: {failures}")


if __name__ == "__main__":
    unittest.main()
