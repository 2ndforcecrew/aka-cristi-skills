# Universal Skill Architecture — incremental upgrade

Status: **P0 preflight candidate**, not a release or verified multi-agent runtime.

## Design
Keep the existing installer, skills, rules and adapters. A standard `SKILL.md` remains the portable entry point. Scripts are optional and must not execute merely because a Skill is inspected. Agent-specific host integration belongs in adapters, never in the core workflow.

## P0 — Skill Validator
```sh
python -m tools.skill_validator skills/verified-change-loop
python -m unittest tests.test_skill_validator -v
```
Read-only preflight checks entry, required metadata, nonempty instructions, script directory and symlink hazards. JSON reports `PREFLIGHT_ONLY` or `FAILED`. A successful preflight **never** proves a Skill was loaded, invoked or successfully executed by Codex, Claude, Gemini, OpenCode or Hermes.

Limitations: this minimal validator does not fully parse YAML, validate script content, prove script safety, test trigger accuracy, run user journeys, install dependencies or certify host compatibility. Multiline descriptions are flagged for review. Future versions should use a maintained YAML parser and documented schema with adversarial fixtures.

## P1 — Universal Skill Builder (planned)
Generate a standard minimal Skill with optional `scripts/`, `references/`, `tests/` and adapter configuration. Detect dependencies before installation; never overwrite an existing Skill or execute arbitrary scripts by default.

## P2 — Lifecycle Manager (planned)
Version pinning, provenance, reproducible evidence, rollback, compatibility matrix, maintenance/deprecation policy and human release gates.

## Release gates
Existing Issues #8–#13 remain BLOCKED. All high-impact operations need explicit authorization. A draft PR is not a merge or installation recommendation.
