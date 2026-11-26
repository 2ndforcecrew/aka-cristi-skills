<!--
  This document is for people evaluating this repository. It is NOT a skill
  and is not meant to be loaded into an agent's working set. It lives in
  docs/ so it stays out of the agent's working set.
-->

# How aka-cristi-skills compares

People often ask how **aka-cristi-skills** relates to
**[agent-skills](https://github.com/addyosmani/agent-skills)** (Addy Osmani).
They share DNA — both are Markdown skills for coding agents, both care about
verification, and this repo has borrowed four mechanisms from that one (see
[What we borrowed](#what-we-borrowed-from-agent-skills)). But they are built
for different jobs, and this page is an honest map of where they overlap,
where they diverge, and where this repo is simply behind.

> **TL;DR** — agent-skills is a general, production-grade engineering
> methodology: 26 skills covering the whole software lifecycle from spec to
> ship, used by a large community. aka-cristi-skills is a personal brand
> workbench: a conductor (CHEF) plus a small set of skills, a real CLI and
> MCP server, and a visual-design practice with 58 catalogued design cases.
> If you want a team-wide engineering process, pick agent-skills. If you want
> one person's design-led workflow as installable tooling, this repo is the
> shape of that — and it is much smaller, much newer, and much less proven.

> **Update — vendored import (PR #66, Draft, 2026-11-26):** this repo now
> vendors the full agent-skills tree under `vendor/addy-agent-skills/`
> (273 files + 1 symlink from upstream e997ac5, 280 entries; 6 files
> excluded). 25 of its 26 skills install through the same installer as the
> 6 native skills (vendored `interview-me` stays reference-only; the native
> one wins). The coverage gaps named below — no spec, TDD, code-review or
> ship skill — are now closed by the vendored set *at file level*: the
> vendored skills are imports, not native skills. They are exempt from this
> repo's literal section-title gate, their evals are separate, and no live
> host has loaded them yet. Full status:
> `vendor/addy-agent-skills/IMPORT_STATUS.md`.

---

## At a glance

| | **aka-cristi-skills** (this repo) | **agent-skills** |
|---|---|---|
| **Core idea** | One person's design-led workflow, packaged as installable tooling | The full senior-engineering lifecycle, packaged as skills |
| **Organizing principle** | A conductor (**CHEF**) routes work to 4 roles across Factory (maintenance) and Studio (experience/craft) lanes | SDLC **phases** (Define to Ship) behind a meta-skill router |
| **Author** | AKA.CRISTI (personal repo) | Addy Osmani (Google Chrome team), with collaborators |
| **Adoption** | 0 stars / 0 forks (public repo, checked 2026-11-26) | 120,411 stars / 12,524 forks (checked 2026-11-26) |
| **Version** | 0.1.0 (`aka_skills.__version__`) | 0.6.18 (`plugin.json`) |
| **License** | No LICENSE file in the repo | MIT |
| **Skills** | 31 installable (6 native + 25 vendored; vendored `interview-me` reference-only) | 26 (25 lifecycle + 1 meta router) |
| **Roles / personas** | 4 agent roles (`coding`, `qa`, `research`, `automation`) | 5 review personas (code, test, security, webperf, a11y) |
| **Entry points** | `aka-skills` CLI (6 commands) + MCP server (7 tools) | 10 slash commands (`/spec` `/plan` `/build` `/test` `/review` `/ship` …) |
| **Reference material** | 12 global rules, 22 shared-training sections, 58 design cases | 7 reference checklists |
| **Verification** | 392 unit tests (see below); native evals + separate vendor evals | 3-tier eval framework in CI (structure, routing, behaviour) |
| **Install** | `aka-skills install` / one-command `full_setup`, 7 hosts | `npx skills add`, 70+ agents |
| **Field validation** | Visual Design Skill V0.1 self-declares NOT FIELD-VALIDATED | Every skill ships with an eval |

---

## Positioning

agent-skills answers the question "how should a team ship software with AI
agents?" Its unit of work is a feature travelling through phases, with a
human checkpoint at each phase. The repo is written to be adopted by
strangers: anyone can install it, and the skills assume no shared history
with the reader.

aka-cristi-skills answers a narrower question: "how does one designer /
creative technologist turn successful collaborations with AI into repeatable,
installable capability?" Its unit of work is a brief handed to CHEF, the
conductor, which routes it to a role and a skill. The repo assumes a single
owner's taste: the visual direction, the global rules, and the shared
training are written in that owner's voice, for that owner's work. That is a
feature for its owner and a limitation for everyone else — a team adopting
this repo would have to rewrite the taste layer before the process layer
made sense.

Neither positioning is "best" in the abstract. The honest difference is
breadth versus identity: agent-skills is broad and impersonal on purpose;
this repo is narrow and personal on purpose.

## Skill coverage

agent-skills covers the lifecycle end to end: idea refinement and
requirements interviews, spec writing, planning, incremental implementation,
TDD, debugging, API and UI design, security, performance, accessibility,
CI/CD, observability, deprecation, ADRs, and launch. If a phase exists, a
skill owns it.

This repo covers orchestration and design, and almost nothing else:

| Area | aka-cristi-skills | agent-skills |
|---|---|---|
| Orchestration / routing | `chef-orchestrator` (CHEF Dual-Engine) | `using-agent-skills` meta-skill |
| Requirements | `interview-me` (added in this PR) | `interview-me`, `idea-refine` |
| Planning | `feature-journey-map` (journey-first, Studio lane) | `planning-and-task-breakdown`, `spec-driven-development` |
| Building | — (no build skill; CHEF delegates to host agents) | `incremental-implementation`, `test-driven-development`, `context-engineering`, `frontend-ui-engineering`, `api-and-interface-design` |
| Verification | `verified-change-loop` (prove it, then close) | `browser-testing-with-devtools`, `debugging-and-error-recovery` |
| Review | `skill-evaluation-gate` (evaluates Skills, not code) | `code-review-and-quality`, plus 5 review personas |
| Shipping | — (no ship skill) | `shipping-and-launch`, `git-workflow-and-versioning`, `ci-cd-and-automation` |
| Visual design | `visual-design` + 58 design cases | — (no design content at all) |
| Skill quality | `skill-evaluation-gate` | Eval framework + `skill-anatomy.md` format spec |

The gap is deliberate but real: this repo has no spec skill, no TDD skill, no
code-review skill, and no ship skill. Work in those phases is delegated to
the host agent's own habits, which means the quality of a build depends on
the host, not on this repo. That is the single largest coverage difference,
and the reason this repo should not be presented as a general engineering
methodology.

## Tooling: a CLI and an MCP server, not just Markdown

This is the one dimension where this repo goes further than agent-skills.

agent-skills is Markdown plus a small amount of shell: hooks and validation
scripts. Its "installation" is copying skill files into the host's native
skill directory, or registering a marketplace plugin.

aka-cristi-skills ships executable tooling around the same Markdown:

- **`aka-skills` CLI (6 commands, verified in `aka_skills/cli.py`):**
  `install`, `verify`, `status`, `list-skills`, `validate`, `serve`.
  Install defaults to a zero-write preview; writing requires an explicit
  confirmation, and conflicts abort instead of overwriting.
- **MCP server (7 tools, verified in `aka_skills/mcp_server.py`):**
  `list_skills`, `read_skill`, `list_design_cases`, `read_design_case`,
  `install_preview` (dry-run only), `validate_skill`, `check_status`.
  Any MCP client can list and read skills without touching the filesystem.
- **Multi-host installer** (`tools/universal_chef.py`, 7 hosts: `codex`,
  `workbuddy`, `claude`, `gemini`, `opencode`, `hermes`, `generic`) plus a
  one-command `full_setup` installer.

The trade-off is maintenance surface: a CLI and an MCP server are code, and
code needs tests, dependency pins (`mcp==1.13.0` with a narrow pydantic
range), and per-platform verification. Markdown does not. This repo pays
that cost because its goal is a tool, not just a document set — but the
cost is real, and it is why the test suite below exists at all.

## Verification

Both repos treat verification as non-negotiable, but they verify different
things.

agent-skills runs a three-tier eval framework in CI: structural checks on
the catalog, routing checks (does each skill's description carry the words
users actually say, and do two skills collide on routing?), and behavioural
grading of real agent execution traces. A routing regression fails CI
instead of surfacing later as "why didn't the skill fire".

This repo verifies the tooling with unit tests and the skills with
field tests:

- **Unit tests: 392 tests in `tests/`** (38 test files), run on this
  branch: 361 passed, 31 skipped, 0 failed. They cover the
  installer, the CLI, the MCP server, and filesystem safety. Landing
  the new skill (`interview-me`) meant updating two list-skills tests
  whose expectations were hard-coded to five skills; the update is
  part of this PR, and the suite is green on the branch.
- **Field validation: incomplete.** Visual Design Skill V0.1 self-declares
  NOT FIELD-VALIDATED. One of three field-test briefs (poster) is done;
  website and brand-system briefs are not.
- **Evals framework: new in this PR** (see below). It starts with
  structural checks and routing cases — deliberately smaller than
  agent-skills' three tiers. There is no behavioural tier yet. Routing
  cases now total 44 (18 native + 26 vendor, the vendor set in
  `evals/vendor-routing-cases.json`); vendored skills are checked by a
  separate vendor evals runner, not by the native literal-title gate.

The honest summary: this repo proves its installer works; agent-skills
proves its skills trigger correctly. Those are different claims, and this
repo's claim is the narrower one.

## How skills are written

agent-skills skills share one anatomy: Overview, When to Use, Process,
Common Rationalizations, Red Flags, Verification. Two elements of that
anatomy are the reason this repo borrowed it:

- **Common Rationalizations** — a table of the excuses an agent uses to
  skip a step ("I'll add tests later"), each with a documented rebuttal.
  It is a discipline mechanism, not decoration.
- **Red Flags** — signs something is going wrong, written so the agent can
  notice its own drift.

This repo's skills were shorter and looser: a `When to use` section, a
process, and preconditions, with no standard anti-rationalization section
and no red flags. This PR adds both to all six skills (see below). What this
repo keeps that agent-skills does not have is the CHEF framing: every skill
names its lane (Factory or Studio) and its handoff contract, because the
skills here are written to be routed by a conductor, not picked by the
model alone.

## Installation and host coverage

| | aka-cristi-skills | agent-skills |
|---|---|---|
| Install command | `aka-skills install` / `python3 -m tools.full_setup --interactive` | `npx skills add addyosmani/agent-skills` |
| Hosts | 7 in the installer (`codex`, `workbuddy`, `claude`, `gemini`, `opencode`, `hermes`, `generic`) | 70+ agents via the `skills` CLI; native adapters for Claude Code, Codex, Cursor, Gemini CLI, Copilot, Kiro, OpenCode, Windsurf, Antigravity, Command Code |
| Per-host setup docs | One README section + `HOST_CAPABILITY_MATRIX.md` | One setup doc per host under `docs/` |
| Install safety | Preview-only by default; explicit confirmation to write; conflicts abort | Copies Markdown files; no installer of its own |

agent-skills wins on breadth of hosts and on documentation per host. This
repo wins on install safety (preview-first) and on having one installer to
maintain instead of ten adapter directories — at the cost of covering fewer
hosts, and with several hosts (notably the four CHEF roles) still unverified
as actually activating on the target machine.

---

## What we borrowed from agent-skills

Four mechanisms in this PR come directly from agent-skills. Each is
credited here rather than silently absorbed.

### 1. Anti-rationalization tables + Red Flags

**Source:** every skill in agent-skills carries a Common Rationalizations
table and a Red Flags section, as specified in its `docs/skill-anatomy.md`.

**What changed here:** all six skills in this repo now carry an
Anti-rationalization table (the excuse and its rebuttal) and a Red Flags section (observable signs the skill is being
skipped or misapplied). The content is ours — the excuses are the ones this
repo's agents actually make (skipping verification, silently filling in
ambiguous requirements, treating a copied file as a successful install) —
but the mechanism is theirs.

### 2. `interview-me`

**Source:** agent-skills' `interview-me` skill: a one-question-at-a-time
interview that extracts what the user actually wants instead of what they
think they should want, until about 95% confidence.

**What changed here:** a new sixth skill, `skills/interview-me/`,
following the same interview shape (hypothesize with a confidence number,
ask one question at a time, stop test at ~95%) but adapted to this repo:
it runs in the Studio lane, produces a confirmed brief rather than a
build, and is explicitly forbidden in non-interactive contexts (CI,
scheduled runs, autonomous loops), where an underspecified ask must be
recorded as a blocker instead of guessed at. It fills the clearest gap in
this repo — CHEF used to route ambiguous briefs straight into work.

### 3. Evals framework

**Source:** agent-skills' three-tier eval framework (structure, routing,
behaviour), run in CI.

**What changed here:** this PR adds a first evals framework to this repo:
structural checks on the skill catalog plus routing cases that assert a
given ask routes to the intended skill. It is deliberately smaller than
the source: two tiers, not three. There is no behavioural tier (grading
real execution traces) yet, and the framework is new — treat it as a
starting point, not as the coverage agent-skills has.

### 4. This comparison document

**Source:** agent-skills' own `docs/comparison.md`, which compares itself
honestly against Superpowers and Matt Pocock's skills, including its own
weaknesses, and says plainly where each alternative is the better pick.

**What changed here:** this file. Same intent — an honest comparison that
does not hide where this repo is behind — applied to the other direction:
a small personal repo measuring itself against the large general one it
borrowed from.

---

## What only we have

Three things in this repo have no counterpart in agent-skills:

- **Visual design as a first-class skill.** `visual-design` plus 58
  catalogued design cases (6 style batches: glassmorphism, flat
  information graphics, giant-type posters, experimental posters,
  colorful commercial posters, giant-type web design; plus a beauty-class
  case study), each with a frontmatter technique taxonomy. agent-skills
  has no design content at all — its closest skill,
  `frontend-ui-engineering`, is about component architecture and
  accessibility, not visual direction.
- **A real CLI and MCP server** (see [Tooling](#tooling-a-cli-and-an-mcp-server-not-just-markdown)).
  agent-skills is consumed as files; this repo is also consumed as a tool.
- **`skill-evaluation-gate`.** A skill whose job is evaluating other
  skills — scenario rubric, independent evidence review, explicit
  autonomy gates before a candidate skill is installed or released.
  agent-skills evaluates its catalog with an eval framework; this repo
  additionally gates each individual skill as a candidate, with provenance
  and retirement conditions.

---

## Honest weaknesses

In the order that matters:

1. **No community.** 0 stars, 0 forks, no external contributors, no
   issue history. Every claim in this repo is self-assessed except where
   an independent verifier ran the tests. agent-skills has 120,000+
   stars and community review; a flaw in its skills gets found by
   strangers. A flaw in ours gets found by us, or not at all.
2. **Skill count: 6 vs 26 (native only).** Even after this PR, this repo covers
   orchestration and design, not engineering. There is no spec skill, no
   TDD skill, no code-review skill, no ship skill. Do not present this
   repo as a software methodology; it is not one. (PR #66 vendors the
   upstream 26 as files, which closes the coverage gap at file level —
   see the update at the top — but the vendored skills are imports, not
   native skills, and no live host has loaded them.)
3. **Visual Design is not field-validated.** V0.1 self-declares
   NOT FIELD-VALIDATED; field validation is one of three briefs done.
   The design cases are catalogued, not proven to make the skill produce
   better work.
4. **Evals are just starting.** Two tiers, new in this PR, no behavioural
   tier, no CI history. agent-skills' evals have been failing CI on real
   regressions; ours have not yet caught anything.
5. **No LICENSE file.** The repo is public with no license, which means
   the default is "all rights reserved" in most jurisdictions — the
   opposite of agent-skills' MIT. Anyone reusing this repo's content
   should know that, and it should be fixed with an explicit license
   decision, not assumed.
6. **Skill count is hard-coded in three places.** Adding a skill
   requires updating the expected-skill list in `tests/test_cli.py`,
   `tests/test_mcp_server.py`, and `evals/run_evals.py`
   (`EXPECTED_FINAL_SKILLS`); miss one and the suite goes red. That
   coupling is the price of the evals gate catching a silently lost
   skill, but it is a maintenance trap worth knowing about.

## When to pick which

- **Ship a feature front to back with a team, with a checkpoint at each
  phase?** agent-skills. It is the only one of the two that carries you
  from spec through security, performance, and launch.
- **Work the way AKA.CRISTI works — design-led, conductor-routed, with
  installable tooling and a visual-design practice?** This repo, with
  eyes open about the weaknesses above.
- **Need requirements pinned down before anything is built?** Either
  repo's `interview-me`; this repo's version is the newer, less proven
  one.
- **Want the skills themselves measured?** agent-skills today. This
  repo's evals are a first step, not yet a track record.
- **Want design cases and visual direction?** Only this repo has them.

You do not have to choose exclusively: skills are Markdown, and
cherry-picking individual skills works. What does not work is running two
routers at once — two meta-skills competing over routing and command names
produces unpredictable behaviour. Pick one framework as the primary router
and borrow from the other à la carte.

---

## A note on Superpowers and Matt Pocock's skills

agent-skills' own comparison describes two other collections worth knowing
about, and this paragraph only restates its account of them: **Superpowers**
is a complete development methodology built for autonomous, reasoning-heavy
runs, with a strict pipeline, subagent-driven execution, and worktree
isolation; **Matt Pocock's skills** are a sharp, opinionated Claude Code
toolkit distilled from one expert's daily workflow, centred on a "grill me"
interrogation loop. Neither is assessed first-hand here. The point of
repeating the summary is that the landscape has more than two shapes: a
lifecycle (agent-skills), an autonomous pipeline (Superpowers), a personal
toolkit (Pocock), and a personal workbench (this repo). The right pick
depends on the work in front of you, not on star counts.

---

## Sources and how the numbers were checked

- **agent-skills figures** (26 skills, 10 commands, 5 personas, 7
  checklists, 26 eval cases, v0.6.18) were counted from a local clone of
  <https://github.com/addyosmani/agent-skills> on 2026-11-26. Star/fork
  counts were read from GitHub the same day; they move daily.
- **aka-cristi-skills figures** were counted from this repo at `main`
  (84c2be0) plus this PR: 6 skills (`skills/`), 4 roles (`agents/*.toml`),
  12 global rules (numbered sections 01–12 in
  `shared-training/rules/GLOBAL_WORK_RULES.md`), 22 training sections
  (`##` headings in `shared-training/rules/TRAINING.md`), 58 design
  images (rows in the six `skills/visual-design/references/styles/*.md`
  tables: 8 + 14 + 9 + 10 + 8 + 9), 6 CLI commands
  (`aka_skills/cli.py`), 7 MCP tools (`aka_skills/mcp_server.py`), 392
  unit tests run with `python3 -m unittest discover -s tests` (361
  passed, 31 skipped, 0 failed on this branch).
- **Borrowing sources:** agent-skills `docs/skill-anatomy.md` and
  `docs/comparison.md` (anti-rationalization tables, Red Flags, and the
  comparison-document pattern), `skills/interview-me/SKILL.md` (the
  interview shape and ~95% stop test), and its eval framework as
  described in `docs/comparison.md` and `evals/`.
- Star counts are a popularity signal, not a quality signal. They are
  included here because the adoption gap is honest context, not because
  more stars means a better fit for a given job.
