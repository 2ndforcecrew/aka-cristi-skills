# Universal Agent Adapters — v0.1 development contract

AKA.CRISTI Skills is **agent-neutral at the core**. CHEF, verification, recovery and public Skills are portable methodology. A host-specific adapter is responsible for detecting capabilities, mapping rules and Skills to supported locations, respecting each host's native instruction precedence, and reporting observable runtime evidence.

## What this branch implements

- A read-only adapter registry and host-presence detector: `python -m tools.agent_adapters list` / `detect`.
- Candidate entries for Codex, Claude Code, Gemini CLI, OpenCode, Hermes Agent and custom agents.
- Conservative status labels. Presence of an executable or config directory **never** means Skills installation or CHEF orchestration works.
- No writes to user homes, no credentials, no automatic installer behavior, and no cross-vendor agent dispatch.

## Adapter contract for future implementation

1. `probe()`: detect host, version and actual capabilities without mutation; unknown capabilities are BLOCKED.
2. `plan()`: enumerate exact destination files, existing ownership, backup and rollback steps.
3. `install(confirmed=True)`: apply only allowlisted, validated public files after explicit user approval; preserve existing configurations and refuse conflicting changes.
4. `verify()`: verify file integrity **and separately** actual host runtime Skill activation; no mocked PASS for live claims.
5. `rollback(confirmed=True)`: restore only files owned by the installer with integrity checks.
6. `handoff()`: optional, only if an authenticated and supported runtime interface exists; no simulated agent connection.

## Compatibility and acceptance

| Host | Existing evidence / scope | Universal adapter status |
| --- | --- | --- |
| Codex | Existing installer candidate and CHEF rules | Runtime acceptance still gated |
| Claude Code | Existing project-scoped file candidate | No independently verified Skill runtime |
| Gemini CLI | No validated adapter | Discovery only |
| OpenCode | No validated adapter | Discovery only |
| Hermes Agent | No validated adapter | Discovery only |
| Custom Agent | No implementation | Requires explicit adapter |

Acceptance gates: preserve current CHEF and installer behavior; no unreviewed overwrites; isolated temporary home tests; Windows/macOS/Linux checks; per-host real Skill activation; permission boundaries; independent review; existing Issues #8–#13 remain BLOCKED until independently satisfied.

This branch does not change `main`, install anything, or authorize publication.
