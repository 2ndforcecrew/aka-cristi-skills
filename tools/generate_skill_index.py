#!/usr/bin/env python3
"""Generate the hybrid skill index (docs/skill-index.json).

Reads the frontmatter of every SKILL.md under skills/ (native) and
vendor/addy-agent-skills/skills/ (vendored, pinned revision
e997ac5b9a74eab332d5e9793bb38a38c8cfdd74 / v0.6.18), and writes one
lightweight entry per skill: name, source, installable verdict,
one-sentence description, trigger keywords, routing phase, and the
sha256 of the SKILL.md (integrity anchor — the vendor evals compare
the recorded hash against the working tree so an accidental edit to
a vendored SKILL.md is caught without needing the upstream clone).

Deterministic: entries are sorted by name, JSON keys are sorted,
output ends with a single newline. Re-running produces a
byte-identical file. Use --check to verify the on-disk index is
fresh (CI guard); exit 1 on any difference.

Stdlib only, no network. The single installability exception is
vendored interview-me (reference only — the native interview-me
takes priority; see docs/dedup-decisions.md). The phase taxonomy
mirrors the discovery flowchart in
vendor/addy-agent-skills/skills/using-agent-skills/SKILL.md, with
the six native skills slotted into their phases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

VENDOR_REVISION = "e997ac5b9a74eab332d5e9793bb38a38c8cfdd74"
VENDOR_VERSION = "0.6.18"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Vendored skills that are reference-only (not installed). Everything
# else is installable. Keys are "vendor/<name>".
REFERENCE_ONLY = {
    "vendor/interview-me": "reference only — native interview-me takes priority",
}

# Routing phase per skill (key: "native/<name>" or "vendor/<name>").
# Phases follow the using-agent-skills discovery flowchart; native
# skills slot into the phase where they fire. Every collected skill
# MUST have an entry here: collect_skills() raises on a missing key
# (fail loud, never a silent empty phase — a new skill without a
# phase must be classified before the index can be generated).
PHASES = {
    "native/chef-orchestrator": "Orchestrate",
    "native/interview-me": "Define",
    "native/feature-journey-map": "Plan",
    "native/verified-change-loop": "Verify",
    "native/skill-evaluation-gate": "Review",
    "native/visual-design": "Build",
    "vendor/accessibility-engineering": "Review",
    "vendor/api-and-interface-design": "Build",
    "vendor/browser-testing-with-devtools": "Verify",
    "vendor/ci-cd-and-automation": "Ship",
    "vendor/code-review-and-quality": "Review",
    "vendor/code-simplification": "Review",
    "vendor/constraint-driven-development": "Define",
    "vendor/context-engineering": "Build",
    "vendor/debugging-and-error-recovery": "Verify",
    "vendor/deprecation-and-migration": "Ship",
    "vendor/documentation-and-adrs": "Ship",
    "vendor/doubt-driven-development": "Build",
    "vendor/frontend-ui-engineering": "Build",
    "vendor/git-workflow-and-versioning": "Ship",
    "vendor/idea-refine": "Define",
    "vendor/incremental-implementation": "Build",
    "vendor/interview-me": "Define",
    "vendor/observability-and-instrumentation": "Ship",
    "vendor/performance-optimization": "Review",
    "vendor/planning-and-task-breakdown": "Plan",
    "vendor/security-and-hardening": "Review",
    "vendor/shipping-and-launch": "Ship",
    "vendor/source-driven-development": "Build",
    "vendor/spec-driven-development": "Define",
    "vendor/test-driven-development": "Verify",
    "vendor/using-agent-skills": "Meta",
}

# Short routing notes, only where the default trigger text is not
# enough to disambiguate. Keys are "native/<name>" or "vendor/<name>".
ROUTE_NOTES = {
    "vendor/interview-me": "reference only — route to native interview-me",
    "vendor/using-agent-skills": "meta — discovery flowchart reference, not a task skill",
    "vendor/doubt-driven-development": (
        "cross-model second opinion only with explicit user "
        "authorization per invocation; read-only sandbox"
    ),
    "vendor/constraint-driven-development": (
        "interview needs a live user; non-interactive contexts apply the floor only"
    ),
    "native/visual-design": (
        "design direction and style judgement; engineering UI implementation "
        "goes to frontend-ui-engineering"
    ),
    "vendor/frontend-ui-engineering": (
        "engineering UI implementation; design direction goes to visual-design"
    ),
    "vendor/test-driven-development": (
        "new logic or behaviour goes TDD first; a reported defect or CI "
        "failure goes to verified-change-loop"
    ),
    "native/verified-change-loop": (
        "reported defect, CI failure, or change needing independent "
        "verification; new logic goes to test-driven-development"
    ),
    "vendor/code-review-and-quality": (
        "reviews code diffs; reviewing a Skill goes to skill-evaluation-gate"
    ),
    "native/skill-evaluation-gate": (
        "reviews candidate Skills; reviewing code goes to code-review-and-quality"
    ),
    "vendor/planning-and-task-breakdown": (
        "spec goes to ordered tasks; mapping a real user journey goes to "
        "feature-journey-map"
    ),
    "native/feature-journey-map": (
        "map a real user journey after planning; decomposing a spec goes to "
        "planning-and-task-breakdown"
    ),
}


def parse_frontmatter(text):
    """Parse the leading --- block into a dict; None when absent."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    out = {}
    for line in match.group(1).splitlines():
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if key_match:
            out[key_match.group(1)] = key_match.group(2).strip()
    return out


