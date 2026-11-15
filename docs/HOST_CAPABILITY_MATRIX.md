# Host capability matrix — 2026-11-15

**Issue #11 remains BLOCKED for real cross-host invocation acceptance.** File installation is an engineering milestone, not evidence of a loaded or successful agent. This branch adds a Claude Code **project-scoped Skill file adapter**; it does not create cross-vendor orchestration.

| Host | Skill discovery / adapter scope | Native roles | Tools / MCP | Authorization | Host version / OS | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Codex | Existing user `~/.agents/skills`; guarded local installer | Existing four TOML files, separate installer | Host-managed; adapter does not configure them | User-managed; no credentials inspected | Observed cloud CLI 0.167.0-alpha.4; isolated filesystem tests on cloud Linux | Synthetic unit tests and isolated installation only; four-role acceptance BLOCKED |
| Claude Code | New opt-in `<project>/.claude/skills/<name>/SKILL.md` | NOT_IMPLEMENTED by this adapter | NOT_IMPLEMENTED by this adapter | User-managed; no credentials inspected | Observed cloud CLI 0.167.0-alpha.4; isolated filesystem tests on cloud Linux | Local file lifecycle tests; loaded/invoked/completed_verified NOT_RUN |
| Hermes | No implemented adapter | NOT_VERIFIED | NOT_VERIFIED | Not inspected | NOT_RUN | BLOCKED |
| ChatGPT | No implemented adapter; copying local files does not install an app | NOT_VERIFIED | NOT_VERIFIED | Not inspected | NOT_RUN | BLOCKED |

Official primary source checked 2026-11-15: [Claude Code Skills documentation](https://code.claude.com/docs/en/skills), “Choose where skills load”. Project `.claude/skills/` discovery and explicit `/skill-name` invocation are documented. Existing Codex methods and their acceptance limitations are described in [Codex native subagents](CODEX_NATIVE_SUBAGENTS_V02.md). A separate [observed Codex cloud attempt](evidence/codex-cloud-attempt.json) exited 1 without attributable threads; no Claude invocation was made.

## Lifecycle contract

`tools.host_adapters.HostAdapter(host, project=None)` exposes:

1. `inspect()` — checks CLI availability and, if found, runs only `--version` with a five-second timeout. Publishes a bounded semver token rather than raw output. Does not inspect login or spend inference quota.
2. `preview(source)` — read-only local plan; Claude requires an explicit existing project. Codex retains existing user-scope behavior and rejects a project override.
3. `install(source, apply=False)` — preview until `--apply`; preserves unmanaged or changed files, records installer ownership and backups. No downloads or dependency installation.
4. `verify(name)` — checks installed file integrity. Returns separate `installed`, `loaded`, `invoked`, `completed_verified` fields. Only `installed` can become PASS here.
5. `live_activation()` — returns NOT_RUN with a reason. This is an explicit unsupported live-test boundary, not a mock agent invocation.
6. `uninstall(name, apply=False)` — previews by default; guarded archive of managed content with `--apply`. Existing local edits block uninstall.

Hermes and ChatGPT return BLOCKED for every lifecycle operation without mutation. Filesystem validation errors return FAIL without printing raw paths or content. Preview conflicts exit 1, unsupported or unexecuted activation exits 2.

## Isolated Claude project walkthrough

Use a fresh disposable project directory. These commands do not install a host or call a model:

```sh
mkdir claude-adapter-test
python -m tools.host_adapters claude inspect --project ./claude-adapter-test
python -m tools.host_adapters claude preview ./skills/verified-change-loop --project ./claude-adapter-test
python -m tools.host_adapters claude install ./skills/verified-change-loop --project ./claude-adapter-test --apply
python -m tools.host_adapters claude verify verified-change-loop --project ./claude-adapter-test
python -m tools.host_adapters claude live-activation --project ./claude-adapter-test
python -m tools.host_adapters claude uninstall verified-change-loop --project ./claude-adapter-test --apply
```

The activation command intentionally exits 2 / NOT_RUN. An authorized independent reviewer must separately open a real Claude Code session in that project, confirm discovery, invoke `/verified-change-loop` against a unique synthetic case and retain attributable sanitized host event logs. Record CLI version, OS, actual returned result and missing evidence. A host’s prose assertion that it used a Skill is insufficient. Do not copy private project context or token-bearing logs into the public repository.

## Acceptance still required

- Real Codex parent/child role correlation for all four named roles.
- Real Claude discovery, loading, invocation and completed-result evidence on an authorized host.
- OS/version-specific evidence before expanding the support matrix.
- A genuine supported Hermes/ChatGPT integration before advertising one.

`tests/test_host_adapters.py` uses temporary directories and one mocked version-probe timeout. Those tests validate installer machinery only.
