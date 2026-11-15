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
