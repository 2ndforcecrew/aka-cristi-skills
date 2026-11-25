# Evals — deterministic skill structure + routing checks

No LLM, no network, stdlib only. The point (borrowed from
addyosmani/agent-skills): a skill that never fires, or fires for the
wrong intent, is a silent regression. These evals catch that in CI
instead of by feel.

## Files

| File | What it is |
|---|---|
| `evals/routing-cases.json` | 18 intent → expected-skill cases, 3 per skill, 6 skills |
| `evals/run_evals.py` | The runner (structure + routing), also the CLI |
| `tests/test_evals.py` | unittest wiring: fixture tests + final-state repo gates |

## Run

```bash
python3 -m evals.run_evals            # text summary, exit 0/1
python3 -m evals.run_evals --json     # full report as JSON
python3 -m unittest tests.test_evals  # the eval tests only
python3 -m unittest discover -s tests # whole suite (evals included)
```

Exit code is 0 only when every hard check passes. Soft
recommendations (see below) never change the exit code.

## Check 1 — structure

For every `skills/<name>/SKILL.md`: frontmatter must have a
well-formed `name` and a non-empty `description`, and the body must
cover one section per concept. Headings must match the **literal
standard titles** in `docs/skill-format.md` — the evals enforce the
standard, they do not accept synonyms (tightened 2026-11-26 in the
format-unification pass; previously aliases like `Procedure` /
`Workflow` / `Evidence contract` were accepted):

| Concept | Required heading |
|---|---|
| overview | `## Overview` |
| when-to-use | `## When to Use` |
| process | `## Process` |
| common-rationalizations | heading containing `Rationalization` |
| red-flags | heading containing `Red Flag` |
| verification | `## Verification` |

Deliberate non-matches: `Safety gates` is safety, not verification
evidence; the parenthetical `(not real evidence)` in the Handoff
output heading is not a verification section.

Soft rule: the description *must* carry `Use when` trigger
language (agent-skills convention, now the repo standard in
`docs/skill-format.md`). All six skills do. A description without
it is reported as a recommendation, not a failure — the hard gate
is name present and well-formed + description non-empty. The soft
rule stays so a future skill that forgets the trigger language is
flagged, not silently accepted.

## Check 2 — routing

For each case in `routing-cases.json`, the expected skill must exist
and be named by `skills/chef-orchestrator/SKILL.md`. Parse basis:
chef-orchestrator has no routing table; its routing surface is the
`When to Use` paragraph plus the `Suggested complementary Skills`
list, so the whole file text is searched for the skill name
(word-boundary match). A match on the orchestrator's own name is an
identity match (it IS the router); the substantive signal is the
other five names.

## Known red — closed in this PR (history)

The evals found three real gaps on the run that built this file
(2026-11-26), and all three were closed in this PR — not by weakening
assertions, but by fixing the repo. Kept here as evidence the evals
catch real problems:

- Structure: `chef-orchestrator` and `feature-journey-map` had no
  verification section (`missing: ['verification']` each). Closed by
  adding a `## Verification` section to both skills.
- Routing: the 3 `visual-design` cases failed —
  `not-routed-by-chef-orchestrator`. Closed by adding a routing line
  for visual-design to chef-orchestrator.
- Unrelated to evals, same run: `test_cli` and `test_mcp_server`
  each had one `list_skills returns five` test failing because
  `interview-me` landed as a 6th skill and those tests hard-coded 5.
  Closed by updating their EXPECTED_SKILLS to 6.

Current state: no known red. `python3 -m evals.run_evals` exits 0
(skills 6/6 ok; routing 18/18 ok). 0 soft recommendations: all six
skill descriptions now carry `Use when` trigger language, and the
structure gate enforces the literal titles in
`docs/skill-format.md`.
