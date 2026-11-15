# External acceptance plan — Issues #10–#12

**Status: BLOCKED / no independent external tester or real host invocation has been observed for this branch.** A CI runner or developer’s temporary directory is not a first-time nontechnical external user. No Windows, macOS or Linux human acceptance PASS is claimed.

## Entry conditions

Use an isolated fresh machine/VM, standard user without this project’s prior configuration, and a release candidate tied to an exact 40-character source commit. Do not test an unverified network archive or disable security settings. Security triage #8 and provenance verification #9 must be reviewed before external distribution. Keep original source files, local configs and any failed run evidence. Each supported platform requires at least one genuinely independent external person. Use aliases, not names, emails, account IDs or private screenshots.

## Platform matrix

| Platform | Required entry and scenarios | Real host acceptance | Current result |
| --- | --- | --- | --- |
| Windows 11 | Standard user, Python/Codex missing, declined elevation, invalid/incomplete archive, offline/interrupted download, proxy failure, consent/diff, cancellation, retry, edited configs, second install, rollback/uninstall | New authorized Codex session; Skill loading and four-role invocation separately observed | BLOCKED — no real Windows 11 external user |
| macOS | Python 3.11+ CLI, actual user paths, missing prerequisites, existing configs, preview/apply/reinstall/rollback, symlink refusal | Authorized Codex Skill loading/invocation separately observed | BLOCKED — no external user |
| Linux | Python 3.11+ CLI, actual user paths, missing prerequisites, permission refusal, existing configs, preview/apply/reinstall/rollback, symlink refusal | Authorized Codex Skill loading/invocation separately observed | BLOCKED — no external user |
| Claude Code project scope | Disposable explicit project; preview/install/integrity/uninstall; detect edited Skill conflicts | Discovery/loading/direct invocation/completed result against unique read-only fixture | NOT_RUN — no authorized real host run |

Only observed host/platform combinations may graduate in README. Keep unsupported combinations visible. Record failed attempts and recovery rather than selecting only successful evidence.

## Per-user recording

Use [uat-template.json](evidence/uat-template.json) as an empty index, not a successful result. For every scenario retain:

- Exact source commit, candidate version/archive SHA-256 and reviewed publisher provenance.
- OS/version/architecture, Python and host CLI versions, user privilege level, whether this is a first installation.
- Anonymous tester alias, independence statement and reviewer alias; no credentials or live customer information.
- Start/end timestamps, time to usable installation, permission prompts and consent choices.
- Ordered steps, expected vs observed outcome, recovery actions, terminal/UI evidence references and artifact SHA-256.
- File-install integrity, loaded, invoked and completed_verified outcomes separately. Use NOT_RUN when not observed and BLOCKED with the actual reason when unavailable.
- Actual per-role parent/child correlations separately; a root process exit 0 cannot substitute for child completion.

Review raw logs privately for secrets before making a sanitized attachment public. Do not publish the original scanner report if it contains private materials. Record its digest and private review reference instead.

## Six-gate documentary preflight

```sh
python -m tools.acceptance_gate docs/evidence/uat-template.json --evidence-root docs/evidence
```

Exit 2 and `BLOCKED` are expected for the empty template. This stdlib utility checks the presence, exact source commit and digest of local JSON attachments, rejects traversal/symlinks, requires observed rather than synthetic classification, and lists missing fields per issue. Claimed `status: PASS` fields have no authority. It does **not** validate human identity, prove tester independence, verify signatures, reproduce scanner findings, or establish runtime role success. Complete-looking records produce only `REVIEW_REQUIRED`, never PASS. `completion_notification_allowed` is always false; the tool cannot authorize a release or completion announcement.

Independent reviewers must assess the original scanner/version/flags and all 24 findings, provenance identity and negative tests, actual Windows GUI behavior, real cross-host invocation, each external platform user and four attributable Codex role completions. Only after all six issue acceptance criteria are genuinely verified may CHEF issue the requested completion notice and prepare the growth-site update. Production deployment remains separately unauthorized by the current task.
