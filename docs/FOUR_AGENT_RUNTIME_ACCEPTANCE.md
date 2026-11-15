# CHEF V0.2 — Real Four-Agent Codex Invocation Acceptance

This is an **actual runtime acceptance gate** for `aka_research`, `aka_coding`, `aka_qa` and `aka_automation`. It never reports a synthetic or mocked worker as a real Agent.

## Scope and prerequisites

- Supported Codex CLI installed on **the same machine** where the acceptance test runs.
- Codex CLI authenticated by the user using the official login flow (`codex login status`).
- All four role TOMLs installed and verified under `~/.codex/agents/` or `$CODEX_HOME/agents/`.
- Enough account quota for an interactive agent + four subagent calls. This consumes Codex usage; no hidden API key is required when using supported ChatGPT login.
- The runtime must support named custom-role selection and accessible saved rollout logs. Some Codex versions can actually spawn subagents while omitting spawn events from `codex exec --json`; the verifier attempts to use session rollout evidence as a stronger, direct source.

## Run

From a Git clone of this public repository, in PowerShell, Terminal, or a supported shell:

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify

codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

The verifier creates a **temporary synthetic project**, calls **actual** `codex exec --json` with read-only sandbox, explicitly instructs CHEF to spawn exactly four custom roles and wait for replies, and inspects the newly created root and child Codex session rollout files. It does not edit an existing Git repo, use credentials from ChatGPT, alter existing global rules, or submit real client data.

## Evidence and statuses

| Status | Meaning |
| --- | --- |
| PASS | Root Codex turn completed; **all four** distinct named custom-role spawn calls paired with successful outputs; child thread rollout for each proves role and response |
| INCONCLUSIVE | Codex ran but runtime event format, missing child metadata or missing session rollout prevented strict verification. This is NOT PASS. |
| FAIL | Codex execution failed or timed out |
| NOT_RUN | Codex CLI missing, not authenticated, or four roles not installed |

Machine-readable summary records root thread ID and confirmed child thread IDs only. It **does not copy raw Codex rollout content** or authentication information into the summary. Inspect any report carefully before sharing it.

A worker's own message saying “I am aka_qa” is **not** proof the configured custom role was instantiated. Neither is a `task_name` label, a valid TOML file or a passing unit test. Validation explicitly rejects those as sufficient evidence.

Codex can change rollout schemas and local session retention; if the verifier is too strict for a newer build, record INCONCLUSIVE, inspect the host's actual spawn traces, and update the parser with a regression test. Do not relax the criterion into a text-only PASS.

## Current release status

The test implementation and negative-case CI are automatable without paid Codex credentials. **A real four-agent PASS requires running this script on an authenticated Codex host**. CI tests assess evidence logic only and cannot imply live activation.

### Compatibility references

- [OpenAI Codex custom agents](https://developers.openai.com/codex/subagents)
- [OpenAI Codex CLI noninteractive mode](https://developers.openai.com/codex/non-interactive)
- [Codex issue: missing spawn event in JSON output](https://github.com/openai/codex/issues/41590)
- [Codex issue: named custom agent cannot be selected on some builds](https://github.com/openai/codex/issues/33244)

**Do not publish user authentication files, whole Codex session logs, or private app data.**
