"""Deterministic evals for aka-cristi-skills: skill structure + routing.

No LLM, no network, stdlib only. Two check families:

1. Structure: every skills/<name>/SKILL.md must carry frontmatter
   (name + non-empty description) and one section per concept in
   SECTION_CONCEPTS. Headings must match the standard literal titles
   in docs/skill-format.md — the evals enforce the standard, they do
   not guess at synonyms (see SECTION_ALIASES and evals/README.md).

2. Routing: every case in evals/routing-cases.json must resolve to a
   skill that chef-orchestrator actually names. Parse basis: the
   whole text of skills/chef-orchestrator/SKILL.md is searched for
   the expected skill name (word-boundary match). Since PR #66 WP2,
   chef-orchestrator carries a `## Routing` table naming all 32
   capabilities (6 native + 26 vendored); the whole-file match is
   still the parse, and the table is what satisfies it. A match on
   the orchestrator's own name is an identity match (it IS the
   router), not a routing entry; the substantive signal is the other
   five names. The vendored routing cases (one per vendored skill,
   26 total) live separately in evals/vendor-routing-cases.json and
   are checked by evals/run_vendor_evals.py — the native cases file
   stays exactly the six native skills.

Literal-title gate (docs/skill-format.md, 2026-11-26):
  overview            -> literal `## Overview`
  when-to-use         -> literal `## When to Use`
  process             -> literal `## Process`
  common-rationalizations -> heading containing `Rationalization`
  red-flags           -> heading containing `Red Flag`
  verification        -> literal `## Verification`
                         (deliberately NOT "Safety gates": safety
                         constraints are not verification evidence;
                         and NOT the parenthetical "(not real
                         evidence)" in the Handoff output heading)

Frontmatter "Use when": the description MUST carry trigger
language ("Use when ..."), per the agent-skills convention. All six
skills in this repo do. A missing "Use when" in the description is
reported as a soft recommendation, not a hard failure: the hard
gate is name present and well-formed + description non-empty.
(Adopting the convention repo-wide was decided in the 2026-11-26
format-unification pass; the soft rule stays so a future skill
that forgets it is flagged, not silently accepted.)

Exit code: 0 when every hard check passes, 1 otherwise. Soft
recommendations never change the exit code.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED_FINAL_SKILLS = (
    "chef-orchestrator",
    "verified-change-loop",
    "feature-journey-map",
    "skill-evaluation-gate",
    "visual-design",
    "interview-me",
)

SECTION_CONCEPTS = (
    "overview",
    "when-to-use",
    "process",
    "common-rationalizations",
    "red-flags",
    "verification",
)

# concept -> regexes matched (case-insensitive) against H2+ headings.
# Literal titles per docs/skill-format.md: no synonyms accepted.
SECTION_ALIASES = {
    "overview": [r"^overview$"],
    "when-to-use": [r"^when to use$"],
    "process": [r"^process$"],
    "common-rationalizations": [r"rationalization"],
    "red-flags": [r"red flag"],
    "verification": [r"^verification$"],
}

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
FENCE_RE = re.compile(r"^```.*?\n.*?^```\s*$", re.DOTALL | re.MULTILINE)


def parse_frontmatter(text):
    """Parse the leading --- block into a dict; None when absent.

    Handles single-line values and folded (>) / literal (|) blocks.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    out = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not key_match:
            i += 1
            continue
        key, value = key_match.group(1), key_match.group(2).strip()
        if value in (">", ">-", "|", "|-"):
            folded = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                folded.append(lines[i].strip())
                i += 1
            joiner = " " if value.startswith(">") else "\n"
            out[key] = joiner.join(folded)
            continue
        out[key] = value
        i += 1
    return out


def strip_fenced_code(text):
    """Remove ``` fenced blocks so `#` comments inside them are not
    mistaken for headings."""
    return FENCE_RE.sub("", text)


def extract_headings(text):
    """Return [(level, title)] for every ATX heading outside code fences."""
    body = strip_fenced_code(text)
    return [
        (len(m.group(1)), m.group(2).strip().rstrip("#").strip())
        for m in HEADING_RE.finditer(body)
    ]


def discover_skills(skills_dir):
    """Skill dirs under skills_dir that contain a SKILL.md, sorted."""
    root = Path(skills_dir)
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
    )


def check_skill_structure(skill_dir):
    """Structure check for one skill dir.

    Returns a dict with ok / missing concepts / frontmatter detail /
    soft recommendations. Hard-fails on: missing frontmatter, bad or
    missing name, empty description, or any missing concept.
    """
    skill_dir = Path(skill_dir)
    path = skill_dir / "SKILL.md"
    result = {
        "skill": skill_dir.name,
        "path": str(path),
        "ok": False,
        "missing": [],
        "frontmatter": {"present": False},
        "headings": [],
        "recommendations": [],
    }
    if not path.is_file():
        result["missing"] = list(SECTION_CONCEPTS)
        return result
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    name = (frontmatter or {}).get("name", "")
    description = (frontmatter or {}).get("description", "")
    name_ok = bool(NAME_RE.match(name or ""))
    description_ok = bool(description and description.strip())
    has_use_when = "use when" in description.lower()
    result["frontmatter"] = {
        "present": frontmatter is not None,
        "name_ok": name_ok,
        "description_ok": description_ok,
        "description_has_use_when": has_use_when,
    }
    if description_ok and not has_use_when:
        result["recommendations"].append(
            "description lacks 'Use when' trigger language "
            "(docs/skill-format.md requires it in the description)"
        )
    headings = extract_headings(text)
    result["headings"] = [title for _, title in headings]
    titles = [title for level, title in headings if level >= 2]
    missing = []
    for concept in SECTION_CONCEPTS:
        patterns = SECTION_ALIASES[concept]
        found = any(
            re.search(pattern, title, re.IGNORECASE)
            for title in titles
            for pattern in patterns
        )
        if not found:
            missing.append(concept)
    result["missing"] = missing
    result["ok"] = bool(
        frontmatter is not None and name_ok and description_ok and not missing
    )
    return result


