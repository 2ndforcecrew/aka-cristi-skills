# CHEF Dual-Engine V0.3 — development roadmap

**Source:** user-provided 11-slide presentation *The Dual-Engine Model* (2026-11-16). Its themes: agent-as-team-member, autonomous PR proposals, experience-driven self-correction, adversarial review/Goodhart risk, Factory + Studio. The following engineering design extends those ideas and is not claimed as a verbatim specification.

**Baseline:** Existing public repository includes CHEF Orchestrator, Verified Change Loop, Feature Journey Map, Skill Evaluation Gate, Codex agent configuration and verification scripts. The six release gates remain BLOCKED; see `docs/SIX_GATE_STATUS.md`. Do not treat a roadmap or PR merge as runtime acceptance.

## Phases and acceptance criteria

### P0 — Baseline, backups, and unblock genuine evidence
- Inventory main, open PRs, existing rules, git status, CI, six gates, test harnesses, actual supported hosts.
- Preserve old versions, produce reproducible baseline reports and rollback instructions.
- For each gate, identify missing evidence and a real, authorized remediation; no changing a threshold just to show PASS.
- **Done when:** baseline is documented, regression tests run, and every gate has an evidence-backed state (PASS/FAIL/BLOCKED/NOT_RUN). Gate clearance is separate from V0.3 work.

### P1 — CHEF routing and agent handoff schema
- Define Factory / Studio / hybrid routing, role registry and capability discovery; do not hard-code specific vendor hosts.
- Implement durable task IDs, isolated workspaces, structured handoffs, audit log, bounded retries/timeouts, resumable states.
- **Done when:** tests show correct routing, failure recovery, no unauthorized tools, and no conflicting file writes.

### P2 — Factory execution and independent validation
- Build reproduce → patch → test → review → PR candidate workflow.
- Run real independent review, CI, regression, performance and security checks where applicable.
- **Done when:** actual PR candidate and reviewer evidence exist; mock traces are clearly labeled and do not satisfy live-agent acceptance.

### P3 — Studio experience review
- Define brief, user journey, visual direction, accessibility and product-intent criteria.
- Add real journey review and independent adversarial critic, with human sign-off for subjective/high-impact changes.
- **Done when:** a real representative project has recorded UX review, screenshots or equivalent evidence, findings and re-test.

### P4 — Self-correction and Skill Evolution
- Capture trigger → reproduce → execute → measure → rewrite loop, deduplicate fixes and detect repeated success.
- Promote only independently verified candidates; track version, owner, compatibility, provenance, regression, expiration/retirement.
- **Done when:** repeated real failure is resolved with replayable evidence, candidate passes separate evaluation, and rollback is tested.

### P5 — Cross-host verification and productization
- Evaluate Codex, Hermes, Claude, ChatGPT and others only where host integrations are actually authorized and supported.
- Prove real activation and actual child-agent runs per host; mark unsupported paths BLOCKED, not PASS.
- Add GUI/CLI visibility for tasks, evidence, gates, Factory/Studio status; protect personal/private data.
- **Done when:** documented external UAT and host-specific live evidence pass; package security/signing requirements remain enforced.

## Safety / merge policy
- Low-risk changes: agent may prepare PR; merge only if existing policy explicitly authorizes and independent checks pass.
- Medium/high-risk, security, publishing, paid API, production, permissions, user data: explicit human approval.
- Never auto-merge solely because an agent or test suite says PASS.
- Track task states: PLANNED, IN_PROGRESS, BLOCKED, NOT_RUN, FAILED, VERIFIED. Do not conflate PLANNED with shipped.

## First implementation backlog
1. Record baseline and six-gate remediation matrix.
2. Define versioned routing and handoff JSON Schema.
3. Add isolated task runner + structured audit trail.
4. Add independent adversarial review and real journey evidence.
5. Add bounded self-correction and Skill candidate evaluation.
6. Build real cross-host acceptance and progress dashboard.

## Reporting
Each phase must link commits/PRs, files changed, executed tests, observed results, limitations, rollback, next steps. Keep existing Skills and user AGENTS.md unchanged unless an additive, reviewed change is explicitly authorized.
