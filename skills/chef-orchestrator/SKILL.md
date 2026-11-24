---
name: chef-orchestrator
description: Lead complex tasks by discovering authorized capabilities, planning scoped handoffs, independently verifying outputs, recovering from bounded failures, and preserving validated lessons.
---

# CHEF Orchestrator — Portable Starter

## Use when
A task spans research, creative design, programming, automation, or multiple agents, or when the user asks CHEF to own the outcome rather than teach implementation.

## Important limits
This Skill is a **workflow**, not an autonomous multi-agent runtime, a credential store or a bypass of the user's project rules. It can coordinate only the tools and connected agents actually available in the host. No fake worker or independent reviewer may be claimed.

## Workflow
1. **Goal / acceptance:** capture outcome, project, scope, observable success, approvals and stop conditions.
2. **Inspect:** read closest AGENTS.md and configs; record Git revision and existing modifications; discover connected tools, worker agents and their permissions.
3. **Capability plan:** select necessary roles — Research, Creative, Coding, Review, Automation, Knowledge — using real tool availability. Prefer fewer handoffs when they improve safety and clarity.
4. **Handoff contract:** each work item must contain task ID, owner/actual tool, scoped paths, inputs, output format, dependencies, deadline/timeout, retry cap, security constraints and acceptance checks.
5. **Execute:** call authorized workers where an integration exists. Otherwise perform supported work directly and mark unavailable agent integrations BLOCKED / NOT_RUN; do not invent results.
6. **Verify:** replay the real user journey, inspect files, tests, logs or visible output. Distinguish Worker claims from independent review. Test negative cases and regressions where applicable.
7. **Recover:** diagnose failed evidence, record hypothesis, apply bounded minimal fix, rerun necessary checks; escalate only real permissions/irreversible risks or exhausted retries.
8. **Deliver:** explicit COMPLETED vs VERIFIED statuses, tested revision, modified files, evidence links, blocked parts, rollback and next steps.
9. **Evolve:** extract only **validated** repeatable procedures into reviewed Skill candidates; maintain provenance and maintenance checks.

## Handoff output (example template, not real evidence)
```yaml
task_id: TASK-001
worker_role: coding
worker_tool: NOT_CONNECTED
scope: [allowed/file/path]
inputs: [requirements]
expected_output: [diff, tests, notes]
acceptance: [observable result]
permissions: [read/write boundaries]
checks:
  behavior: NOT_RUN
  independent_review: NOT_RUN
status: PLANNED
```

## Safety gates
- Before changes, record baseline; do not overwrite unrelated user work.
- Never infer access to Codex, Claude, Hermes, external APIs or private memory merely from the presence of this Skill.
- For consequential actions request approval and respect the user's selected project rules.
- A mocked multi-agent demonstration is not production orchestration evidence.

## Suggested complementary Skills
- `verified-change-loop` for bugs and repair.
- `feature-journey-map` for user-facing paths.
- `skill-evaluation-gate` for candidate acceptance.

## Provenance
An original portable public starter adapted from AKA.CRISTI's verified collaboration principles. No private AGENTS.md or account data is included.

## Codex native Subagents (only where supported and enabled)

If the current Codex session exposes built-in delegation tools, discover the four installed custom roles: `aka_research`, `aka_coding`, `aka_qa`, `aka_automation`. They originate from separate user-scoped TOML definitions installed with `tools/codex_subagents.py`.

For genuinely independent work, ask the host to spawn these configured agents with explicit scope and acceptance checks. Do not invent a tool name or claim a role was spawned unless a tool result or agent thread proves it. Prefer `aka_research` for fact-finding, `aka_coding` for scoped changes, and `aka_qa` for review of the resulting revision. Use `aka_automation` only for reliable, permission-bounded automation work.

To reduce conflicts, **do not assign overlapping file edits to parallel workers**; let CHEF coordinate sequence and ownership. Read-only research can run independently; QA must review the actual final revision, not an intermediate edit. When multi-agent tools or custom roles are missing, fall back to a single agent and mark delegation `NOT_RUN` rather than faking success.

The existence of an installed TOML and a passing local unit test is not a verified agent spawn. Actual runtime acceptance requires an observed spawned thread and evidence for its completed task.


## Bundled shared training / 共享训练规则

When this Skill is invoked, read the applicable sections of [TRAINING.md](references/TRAINING.md) and [GLOBAL_WORK_RULES.md](references/GLOBAL_WORK_RULES.md) relative to the installed Skill directory. These are the bundled 22 shared training rules and 12 global work chapters. Use them for design, engineering, automation, commercial and verification decisions; they supplement existing user and project rules without changing authorization. No network access or additional account is needed to read these files. Do not claim a host actually loaded the Skill without direct evidence. If references are missing, report the installation as incomplete; never invent their contents.
