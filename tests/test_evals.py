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
    orchestrator_mentions_skill,
    run_all,
)
from evals.run_vendor_evals import (
    check_index_coverage,
    check_vendor_frontmatter,
    run_vendor_all,
)
from tools.generate_skill_index import build_index, render

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "evals" / "routing-cases.json"
VENDOR_CASES_PATH = REPO_ROOT / "evals" / "vendor-routing-cases.json"
VENDOR_SKILLS_DIR = REPO_ROOT / "vendor" / "addy-agent-skills" / "skills"
INDEX_PATH = REPO_ROOT / "docs" / "skill-index.json"

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


# A vendored skill body with frontmatter only — no standard sections
# at all. The vendor adapter evals check frontmatter, not sections:
# that is the Option A exemption (docs/dedup-decisions.md §4).
VENDOR_MINIMAL_SKILL = """---
name: vdemo-skill
description: Do vendor demo work. Use when a vendor demo is needed.
---

# Vendor Demo Skill

Some prose, no standard sections.
"""


class VendorFrontmatterFixtureTests(unittest.TestCase):
    def test_frontmatter_only_skill_passes(self):
        with tempfile.TemporaryDirectory() as d:
            result = check_vendor_frontmatter(
                make_skill(d, "vdemo-skill", VENDOR_MINIMAL_SKILL)
            )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["problems"], [])
        self.assertTrue(result["frontmatter"]["description_has_use_when"])

    def test_name_must_match_directory(self):
        body = VENDOR_MINIMAL_SKILL.replace("name: vdemo-skill", "name: other-skill")
        with tempfile.TemporaryDirectory() as d:
            result = check_vendor_frontmatter(make_skill(d, "vdemo-skill", body))
        self.assertFalse(result["ok"])
        self.assertIn("!= directory", result["problems"][0])

    def test_missing_use_when_is_soft_only(self):
        body = VENDOR_MINIMAL_SKILL.replace(
            "description: Do vendor demo work. Use when a vendor demo is needed.",
            "description: Do vendor demo work.",
        )
        with tempfile.TemporaryDirectory() as d:
            result = check_vendor_frontmatter(make_skill(d, "vdemo-skill", body))
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["recommendations"]), 1)


class VendorIndexFixtureTests(unittest.TestCase):
    # Fixture skills use real PHASES-covered names (native interview-me,
    # vendored test-driven-development): generate_skill_index raises on
    # any collected skill without a PHASES entry, so demo names that
    # are not in the taxonomy cannot be used to build an index.
    def _fixture_repo(self, d):
        root = Path(d)
        make_skill(
            root / "skills",
            "interview-me",
            CONFORMING_SKILL.replace("demo-skill", "interview-me"),
        )
        vendor_dir = root / "vendor" / "addy-agent-skills" / "skills"
        make_skill(
            vendor_dir,
            "test-driven-development",
            VENDOR_MINIMAL_SKILL.replace(
                "vdemo-skill", "test-driven-development"
            ),
        )
        index_path = root / "docs" / "skill-index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(render(build_index(root)), encoding="utf-8")
        return root, index_path

    def test_missing_phase_raises(self):
        # A collected skill with no PHASES entry must fail loud, never
        # land in the index with a silent empty phase (WP4 issue 2).
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skill(root / "skills", "demo-skill", CONFORMING_SKILL)
            (root / "vendor" / "addy-agent-skills" / "skills").mkdir(
                parents=True, exist_ok=True
            )
            with self.assertRaises(ValueError) as ctx:
                build_index(root)
        self.assertIn("no routing phase", str(ctx.exception))
        self.assertIn("native/demo-skill", str(ctx.exception))

    def test_generated_index_covers_fixture_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root, index_path = self._fixture_repo(d)
            result = check_index_coverage(root, index_path)
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["counts"], {"native": 1, "vendor": 1, "index_entries": 2})

    def test_tampered_skill_file_fails_hash_check(self):
        with tempfile.TemporaryDirectory() as d:
            root, index_path = self._fixture_repo(d)
            vendor_skill = (
                root
                / "vendor"
                / "addy-agent-skills"
                / "skills"
                / "test-driven-development"
                / "SKILL.md"
            )
            vendor_skill.write_text(
                vendor_skill.read_text(encoding="utf-8") + "\nTampered.\n",
                encoding="utf-8",
            )
            result = check_index_coverage(root, index_path)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("sha256 mismatch" in p for p in result["problems"]),
            result["problems"],
        )

    def test_missing_index_entry_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root, index_path = self._fixture_repo(d)
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["skills"] = [
                s for s in index["skills"] if s["name"] != "test-driven-development"
            ]
            index_path.write_text(json.dumps(index), encoding="utf-8")
            result = check_index_coverage(root, index_path)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "index missing vendored skill: test-driven-development" in p
                for p in result["problems"]
            ),
            result["problems"],
        )


