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


## P1 implementation candidate — Builder
```sh
python -m tools.skill_builder demo-skill ./demo-skill --description "Reusable demo skill"
python -m tools.skill_builder demo-skill ./demo-skill --description "Reusable demo skill" --apply
```
Preview is read-only; `--apply` creates a new folder only and refuses existing destinations. Generated `SKILL.md` follows the minimal frontmatter entry format. This is a local authoring utility, not an installer or proof of Agent compatibility. Optional scripts are deliberately not generated or executed automatically.

## P2 implementation candidate — Lifecycle inventory
```sh
python -m tools.skill_lifecycle ./demo-skill
```
Produces deterministic SHA256 file inventory, reports structural preflight and marks all host runtime checks NOT_RUN. Does not install, auto-update, retire, roll back, release or merge. Existing installer remains responsible for guarded local backups and rollback. Future release automation requires explicit human authorization, actual host test evidence, provenance checks and existing release gates.

## Development backup and acceptance
Pre-upgrade GitHub snapshot branch: `backup/pre-universal-skill-upgrade-20261116` (from PR #22 head `a2c9d6f828e15412ce6e9c03804421128aecfc04`). Implementation branch: `feat/universal-skill-builder-lifecycle-20261116`. Do not merge or remove backup before review.

After implementation, run:
```sh
python -m unittest tests.test_skill_validator tests.test_skill_builder_lifecycle tests.test_agent_adapters -v
python -m compileall -q tools tests
```
A passing unit test does not substitute for clean Windows/macOS/Linux and real Agent invocation tests.
