---
name: dual-engine-routing
description: Route CHEF tasks through Factory engineering and Studio experience gates with explicit evidence, permissions, and independent review. Use when a change needs both engineering correctness and product judgment.
---

# CHEF Dual-Engine Routing

## Overview

Coordinate two complementary engines without confusing code correctness with product fitness. This Skill is a workflow, **not** a claim that independent agents or runtime integrations are available.

## When to Use

Use when a task needs both engineering correctness and product fitness — for example a product-facing code change where a Factory pass alone does not prove the user outcome. Use when Factory and Studio judgment could conflict, or when a change needs independent review before it ships. Do not use as a substitute for real delegation: this Skill routes work, it does not spawn agents.

## Process

1. Inspect repository instructions, git revision, worktree, current skills, tools and authorization before editing.
2. Capture objective, user journey, product intent, scope, risk, stop conditions and evidence requirements.
3. Choose `factory` for engineering repair/performance/maintenance, `studio` for UX/visual/product judgment, or `both` for product-facing code changes.
4. Assign actual available tools and owners. Never fabricate delegation, screenshots or independent reviews.
5. Require Factory to reproduce, execute, measure and retest using `verified-change-loop`.
6. Require Studio to compare observable behavior with user intent, accessibility, design consistency and real user paths using `feature-journey-map`.
7. Mark each gate `PASS`, `FAIL`, `BLOCKED` or `NOT_RUN`; a Factory pass does not imply a Studio pass.
8. Obtain independent acceptance where required; default to draft PR and human approval. No autonomous production deployment or high-risk merges.
9. Record versioned evidence and lessons; only promote independently validated repeated workflows into reviewed Skill candidates.

## Dual-engine handoff

Use the JSON contract in `docs/DUAL_ENGINE_CONTRACT.md`. Never include secrets, private rules or personal data in a public artifact.

## Common Rationalizations

| Rationalization | Rebuttal |
| --- | --- |
| "Factory passed, so the product is fine." | A Factory pass does not imply a Studio pass. Mark each gate separately. |
| "We can skip independent review this once." | Independent acceptance is the default. A skipped review is NOT_RUN, never PASS. |
| "I will just simulate the handoff to move faster." | Never fabricate delegation, screenshots or independent reviews. Mark NOT_RUN honestly. |
| "Routing is overhead for a small change." | Small changes fail silently instead of cheaply. Route, or record why routing was skipped. |
| "The roles are installed, so delegation worked." | Installed files are not spawned agents. Only an observed thread with evidence counts. |

## Red Flags

- Work starts without inspecting repository instructions, revision, worktree or authorization.
- A Factory pass is reported as if it proved the product outcome.
- Delegation, screenshots or reviews are claimed without an observed thread or evidence.
- Missing permissions, exhausted retries, unverified evidence, product-intent conflict, or irreversible changes are pushed through instead of stopping.
- Branch protection is bypassed, or a production deployment happens without human approval.

## Verification

- [ ] Objective, user journey, product intent, scope, risk, stop conditions and evidence requirements were captured before editing.
- [ ] Engine choice (`factory` / `studio` / `both`) is recorded with its reason.
- [ ] Every gate is marked `PASS`, `FAIL`, `BLOCKED` or `NOT_RUN`; Factory and Studio gates are marked separately.
- [ ] Independent acceptance is recorded where required; otherwise the change stays a draft PR awaiting human approval.
- [ ] Evidence is versioned and linked; no fabricated delegation, screenshots or reviews appear in the record.
- [ ] Rollback path is preserved: baseline intact, changes reversible.

## Provenance

Original AKA.CRISTI adaptation of the user-supplied 11-page *The Dual-Engine Model* (Factory / Studio concept). Implementation rules and safety gates are AKA.CRISTI engineering decisions, not direct quotations.
