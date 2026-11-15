# Four-role correlation v0.3 — Issue #13

The verifier now requires this chain for each of four distinct roles and child IDs:

`spawn_agent(agent_type)` → same `call_id` structured JSON result with `agent_id` → exact child `session_meta.id` → exact `source.subagent.thread_spawn.parent_thread_id` → exact `agent_role` → terminal `task_complete`/`turn_complete` with nonempty reply and no error.

Top-level parent/role duplicates must agree with nested metadata. `agent_type` is supported as the documented serde alias for metadata role. Role substrings, task labels, UUIDs extracted from prose/errors, an intermediate assistant message, duplicate child IDs and wrong-parent rollouts cannot pass. A live run also rejects old child creation metadata even if the file was touched recently.

The sanitized report separates `SPAWN_ATTEMPT`, `SPAWN_SUCCESS`, `ROLE_SELECTED`, `CHILD_COMPLETED`, `ROLE_PASS`. CLI stdout completion alone is insufficient. Offline diagnostics expose stages without raw prompts or tool arguments. An offline classification is not a new live invocation.

## Schema reference

Source inspected on 2026-11-15: official [openai/codex at ee344ca](https://github.com/openai/codex/tree/ee344ca9458351a6ea102795fa73110ad3ede5dc).

- [protocol.rs](https://github.com/openai/codex/blob/ee344ca9458351a6ea102795fa73110ad3ede5dc/codex-rs/protocol/src/protocol.rs): `SubAgentSource::ThreadSpawn`, `SessionMeta`, `TurnCompleteEvent` and `task_complete` wire alias.
- [spawn.rs](https://github.com/openai/codex/blob/ee344ca9458351a6ea102795fa73110ad3ede5dc/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs): structured `SpawnAgentResult.agent_id`.

`tests/fixtures/codex/schema-reference.json` and test-generated sessions are **synthetic**, derived from those public types. They are not captured real Windows runtime fixtures. Unknown/older schemas remain INCONCLUSIVE instead of guessed successful.

## Remaining acceptance

This code change does not establish the four-role live PASS. Inspect the existing sanitized failed local report before repeating a quota-consuming invocation. The original raw Windows report is not available in this checkout. A real run must capture exact CLI version, root and child IDs, attributable metadata and completed replies. `run()` records only a validated CLI version string; credentials and raw logs are not copied into the public report.

Regression command: `python -m unittest discover -s tests -p 'test_four_agent*.py' -v`.

## Observed cloud attempt, 2026-11-15

One authorized bounded invocation was attempted with `codex-cli 0.167.0-alpha.4`, existing CLI authentication, four public role TOMLs staged under a temporary workspace and per-process config overrides. No user global roles/config or credentials were copied/modified. Timeout was 180 seconds, with no retries.

The CLI exited **1**, emitted no observed `thread.started`, produced no root ID and no completion. All four roles remain **NOT_VERIFIED**; the issue is **BLOCKED**, not a four-agent PASS. Stderr was not retained by that verifier version, so the cause (CLI config, network or another problem) cannot be asserted. The later code change classifies nonzero stderr into fixed safe categories; only synthetic tests cover that classification because the paid invocation was not repeated.

Sanitized observed report: [codex-cloud-attempt.json](evidence/codex-cloud-attempt.json). The report's `patch_commit` is null until the root coordinator records the actual branch commit. `--role-source ./agents` stages only public TOMLs for per-process overrides and leaves global host configuration untouched.

A separate **non-model** `codex ... features list` inspection with the same four temporary per-process role config overrides exited 0. This establishes that the configuration syntax is accepted by the current CLI, not that roles were loaded in a model invocation or that the earlier exec failure has been diagnosed.
