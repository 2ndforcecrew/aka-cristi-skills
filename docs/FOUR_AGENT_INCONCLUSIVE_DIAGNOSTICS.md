# Four-Agent Diagnostic — local evidence only

If the live acceptance report says `INCONCLUSIVE`, **do not repeat costly Codex calls yet**. Instead, use the returned `root_thread_id` to inspect the existing rollout locally without sending raw session logs to anyone.

In PowerShell (from the public repository root):

```powershell
py -m tools.diagnose_four_agents --root-thread YOUR-ROOT-THREAD-ID --out four-agent-diagnostic.json
```

Replace `YOUR-ROOT-THREAD-ID` with the UUID in your previous report.

The output **only contains aggregate tool names, field-presence counts, event kinds, unverified role names and sanitized metadata field names**. It does **not** output raw agent prompts, session contents, tool arguments, credentials or private paths. Host-wide subagent counts are deliberately labeled **unattributed** and are not proof that the current run spawned anyone.

Interpretation:
- `root_rollout_found: false`: the checker cannot find the session file in the configured `CODEX_HOME`; investigate path or retention.
- `spawn_calls_observed: 0`: no native spawn event appeared in the root response-item rollout; confirm whether your Codex build exposes custom agent spawning.
- `spawn_calls_observed > 0` but `named_role_spawn_outputs: []`: actual spawn tool calls may exist, but role selection, return payload or correlation does not meet the strict parser.
- A `named_role_spawn_outputs` value only shows a **candidate paired spawn**; full PASS still requires a separate matched child rollout with selected role and reply.

For a genuine real-world PASS, the role must be proven with a tool call + corresponding successful child thread + role identity + completed reply. Static TOML and `agent_completion_observed: true` are **not** proof of four Agent invocations.

This diagnostic runs only on the local files of the signed-in Codex account. Do not upload raw `~/.codex/sessions` files or authentication directories.