def first_sentence(text):
    """First sentence of a description (the one-line summary)."""
    text = " ".join(text.split())
    parts = re.split(r"\.\s+", text, maxsplit=1)
    sentence = parts[0].strip()
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def trigger_text(description, limit=300):
    """The 'Use when ...' portion of a description, capped at a word
    boundary so the index stays light."""
    match = re.search(r"use when\b", description, re.IGNORECASE)
    if not match:
        return ""
    triggers = description[match.start():].strip()
    triggers = " ".join(triggers.split())
    if len(triggers) <= limit:
        return triggers
    cut = triggers[:limit].rsplit(" ", 1)[0]
    return cut + " …"


def collect_skills(repo_root):
    """Read every native + vendored SKILL.md; return entry dicts."""
    entries = []
    for source, skills_dir in (
        ("native", repo_root / "skills"),
        ("vendor", repo_root / "vendor" / "addy-agent-skills" / "skills"),
    ):
        for skill_dir in sorted(skills_dir.iterdir()):
            path = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            frontmatter = parse_frontmatter(text)
            if frontmatter is None:
                raise ValueError(f"{path}: missing frontmatter")
            name = frontmatter.get("name", "")
            description = frontmatter.get("description", "")
            if not NAME_RE.match(name or ""):
                raise ValueError(f"{path}: bad frontmatter name {name!r}")
            if name != skill_dir.name:
                raise ValueError(
                    f"{path}: frontmatter name {name!r} != directory {skill_dir.name!r}"
                )
            if not description.strip():
                raise ValueError(f"{path}: empty frontmatter description")
            key = f"{source}/{name}"
            phase = PHASES.get(key)
            if phase is None:
                raise ValueError(
                    f"{path}: no routing phase for {key!r} — add it to PHASES"
                )
            entries.append(
                {
                    "name": name,
                    "source": source,
                    "installable": key not in REFERENCE_ONLY,
                    "phase": phase,
                    "description": first_sentence(description),
                    "triggers": trigger_text(description),
                    "route_note": ROUTE_NOTES.get(
                        key, REFERENCE_ONLY.get(key, "")
                    ),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                }
            )
    entries.sort(key=lambda e: (e["source"], e["name"]))
    return entries


def build_index(repo_root):
    """Build the full index document."""
    entries = collect_skills(repo_root)
    native = [e for e in entries if e["source"] == "native"]
    vendor = [e for e in entries if e["source"] == "vendor"]
    return {
        "generated_by": "tools/generate_skill_index.py",
        "generated_from": {
            "native": "skills/",
            "vendor": "vendor/addy-agent-skills/skills/",
            "vendor_revision": VENDOR_REVISION,
            "vendor_version": VENDOR_VERSION,
        },
        "counts": {
            "native": len(native),
            "vendor": len(vendor),
            "installable": sum(1 for e in entries if e["installable"]),
            "reference_only": sum(1 for e in entries if not e["installable"]),
        },
        "skills": entries,
    }


def render(index):
    """Deterministic JSON rendering (sorted keys, 2-space indent)."""
    return json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate docs/skill-index.json from SKILL.md frontmatter."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repo root (default: parent of tools/).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: <root>/docs/skill-index.json).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when the on-disk index differs from the generated one.",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    output = Path(args.output) if args.output else root / "docs" / "skill-index.json"
    index = build_index(root)
    text = render(index)
    if args.check:
        current = output.read_text(encoding="utf-8") if output.is_file() else ""
        if current != text:
            print(f"index out of date: {output} (run without --check to regenerate)")
            return 1
        print(f"index fresh: {output} ({index['counts']['installable']} installable, "
              f"{index['counts']['reference_only']} reference-only)")
        return 0
    output.write_text(text, encoding="utf-8")
    print(f"wrote {output} ({len(index['skills'])} skills, "
          f"{index['counts']['installable']} installable, "
          f"{index['counts']['reference_only']} reference-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
