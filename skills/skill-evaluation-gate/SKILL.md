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

## Common Rationalizations

| Rationalization | Rebuttal |
| --- | --- |
| "It worked once in my session, so it is tested." | One pass is Candidate at best. Tested requires a real scenario replay with documented negative cases. |
| "The author reviewed it; that is independent enough." | The reviewer must be separate from the executor. The author's summary is not evidence. |
| "Formatting checks pass, so it is ready to install." | Static checks are the Candidate gate only. Never advertise a candidate as installed. |
| "No negative cases failed, so there are no negatives." | Negative and edge cases must be written and run, not assumed absent. |
| "It works on my machine; platform support is fine." | Approved/released requires a supported target platform and a rollback plan, not one local run. |
| "The scores look good; ship it." | Scores may only cover cases actually tested. A successful journey does not establish every quality property. |

## Red Flags

- A gate advanced without an evidence ledger, or with the executor acting as reviewer.
- "Tested" claimed from a single happy-path run with no negative cases.
- A skill described as installed or activated before explicit human approval.
- Failures fixed by changing several things at once, with no regression rerun.
- Post-release results never monitored; silent deactivation instead of retest or retirement.
- The evidence tool validates the ledger shape, but commands, screenshots and review were never checked by a real reviewer.
