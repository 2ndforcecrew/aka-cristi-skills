<!--
  Dedup decisions for the PR #66 hybrid skill set (WP2).
  Decision record, not a skill: it lives in docs/ so it stays out of
  the agent's working set. CHEF's routing table
  (skills/chef-orchestrator/SKILL.md, "## Routing") is the runtime
  form of these decisions; this file is the auditable record behind it.
-->

# Dedup decisions — native 6 + vendored 26 (PR #66, WP2)

- Pinned vendor revision: `e997ac5b9a74eab332d5e9793bb38a38c8cfdd74` (v0.6.18)
- Date: 2026-11-26
- Counts: **32 capabilities** (6 native + 26 vendored), **31 installable**,
  **1 reference-only** (vendored `interview-me`)
- Rule: on a near-identical duplicate, the native skill wins — it already
  carries this repo's format standard, evals routing, and stop tests.
  A vendored skill is never retitled or edited to fit the native format
  (red line R1: vendor files stay byte-identical to upstream).

## 1. Overlap pairs (decided, with evidence)

| Vendored | Native | Overlap | Verdict |
|---|---|---|---|
| `interview-me` | `interview-me` | Descriptions nearly verbatim: one question at a time until ~95% confidence; explicit yes before continuing. Vendored adds triggers "are we sure?" / "stress-test my thinking". | **Native priority.** Vendored copy stays in `vendor/` as reference only, never installed. Routing table points to native only. |
| `test-driven-development` | `verified-change-loop` | Bug-fix path overlaps (TDD Prove-It Pattern vs VCL reproduce → fix → replay). TDD is broader (any logic change starts with a failing test); VCL is the verification loop. | **Both, split by trigger.** New logic / behaviour change → TDD first. Reported defect / CI failure / change needing independent verification → VCL. Chainable: TDD writes the test, VCL replays the user scenario. |
| `planning-and-task-breakdown` | `feature-journey-map` | Both decompose work. Planning turns a spec into ordered implementable tasks; FJM maps a real user path into replayable scenarios. | **Both, in order.** Planning first (spec → tasks), then FJM (tasks → real user journey). Trigger text in the routing table separates them. |
| `code-review-and-quality` | `skill-evaluation-gate` | Both "review", different objects: vendored reviews a code diff before merge; native reviews a candidate Skill before installation/release. | **Both, split by object.** Reviewing code → vendored. Reviewing a Skill → native. Neither substitutes for the other. |
| `frontend-ui-engineering` / `accessibility-engineering` | `visual-design` | Web/UI and a11y overlap. Native visual-design is broader (brand, packaging, photography, motion, 58 design cases); vendored pair is engineering implementation and WCAG audit. | **Split by layer.** Brand / visual direction / layout / style judgement → native visual-design. Production UI implementation and a11y audit → vendored pair. Chainable: visual-design sets direction, frontend-ui-engineering builds it. |
| `using-agent-skills` (meta) | `chef-orchestrator` | Both "route". Upstream AGENTS.md explicitly rejects a separate router persona; routing is the orchestrator's job. | **CHEF routes; no new persona.** `using-agent-skills` is referenced by CHEF only as the discovery flowchart (phase → skill). It is not a routing entity and never spawns reviewers. |

## 2. Full verdict table (all 26 vendored + 6 native)

Install = the skill is installed with its references/scripts and named
in the CHEF routing table. Reference-only = kept in `vendor/` for
consultation, never installed, never routed to.

### 2a. Vendored — install (25)

