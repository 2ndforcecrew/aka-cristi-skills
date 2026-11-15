# CHEF V0.2 — Native Codex Subagents

This is an **additive, portable setup** for the publicly released CHEF rules and Skills. The four role definitions use Codex's documented custom agent TOML format, not a homemade imitation of agents.

## What is included

| Role | Configuration | Responsibility |
| --- | --- | --- |
| Research | `agents/research.toml` → `aka_research` | Read-focused research and source evidence |
| Coding | `agents/coding.toml` → `aka_coding` | Scoped programming, repair and tests |
| QA | `agents/qa.toml` → `aka_qa` | Independent review and real evidence |
| Automation | `agents/automation.toml` → `aka_automation` | Safe, bounded automation design |

All roles inherit actual parent tools, permissions, provider and MCP connections. A TOML file does not authenticate to a separate provider, create credentials, or guarantee a subagent will spawn.

## Installation — Windows 11 / macOS / Linux

Requirements: Git, Python 3.11+ and a supported Codex client.

From a checkout of the public repo:

```powershell
# Existing CHEF core; safe preview first
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex

# Native custom agents: preview then explicit installation
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

By default this writes only its own role TOMLs into `$CODEX_HOME/agents/` or `~/.codex/agents/`; it does **not** edit `config.toml`, modify any existing custom role, enable paid tools, or overwrite another user's configuration. Default multi-agent configuration is managed by Codex; inspect your client version and `config.toml` before changing it. Do not insert `[agents]` blindly into an existing TOML file.

For an isolated test, add `--codex-home ./test-codex-home` to any of the commands.

## End-to-end verification

Open a **new Codex session** after installation. In a disposable test repository, request:

> Use $chef-orchestrator. Delegate independent read-only findings to aka_research and ask aka_qa to review them. Have both report a structured result with their agent name, evidence and status. Avoid any file changes, report whether genuine subagent threads were spawned, and if this host cannot spawn a role mark it NOT_RUN.

Save real Codex agent-thread IDs, timestamps, task request/response, and evidence of role selection. A console statement such as "I delegated" is not enough: inspect the **actual agent thread/tool call**.

After that, with a separately approved local throwaway coding fixture, test `aka_coding` and QA validation of the resulting change. Do not run a mass edit or production deployment during an acceptance test.

### Completion criteria

- PASS only when the real Codex host has loaded all four TOML definitions and actual subagent spawning has been observed with separate agent threads and results.
- PASS for Codex's orchestration requires at least one real handoff with evidence, return status, and independent review.
- The CI tests bundled here check **TOML structure and safe installation mechanics**. They do NOT invoke a signed-in Codex agent.
- Installed but unspawned = `NOT_RUN`. Unavailable permission, unsupported client or error must be recorded exactly.

## Safe removal

```powershell
python -m tools.codex_subagents uninstall --apply
```

Uninstallation only archives **installer-owned, unmodified** role TOMLs. Any existing user-created agents are preserved. Changed installed roles produce a conflict rather than being overwritten or removed.

## Architecture and later versions

- V0.2: Native Codex agents, existing global AGENTS.md installer, CHEF Skill and real host evidence procedure.
- V0.3: Add separately tested adapters for other providers (Hermes/Claude/others), not generic guessed support.
- V0.4: Integrate approved event tracking, candidate Skill generation and evidence-based evaluation.

## Sources

- [Codex official Subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

**Do not confuse OpenAI Agents API multi_agent session configuration with Codex desktop's local TOML role files; they are different integration surfaces.**