class VendorEvalsFinalStateTests(unittest.TestCase):
    """Final-state gates for the vendored skill set (PR #66 WP2).

    Same rule as the native gates: a failure here is a todo list,
    not a broken runner — do not weaken the assertions to force green.
    """

    def test_vendor_evals_final_state(self):
        report = run_vendor_all(REPO_ROOT)
        frontmatter_failures = {
            s["skill"]: s["problems"] for s in report["frontmatter"] if not s["ok"]
        }
        routing_failures = [
            (r["id"], r["expected_skill"], r["reason"])
            for r in report["routing"]
            if not r["ok"]
        ]
        self.assertEqual(frontmatter_failures, {}, msg=f"frontmatter gaps: {frontmatter_failures}")
        self.assertEqual(routing_failures, [], msg=f"routing gaps: {routing_failures}")
        self.assertTrue(report["index"]["ok"], msg=f"index gaps: {report['index']['problems']}")

    def test_vendor_cases_cover_all_26_vendored_skills_once_each(self):
        cases = load_routing_cases(VENDOR_CASES_PATH)
        vendored = {p.name for p in VENDOR_SKILLS_DIR.iterdir() if p.is_dir()}
        by_skill = Counter(c["expected_skill"] for c in cases)
        self.assertEqual(sorted(by_skill), sorted(vendored), "one case per vendored skill")
        for skill, count in by_skill.items():
            self.assertEqual(count, 1, skill)

    def test_chef_routing_names_all_32_skills(self):
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        chef_text = (
            REPO_ROOT / "skills" / "chef-orchestrator" / "SKILL.md"
        ).read_text(encoding="utf-8")
        missing = [
            f"{e['source']}/{e['name']}"
            for e in index["skills"]
            if not orchestrator_mentions_skill(chef_text, e["name"])
        ]
        self.assertEqual(missing, [], msg=f"chef routing table misses: {missing}")

    def test_every_index_entry_has_phase(self):
        # PHASES coverage lock (WP4 issue 2): every collected skill
        # must carry a non-empty routing phase; a missing entry raises
        # in build_index (see test_missing_phase_raises), this gate
        # pins the real repo at 32/32.
        index = build_index(REPO_ROOT)
        self.assertEqual(len(index["skills"]), 32)
        missing = [
            f"{e['source']}/{e['name']}"
            for e in index["skills"]
            if not e["phase"]
        ]
        self.assertEqual(missing, [], msg=f"skills without phase: {missing}")

    def test_skill_index_is_fresh(self):
        proc = subprocess.run(
            [sys.executable, "tools/generate_skill_index.py", "--check"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_combined_routing_cases_total_44(self):
        native = load_routing_cases(CASES_PATH)
        vendor = load_routing_cases(VENDOR_CASES_PATH)
        self.assertEqual(len(native), 18)
        self.assertEqual(len(vendor), 26)
        self.assertEqual(len(native) + len(vendor), 44)


if __name__ == "__main__":
    unittest.main()
