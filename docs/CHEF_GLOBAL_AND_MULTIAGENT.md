# CHEF Global Rules + Multi-Agent Starter

**Status:** Public starter package, not a complete multi-agent runtime. Local Codex host activation and cross-agent tool access must be verified separately.

## Layers

| Layer | Installed artifact | What it genuinely does |
| --- | --- | --- |
| Global operating policy | `~/.codex/AGENTS.md` | Gives Codex durable, scoped instructions for work across projects |
| CHEF coordination workflow | `~/.agents/skills/chef-orchestrator/SKILL.md` | Teaches the Agent to own planning, tool discovery, handoffs, review and bounded recovery |
| Verification Skills | `~/.agents/skills/{verified-change-loop,feature-journey-map,skill-evaluation-gate}` | Separate reproducible QA workflows |
| Agent runtime connections | Actual installed / authorized agent CLIs, APIs or MCP connectors | Are necessary to actually delegate tasks to different agents; **not included** |

## Install on your Codex Desktop/CLI machine

Prerequisites: Python 3.11+, a local checkout of this public repository, user permission to edit their own Codex files. Do not run on a friend's device without their explicit consent.

### 1. Inspect before modifying

```powershell
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex
```

The rules preview identifies the global file. It does not alter it.

### 2. Add the CHEF rules without replacing existing global rules

```powershell
python -m tools.chef_global_rules install --apply
```

The installer appends its uniquely marked **public** block to `CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`), makes a timestamped backup when a file exists, and refuses to replace an edited managed block. Project-level `AGENTS.md` continues to apply within its project.

### 3. Install CHEF and verification Skills

```powershell
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

Open a **new Codex session**. Try a task such as:

> Use $chef-orchestrator. Inspect this project without changing anything. Find actual connected agents and tools. Define a scoped build/review handoff and verify what's possible. State NOT_RUN for unconnected agents and do not invent results.

### 4. Verify installation vs live use

```powershell
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
python -m tools.verify_codex_activation --skill verified-change-loop --out local-activation-report.json
```

The first two check file/rule integrity. The third attempts an actual Codex CLI Skill invocation **only when Codex CLI is installed and signed in**, and uses a disposable read-only test fixture. It **does not yet exercise chef-orchestrator or multi-agent handoffs**. Treat the Agent use cases as `NOT_RUN` until actual invocation/communication evidence exists. If the user is in Codex Desktop, only the host itself can provide trustworthy user-visible activation evidence.

### 5. Revert safely

```powershell
python -m tools.skill_installer uninstall chef-orchestrator --target codex --apply
python -m tools.chef_global_rules uninstall --apply
```

The rules removal only removes the installer-owned unmodified block. It preserves preexisting global content and keeps backups of previously existing files. If the block was edited, stop and review manually.

## What a real multi-agent implementation requires

1. Identify the actual working Agent connectors (e.g. Codex CLI, another agent's native API or authorized MCP), permissions, versions and invocation capability.
2. Build adapters with explicit capabilities, timeouts, budgets, idempotent jobs and authenticated sessions.
3. Send each worker a scoped input/output handoff contract, never unrestricted access to other workers' secrets.
4. Use independently inspectable results and a separate reviewer. Verify an actual worker run, not a mock result.
5. Persist task status and audit logs; implement bounded retries, recovery and rollback.
6. Only enable unattended execution after real replay tests and explicit approval.

A Skill or AGENTS.md cannot grant capabilities, install hidden integrations, share private conversation memories, or bypass other providers' permissions.

## Portability / privacy

The public CHEF rule template is a **sanitized derivative** of general collaboration principles. It is **not** a copy of the owner's private source-of-truth AGENTS.md. Personal preferences and internal project references stay in the user's own private repository, and no automatic sharing/synchronization occurs. Cross-computer syncing requires authenticated Git/file syncing explicitly set up by each user.

Official background:
- [Codex agent loop and AGENTS.md discovery](https://openai.com/index/unrolling-the-codex-agent-loop/)
- [Codex Skills manual installation locations](https://developers.openai.com/api/reference/cli)
