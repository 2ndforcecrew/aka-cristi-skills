---
name: skill-evaluation-gate
description: Evaluate a candidate Skill with a scenario rubric, independent evidence review and explicit autonomy gates before proposing installation or release.
---

# Skill Evaluation Gate

## When to use
A new or revised Skill has been written from successful task experience, or an installed Skill shows a regression, environment drift or duplicated behavior.

## Preconditions
- Candidate SKILL.md and immutable version/fingerprint.
- At least one real controlled test scenario with expected outcomes and negative/edge cases.
- Approved sandbox or test environment and a separately identified reviewer.
- Existing security, licensing, provenance and permission requirements.

## Procedure
1. **Define rubric**: record expected user behavior, platform support, setup cost, safety limits, error handling, rollback, performance and quality checks. Mark non-applicable checks explicitly.
2. **Prepare test**: use repeatable fixtures, record baseline version, scenario, available tools and permissions. Never assume installation equals activation.
3. **Execute**: run the candidate from its published instructions with minimal extra prompting; capture actual commands, outputs and artifacts.
4. **Review independently**: reviewer compares test results with rubric and evidence, not the executor's summary. Mark each item `PASS`, `FAIL` or `NOT RUN`.
5. **Revise**: if failures occur, change one method or constraint at a time, rerun the same scenario and regression cases; retain unsuccessful attempts in the evidence ledger.
6. **Gate autonomy**: progress from local proof to multiple reproducible passes to controlled scheduled use. Require explicit authorization before permission changes, external access, unattended runs, installation or publishing.
7. **Maintain**: monitor post-release results and propose retest/upgrade/retirement. Do not delete or silently deactivate Skills.

## Mandatory gates
- **Candidate**: formatting and static checks pass; never advertised as installed.
- **Tested**: real scenario has passing replay evidence and documented negatives.
- **Reviewed**: independent verifier and source evidence.
- **Approved / released**: explicit human approval, supported target platform and rollback plan.
- Scores may only cover cases actually tested; a successful journey does not establish every quality property.

## Evidence check
Run `python -m tools.skill_evidence --file evidence.json` to validate an evidence ledger's shape and reviewer separation. It cannot prove that commands, screenshots or review are genuine; those are external acceptance tasks.

## Provenance
Original AKA.CRISTI adaptation inspired by user-provided Lauren Tan/Grok Bot fieldnotes, 2026. Do not present it as an official third-party Skill or claim independent replay without execution logs.
