---
name: chef-control-center
description: Track actual Agent work using portable task events, summarize progress, failures, retries and verification evidence, and require explicit approval for consequential actions.
---

# CHEF Control Center — Portable Agent Skill

## Use when
A user asks which Agent is working, what step it reached, why it failed, how long it took, whether it was tested, or requests retry/approval tracking.

## Host-neutral workflow
1. Discover host capabilities and existing task logs. Do not assume Codex, a running daemon, cloud account or another Agent is connected.
2. Record the real task/role/status transition with the bundled Python CLI if local execution is authorized and available; otherwise produce a structured handoff for the host's own logging system.
3. Read task state using `python -m tools.chef_skill_events --db <private-db> list` from the repository checkout, or the installed Skill's `scripts/events.py` directly.
4. Report actual task IDs, actor names, stage, timestamps, elapsed time and evidence references. Never invent active workers or tests.
5. On failure, diagnose and propose a bounded retry. Do not trigger retries solely because a task is BLOCKED. A retry requires a supported runtime, matching source revision, remaining attempts and explicit authorization for its effects.
6. For paid calls, publication, external sharing, credential changes, destructive operations or production changes, request user approval before execution; store decision metadata only, not secrets.
7. Mark file installation, Agent loading, actual execution and independent QA as distinct verification states.

## Event protocol
See `references/event-schema.md`. Events must be append-only, timestamped, actor-attributed and use real evidence references; evidence content stays in its original protected location.

## Local CLI
```bash
python scripts/events.py --db /private/chef-events.sqlite3 record --task TASK-001 --actor coding --status STARTED --stage implementation
python scripts/events.py --db /private/chef-events.sqlite3 list
python scripts/events.py --db /private/chef-events.sqlite3 timeline --task TASK-001
```
Use a private database outside source control. This CLI does not spawn Agents, grant approvals, or execute retries.

## Security
- No remote access, automatic model spending, private-log publication or self-approval.
- If tools are missing, state NOT_RUN and offer a portable manual event record.
- Never treat a copied SKILL.md as proof the host activated it.
- Preserve existing files and respect higher-priority host instructions.
