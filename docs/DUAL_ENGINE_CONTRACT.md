# CHEF Dual-Engine contract — Issue #20

This additive contract complements existing CHEF Orchestrator, Verified Change Loop, Feature Journey Map and Skill Evaluation Gate. It does not replace their instructions.

## Task envelope (illustrative, not operational evidence)

```json
{
  "schema_version": "1.0",
  "task_id": "EXAMPLE-001",
  "goal": "Describe observable outcome",
  "scope": ["authorized/path"],
  "engine": "both",
  "risk": "low",
  "permissions": ["read"],
  "factory": {"owner": "UNASSIGNED", "status": "NOT_RUN", "evidence": []},
  "studio": {"owner": "UNASSIGNED", "status": "NOT_RUN", "evidence": []},
  "acceptance": ["Observable user journey"],
  "independent_review": "NOT_RUN",
  "human_approval": "REQUIRED",
  "merge": "BLOCKED"
}
```

Allowed engine values: `factory`, `studio`, `both`. Gate statuses: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`. A task may reach VERIFIED only after its required gates have actual evidence and an independent reviewer; never infer verification from generated text.

## Factory
Trigger → isolate/reproduce → execute actual app → collect logs/traces/metrics → minimal reversible patch → rerun identical scenario → compare regressions. Bounded retries and timeouts; preserve baseline and artifact provenance.

## Studio
Evaluate product vision, real user journey, visual consistency, accessibility, user psychology and commercial impact. Explicitly reject technically correct changes that violate user intent. Screenshots and real-host tests are required where applicable; if unavailable mark NOT_RUN.

## Release and safety
Default PR mode is draft. Auto-merge is disabled until separately approved low-risk policy, protected branch checks and reviewer gates are proven. Never auto-publish, modify production secrets, change permissions, expose private rules or silently deploy.

## Evidence manifest
Store task ID, repository revision, environment, timestamp, commands, exit codes, redacted artifact references, gate-specific outcomes and reviewer identity. `tools/skill_evidence.py` remains authoritative for existing evidence validation; this document does not claim it implements the new contract.

## Acceptance backlog
- [ ] Runtime routing and machine-readable schema validation
- [ ] Factory before/after real application proof
- [ ] Studio rejection of passing-code/bad-UX example
- [ ] Timeout/retry/rollback integration tests
- [ ] Independent review and approval guard tests
- [ ] Dashboard sanitized status feed
- [ ] Multi-host real-world acceptance

Existing six release gates remain BLOCKED until separately verified.
