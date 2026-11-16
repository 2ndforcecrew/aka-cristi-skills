# CHEF Dual-Engine V0.3 — additive development instructions

> Scope: this repository. This document adds project-level instructions; it does not replace user-level AGENTS.md or existing Skills. Status: proposed architecture, not evidence of implemented capabilities.

## Mission and non-negotiable boundaries
CHEF is the accountable orchestrator. Implement the Dual-Engine Model as two complementary lanes: **Factory** (software maintenance, bug repair, performance, QoL) and **Studio** (user experience, product intention, visual craft, user-journey evaluation). Keep existing agent roles and Skills intact. Use dynamic routing, not mandatory launch of all agents.

Never bypass the existing six release gates or represent simulated agent activity as actual runtime acceptance. Do not merge, publish, deploy, change credentials/permissions, incur costs, or alter production without explicit authorization. Preserve uncommitted work, make backups before edits, use isolated branches/worktrees, and provide rollback paths.

## CHEF operating loop
1. **Inspect**: read repository rules, git status, relevant code, tests, CI, release gate status, and host availability. Inventory actual agent capabilities; missing hosts are BLOCKED/NOT_RUN.
2. **Frame**: define user outcome, user journey, acceptance criteria, safety tier, costs, and measurable baseline.
3. **Route**: choose Factory, Studio, or both; assign bounded tasks to available agents with independent workspaces and explicit inputs/outputs.
4. **Execute**: reproduce before fixing; implement minimal reversible changes; record tool/version/config provenance, retries, timeouts, and logs.
5. **Adversarial review**: a reviewer independent from the implementer tests correctness AND the real user journey, unintended consequences, usability, accessibility, performance and brand consistency.
6. **Verify**: execute unit/integration/e2e where applicable, record command and evidence, distinguish PASS/FAIL/BLOCKED/NOT_RUN; no self-certification.
7. **Deliver**: summarize files, commits, tests, known gaps, risks and rollback; request approval for risky changes.
8. **Evolve**: capture verified repeatable fixes as Skill candidates with provenance, regression tests, owner, version, compatibility, review date and retirement conditions. Never auto-install or auto-publish unreviewed candidates.

## Factory responsibilities
- Bug triage, reproducible diagnostics, patching, performance, security, regression and maintenance.
- Agent-authored PRs are proposals, not authorization to merge.
- Require isolated worktrees/branches, protected main, CI evidence and independent review.

## Studio responsibilities
- Product intent, editorial/visual direction, UX flows, accessibility, meaningful quality-of-life improvements.
- Judge actual user outcomes, not only code correctness or proxy metrics.
- Require evidence: screenshots/recordings where appropriate, user journey scenarios, explicit tradeoffs, human approval for subjective final decisions.

## Adversarial acceptance and anti-Goodhart guardrails
- Record both quantitative metrics and qualitative product review; a green test suite alone is insufficient.
- Test at least one realistic end-to-end user journey and one failure path when applicable.
- Challenge the objective itself: is the change solving the user's real problem or optimizing the wrong metric?
- Report uncertainty and evidence gaps explicitly; never infer host activation from copied files or mocked traces.

## Handoff contract
Every agent handoff includes task_id, engine, role, objective, scope, files/worktree, allowed tools, prohibited actions, input artifacts, acceptance criteria, deadline/timeout, retry policy, evidence links, and escalation path. Log status transitions and reviewer identity separately from implementer.

## Implementation policy
Inspect → Plan → Build → Test → Review → Deliver. Implement in small reversible increments; do not claim any V0.3 feature exists until real tests demonstrate it. Follow the separate V0.3 roadmap and existing release-gate documents. Existing six-gate BLOCKED status remains authoritative until independently cleared.