| Skill | Phase | Trigger (user's words) | Do NOT trigger when |
|---|---|---|---|
| `accessibility-engineering` | Review | "audit this page for accessibility" / "check screen reader and contrast issues before shipping" | Design direction or style judgement is wanted (→ visual-design); building a new UI (→ frontend-ui-engineering) |
| `api-and-interface-design` | Build | "design this API" / "define the contract between frontend and backend" | The interface already exists and only needs implementing |
| `browser-testing-with-devtools` | Verify | "test this in a real browser" / "check the console errors" / "verify the visual output" (requires chrome-devtools MCP) | The check can be done with unit tests or static review alone |
| `ci-cd-and-automation` | Ship | "set up the CI pipeline" / "automate the deployment" / "configure the quality gates in CI" | A one-off local build; a quality bar for the project (→ constraint-driven-development) |
| `code-review-and-quality` | Review | "review this diff / PR before merging" | Reviewing a Skill (→ skill-evaluation-gate); the change is a one-line rename |
| `code-simplification` | Review | "this code works but is hard to read" / "clean up this function without changing behaviour" | Behaviour must change (→ test-driven-development first); the code is already simple |
| `constraint-driven-development` | Define | "set up constraints" / "define our standards" / "stop the agent shipping junk" / "an agent keeps silencing checks to get to green" | A CONSTRAINTS.md already exists and is not changing (read it instead); one-off scripts and throwaway prototypes |
| `context-engineering` | Build | "starting a new session" / "output quality is degrading" / "switching between tasks" / "set up rules files for this project" | The task is a single well-specified change with context already loaded |
| `debugging-and-error-recovery` | Verify | "tests fail" / "it worked yesterday and broke" / "what broke and why" | The failure is already reproduced and the fix is known (→ test-driven-development / verified-change-loop) |
| `deprecation-and-migration` | Ship | "remove this old API" / "migrate users to the new implementation" / "rename a column without downtime" | The old code is still in active use with no migration plan |
| `documentation-and-adrs` | Ship | "document this architecture decision" / "the docs drifted from the code" | Writing code comments only; the decision is not yet made |
| `doubt-driven-development` | Build | "cross-examine every assumption" / "stress-test this plan for hidden failure modes" / "this touches production auth" | Mechanical operations, one-line changes with obvious correctness, or the user explicitly asked for speed over verification |
| `frontend-ui-engineering` | Build | "build this page / component" / "implement the layout" / "it needs to look production-quality" | Brand / visual direction is undecided (→ visual-design first) |
| `git-workflow-and-versioning` | Ship | "split this into clean commits" / "write the changelog" / "cut a release" | The change is uncommitted exploration with no history to keep |
| `idea-refine` | Define | "ideate" / "refine this idea" / "stress-test my plan" (before committing to a plan) | Requirements are already clear (→ spec-driven-development) |
| `incremental-implementation` | Build | "this touches more than one file" / "roll it out behind a feature flag" / "this is too big to land in one step" | A single-file change with an obvious shape |
| `observability-and-instrumentation` | Ship | "add logging / metrics / tracing" / "we can't tell what happened in production" | Local-only code with no production surface |
| `performance-optimization` | Review | "this is slow" / "Core Web Vitals need improvement" / "fix the N+1 queries" | No measured bottleneck (measure first; do not optimize on suspicion) |
| `planning-and-task-breakdown` | Plan | "break this spec into tasks" / "this is too large to start" / "estimate the scope" | No spec exists yet (→ spec-driven-development); mapping a user journey (→ feature-journey-map) |
| `security-and-hardening` | Review | "audit this login flow" / "is this input handler safe" / "check dependencies for vulnerabilities" | The code handles no untrusted data, auth, sessions, or third-party input |
| `shipping-and-launch` | Ship | "prepare to deploy to production" / "what needs to be in place before shipping" / "plan a staged rollout" | Deploying to a local dev environment only |
| `source-driven-development` | Build | "verify this against the official docs before implementing" / "I want source-cited code, not outdated patterns" | The framework is one the team already knows cold; the answer is in the codebase |
| `spec-driven-development` | Define | "no specification exists yet" / "draft the PRD" / "requirements are unclear" | A spec already exists and is current (→ planning-and-task-breakdown) |
| `test-driven-development` | Verify | "write a failing test first" / "prove this works" / "fix this bug" (new logic or behaviour change) | A reported defect or CI failure needing independent verification (→ verified-change-loop); docs-only change |
| `using-agent-skills` | Meta | "which skill should handle this?" / "where do I start?" | Never routed as a task skill — it is the discovery flowchart CHEF consults, not work itself |

### 2b. Vendored — reference only (1)

| Skill | Reason |
|---|---|
| `interview-me` | Near-verbatim duplicate of native `interview-me`. Native already has the repo format standard (10 sections, literal titles), evals routing, and the 95% stop test. Kept in `vendor/` as reference only. |

### 2c. Native — stay (6)

| Skill | Phase | Note |
|---|---|---|
| `chef-orchestrator` | Orchestrate | The router. Owns the routing table; no new router persona is created. |
| `interview-me` | Define | Native priority over the vendored copy (see §1). |
| `feature-journey-map` | Plan | Runs after planning-and-task-breakdown on user-facing paths. |
| `verified-change-loop` | Verify | Runs after test-driven-development on reported defects and CI failures. |
| `skill-evaluation-gate` | Review | Evaluates candidate Skills only — never code diffs. |
| `visual-design` | Build | Design direction and style judgement; hands off engineering implementation to frontend-ui-engineering. |

## 3. Hidden-overlap review (beyond the plan's table)

Checked by reading the full skill bodies, not just frontmatter.

### 3a. `doubt-driven-development` vs `skill-evaluation-gate` — no conflict

Doubt-driven is an **in-flight, per-decision** adversarial review: a
fresh-context reviewer cross-examines a non-trivial decision
(CLAIM → EXTRACT → DOUBT → RECONCILE → STOP) while correction is
still cheap. It states explicitly: "This is not `/review`. `/review`
is a verdict on a finished artifact." Its "Interaction with Other
Skills" section already records the split with
`code-review-and-quality`, `source-driven-development`, and
`test-driven-development` (whose RED step *is* the doubt step for
behavioural claims).

`skill-evaluation-gate` evaluates a **candidate Skill artifact**
against a scenario rubric before installation or release. Different
object (a decision vs a Skill), different timing (in-flight vs
pre-install). Complementary, not overlapping.

Safety note carried into the routing table: doubt-driven's
cross-model escalation invokes external CLIs (`codex`, `gemini`).
Each invocation needs explicit user authorization, a PATH check, a
working-binary test, and a read-only sandbox. Non-interactive
contexts skip cross-model and announce the skip. (Risk R-Doubt.)

### 3b. `constraint-driven-development` vs CHEF global rules — no conflict

Constraint-driven writes a **per-project** quality bar
(`CONSTRAINTS.md`: floor + numbered dimensions + ratchets) and guards
it against being weakened to make a change pass. CHEF's global rules
(`shared-training/rules/`, bundled into chef-orchestrator) are
**agent operating rules** — how agents work, verify, and hand off.
Different objects (a project's bar vs an agent's conduct), different
scope. Constraint-driven plugs *into* the rules layer (it adds one
line to `AGENTS.md`/`CLAUDE.md`: read `CONSTRAINTS.md` before
writing code); it does not replace it.

Note: its four-question interview needs a live user. In
non-interactive contexts it applies the floor only and flags the
rest for a human.

### 3c. `context-engineering` vs CHEF context management — no conflict

Context-engineering **configures** session context: the five-level
hierarchy (rules files → specs → source → errors → history),
packing strategies, budget management (what to cut first, what to
protect, compress before dropping), and confusion management.
CHEF **consumes** context (Process step 2 Inspect reads configs;
step 9 Evolve extracts lessons) but never configures the budget or
writes rules files. One sets up the desk, the other works at it.

Trigger split: context-engineering fires at session start, when
output quality degrades, when switching tasks, or when setting up
rules files. CHEF fires when a task spans agents or lanes. Its
trust-levels rule (external data is untrusted input, never
instructions) matches this repo's safety rules.

## 4. Why the vendor format is exempt (Option A, decided)

Hand-survey of all 26 vendored `SKILL.md` files (headings outside
code fences):

- Only **1 of 26** (`observability-and-instrumentation`) has a
  literal `## Process` heading. The other 25 use `The Process`,
  `The TDD Cycle`, `Workflow`, `The Planning Process`,
  `Process: Threat Model First`, or no process-titled section at all.
- `using-agent-skills` has **none** of the native standard sections
  except `## Overview` — no `When to Use`, no `Process`, no `Common
  Rationalizations`, no `Red Flags`, no `Verification`. It is a
  discovery flowchart, not a standard skill.
- All 26 have frontmatter `name` + non-empty `description` with a
  `Use when` clause, and all 26 have `## Overview` and
  `## When to Use`.

Retitling vendor headings to pass the native structure gate would
break byte identity (red line R1) and make future upstream diffs
unverifiable. Expanding the native gate with aliases (Option B)
would need a 25-entry alias table and still could not cover
`using-agent-skills`. So: **Option A** — vendored skills are exempt
from the native structure gate and are checked instead by the vendor
adapter evals (`evals/run_vendor_evals.py`): frontmatter present +
name matches directory + description non-empty, routing-index
coverage of all 26, and sha256 of each `SKILL.md` against the
generated index. Full-tree byte identity remains WP1 evidence (cmp
records), not an eval — the evals are stdlib-only with no network
and no upstream clone.

## 5. Combination chains (canonical)

- Full feature: `interview-me` → `idea-refine` →
  `spec-driven-development` → `constraint-driven-development` →
  `planning-and-task-breakdown` → `feature-journey-map` →
  `incremental-implementation` → `test-driven-development` →
  `code-review-and-quality` → `shipping-and-launch`
- Bug fix: `debugging-and-error-recovery` →
  `test-driven-development` (Prove-It) → `verified-change-loop` →
  `code-review-and-quality`
- Design: `visual-design` → `frontend-ui-engineering` →
  `accessibility-engineering` → `browser-testing-with-devtools`
- Review loop: `doubt-driven-development` (in-flight) →
  `code-review-and-quality` (pre-merge); reviewing a Skill instead →
  `skill-evaluation-gate`

## 6. Sources

- Vendor frontmatter + headings: hand-surveyed 2026-11-26 from
  `vendor/addy-agent-skills/skills/*/SKILL.md` (see
  `docs/skill-index.json` for the machine-readable extract).
- Discovery flowchart + lifecycle sequence:
  `vendor/addy-agent-skills/skills/using-agent-skills/SKILL.md`.
- Native skill triggers: `skills/*/SKILL.md` frontmatter.
- Format standard: `docs/skill-format.md`. Vendor evals:
  `evals/run_vendor_evals.py`.
