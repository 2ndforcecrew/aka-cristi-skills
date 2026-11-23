# CHEF Platform — Seven-Track Delivery Plan (2026-11-23)

Status: **implementation program authorized; NOT delivered**. Preserve main, original rules, prior releases and six release gates. Work on isolated branches/PRs. No automatic merge, paid-model invocation, private-data transmission or production deployment.

## Verified baseline
- Public `v1.0.0-beta.3` is documented in README; four Skills, CHEF rule installation, four Codex role configurations and multi-host configuration installers exist.
- `tools.chef_dual_engine` is experimental: local Git snapshots, SQLite events/tasks, explicit resume and independent QA handoff. Real authorized Factory→Studio→QA completion is still unverified.
- Personal Workspace has mock-based OAuth/sync tests but lacks independent real OAuth/private-repo UAT.
- Existing [#44](https://github.com/2ndforcecrew/aka-cristi-skills/issues/44) covers live multi-host dispatch. [#31](https://github.com/2ndforcecrew/aka-cristi-skills/issues/31) tracks unresolved security triage. Do not duplicate or waive either.

## Delivery tracks
| Track | Priority | First increment | Acceptance gate |
| --- | --- | --- | --- |
| 1. CHEF Control Center | P0 | Local-only read-only task/event API and simple dashboard | Reads real SQLite data, does not fabricate running states; API integration tests |
| 2. Universal Agent Runtime | P0 | Typed host capabilities, explicit auth probes, redacted event contract | One non-Codex real authorized E2E, no silent tool/credential inheritance |
| 3. Studio Visual Intelligence | P1 | Screenshot review, responsive comparison and visual evidence manifest | Repeatable visual QA on a representative site; accessibility and reduced-motion |
| 4. Skill Evolution | P1 | Candidate capture from verified outcomes; approval gate | Candidate reproducibility, security checks and independent evaluation |
| 5. Personal Workspace 2.0 | P1 | Real Device Flow/keyring/private-repo UAT, conflict preview | Windows/macOS/Linux consented acceptance; no default push |
| 6. Self-Healing and QA | P1 | Bounded failure classification and recovery playbooks | Negative tests for loops, timeouts, child cleanup and escalation |
| 7. One-Click Setup | P2 | Host/dependency detection and safe install preview | Fresh standard-user install, rollback, second launch and external UAT |

## Sequence and dependencies
1. **Foundation and truthfulness:** reconcile README/FEATURE_CATALOG versions, inspect open PRs and release gates, define task/event evidence schema and read-only API. Do not claim live completion.
2. **Runtime:** prove authorized Codex Factory→Studio→independent QA on a clean sample repository. Keep #44 cross-vendor work separate until real host evidence exists.
3. **Control Center:** build local UI using real task/events/attempts; statuses `NOT_RUN`, `BLOCKED`, `FAILED`, `REVIEW_REQUIRED`, `PASS` must be grounded in stored evidence, not inferred from process launch.
4. **Studio + self-healing:** implement visual comparisons and bounded recovery only after runtime/evidence contracts stabilize.
5. **Skill Evolution + Workspace:** candidates remain drafts pending review; real OAuth and syncing require user consent.
6. **Productization:** GUI onboarding, three-OS external UAT, independent security review and signed release decisions.

## Safety and product contracts
- Local-only service by default, read-only SQLite access, no raw prompt/transcript/credential exposure; redact potentially sensitive event payloads.
- Do not automatically install, start, run paid agents, sync, merge, publish, or modify account permissions.
- Retain immutable source snapshots and evidence; do not mutate source checkout from a read-only dashboard.
- Add tests and review for each incremental PR; green CI does not substitute for live model or external UAT.
- Update project growth journal and feature matrix after verified merges only.

## Definition of done
Every track requires code, repeatable tests, security/permission checks, exact files changed, versioned evidence, and an explicit `PASS/FAIL/INCONCLUSIVE/NOT_RUN` report. Stable release additionally requires outstanding independent security/release gates to be resolved with reviewer sign-off.
