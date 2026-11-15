---
name: verified-change-loop
description: Reproduce defects, inspect evidence, apply a minimal reversible patch, replay the same user scenario, and compare outcomes before handing off a change.
---

# Verified Change Loop

## When to use
A user reports a defect, a CI failure, a broken workflow, or requests a code change whose outcome must be independently verified. This Skill is a repeatable verification method, **not** permission to modify production or publish changes.

## Inputs and prerequisites
- Authorized repository or project; working tree status and current revision recorded.
- Clear user-facing target outcome, a reproducible baseline and a comparable post-change scenario.
- Commands permitted by the project owner and a safe rollback route.
- An independent reviewer or, if unavailable, a clear **NOT RUN** review status.

## Procedure
1. **Scope**: inspect instructions and current configuration; record baseline revision, allowed files, safety boundaries, required approvals and stop conditions.
2. **Reproduce**: follow the real user journey; record steps, starting state, inputs, observed output, exact errors, environment and artifacts. If the failure cannot be reproduced, record uncertainty instead of guessing.
3. **Inspect**: compare logs, code, dependency versions and visible UI behavior; form a specific root-cause hypothesis.
4. **Patch**: apply the smallest cohesive reversible change using existing repository patterns. Do not replace unrelated code or data.
5. **Replay**: rerun the **same** scenario with equivalent inputs and record outputs, screenshots or traces; execute relevant unit, lint, type, security and performance checks as applicable.
6. **Compare**: evaluate before/after evidence and regressions, distinguish *behavior*, *performance* and *quality*; do not claim one passing dimension proves the others.
7. **Repair loop**: on failure, inspect the new evidence, modify the hypothesis, make one targeted fix and repeat within a bounded retry budget.
8. **Handoff**: report revision, changed paths, evidence references, individual checks as `PASS`, `FAIL` or `NOT RUN`, limitations, rollback and next steps; obtain review from someone other than the executor before `verified` status.

## Stop conditions
- Missing permission or necessary evidence; irreversible or production changes not explicitly approved.
- Same failure persists without a new hypothesis; unsafe scope growth; retry budget exhausted.
- Independent review or user-visible verification unavailable: mark `NOT RUN`, never `PASS`.

## Evidence contract
Use `evidence.json` with the schema specified in this repository's `tools/skill_evidence.py`. Run:
```bash
python -m tools.skill_evidence --file evidence.json
```
This command validates structure and reviewer separation; it **does not** execute or attest the described tests. Source links and artifacts must be checked by a real reviewer.

## Provenance and reuse
Adapted into an original AKA.CRISTI workflow from the user-supplied Lauren Tan/Grok Bot verification-engineering reference (November 2026). Attribution is for methodological inspiration; this is not Lauren Tan's official Skill. Use on supported, authorized projects; retain local policies and human approvals.
