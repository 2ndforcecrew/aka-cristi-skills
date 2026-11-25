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
cover one section per concept. Headings are matched **by concept,
not by literal agent-skills titles**, because this repo's skills use
their own section names (decided from the actual headings,
2026-11-26):

| Concept | Accepted headings |
|---|---|
| overview | H1 title + non-empty frontmatter description (repo convention; only interview-me has a literal `## Overview`) |
| when-to-use | `Use when` / `When to use` / `Trigger …` |
| process | `Procedure` / `Workflow …` / `Process` |
| common-rationalizations | heading containing `Rationalization` |
| red-flags | heading containing `Red Flag` |
| verification | `Verification` / `Evidence check` / `Evidence contract` / `Quality gates` / `Acceptance` |

Deliberate non-matches: `Safety gates` is safety, not verification
evidence; the parenthetical `(not real evidence)` in the Handoff
output heading is why `evidence` only matches at the start of a
heading.

Soft rule: the description *should* carry `Use when` trigger
language (agent-skills convention). Only visual-design and
interview-me do today; the other four put trigger language in the
body `When to use` section instead. Reported as a recommendation,
not a failure — adopting the convention repo-wide (or dropping the
requirement) is a parent decision.

## Check 2 — routing

For each case in `routing-cases.json`, the expected skill must exist
and be named by `skills/chef-orchestrator/SKILL.md`. Parse basis:
chef-orchestrator has no routing table; its routing surface is the
`Use when` paragraph plus the `Suggested complementary Skills`
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
(skills 6/6 ok; routing 18/18 ok). 4 soft recommendations remain:
four skills' frontmatter descriptions lack "Use when" trigger
language — by design, these never affect the exit code.