def orchestrator_mentions_skill(orchestrator_text, skill_name):
    """Word-boundary match for a skill name in the orchestrator text."""
    pattern = r"(?<![a-z0-9-])" + re.escape(skill_name) + r"(?![a-z0-9-])"
    return re.search(pattern, orchestrator_text, re.IGNORECASE) is not None


def load_routing_cases(cases_path):
    """Load and validate routing cases; raises ValueError on bad data."""
    data = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    cases = data["cases"] if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise ValueError("routing cases must be a non-empty list")
    for case in cases:
        for key in ("id", "intent", "expected_skill", "notes"):
            if not case.get(key):
                raise ValueError(f"routing case missing {key}: {case!r}")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate routing case ids")
    return cases


def check_routing(skills_dir, orchestrator_path, cases):
    """Routing check: each case's expected skill must exist and be
    named by chef-orchestrator. Returns per-case results."""
    discovered = {p.name for p in discover_skills(skills_dir)}
    orchestrator_path = Path(orchestrator_path)
    orchestrator_text = (
        orchestrator_path.read_text(encoding="utf-8")
        if orchestrator_path.is_file()
        else ""
    )
    results = []
    for case in cases:
        expected = case["expected_skill"]
        if expected not in discovered:
            results.append({**case, "ok": False, "reason": "skill-not-found"})
        elif not orchestrator_mentions_skill(orchestrator_text, expected):
            results.append(
                {**case, "ok": False, "reason": "not-routed-by-chef-orchestrator"}
            )
        else:
            results.append({**case, "ok": True, "reason": "routed"})
    return results


def run_all(repo_root, cases_path=None, orchestrator_path=None):
    """Run both check families over a repo root; return a report dict."""
    repo_root = Path(repo_root)
    skills_dir = repo_root / "skills"
    cases_path = (
        Path(cases_path) if cases_path else repo_root / "evals" / "routing-cases.json"
    )
    orchestrator_path = (
        Path(orchestrator_path)
        if orchestrator_path
        else skills_dir / "chef-orchestrator" / "SKILL.md"
    )
    structures = [check_skill_structure(p) for p in discover_skills(skills_dir)]
    discovered_names = {s["skill"] for s in structures}
    for name in EXPECTED_FINAL_SKILLS:
        if name not in discovered_names:
            structures.append(
                {
                    "skill": name,
                    "path": str(skills_dir / name / "SKILL.md"),
                    "ok": False,
                    "missing": list(SECTION_CONCEPTS),
                    "frontmatter": {"present": False},
                    "headings": [],
                    "recommendations": [],
                    "reason": "skill-not-found",
                }
            )
    structures.sort(key=lambda s: s["skill"])
    cases = load_routing_cases(cases_path)
    routing = check_routing(skills_dir, orchestrator_path, cases)
    summary = {
        "skills_checked": len(structures),
        "skills_ok": sum(1 for s in structures if s["ok"]),
        "routing_cases": len(routing),
        "routing_ok": sum(1 for r in routing if r["ok"]),
        "recommendations": sum(len(s.get("recommendations", [])) for s in structures),
    }
    return {"structures": structures, "routing": routing, "summary": summary}


def format_summary(report):
    """One line per failure plus counts; empty output means all green
    apart from the header (callers should still print the counts)."""
    lines = []
    for skill in report["structures"]:
        if skill["ok"]:
            lines.append(f"  OK   {skill['skill']}")
        else:
            detail = skill.get("reason") or f"missing: {', '.join(skill['missing'])}"
            lines.append(f"  FAIL {skill['skill']}: {detail}")
    for case in report["routing"]:
        if not case["ok"]:
            lines.append(
                f"  FAIL {case['id']} -> {case['expected_skill']}: {case['reason']}"
            )
    summary = report["summary"]
    lines.append(
        f"skills {summary['skills_ok']}/{summary['skills_checked']} ok; "
        f"routing {summary['routing_ok']}/{summary['routing_cases']} ok; "
        f"{summary['recommendations']} soft recommendation(s)"
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic evals for aka-cristi-skills (no LLM, no network)."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repo root (default: parent of evals/).",
    )
    parser.add_argument("--cases", default=None, help="Routing cases JSON path.")
    parser.add_argument(
        "--orchestrator", default=None, help="chef-orchestrator SKILL.md path."
    )
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    args = parser.parse_args(argv)
    report = run_all(args.root, args.cases, args.orchestrator)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_summary(report))
    hard_ok = (
        report["summary"]["skills_ok"] == report["summary"]["skills_checked"]
        and report["summary"]["routing_ok"] == report["summary"]["routing_cases"]
    )
    return 0 if hard_ok else 1


if __name__ == "__main__":
    sys.exit(main())
