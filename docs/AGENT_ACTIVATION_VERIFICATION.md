# Codex Agent Real Invocation Verification V0.1

## What counts as evidence?

File installation is NOT equivalent to Agent activation. The local runner `tools/verify_codex_activation.py` makes a **real Codex CLI call** via `codex exec --json` when this machine has a signed-in Codex CLI. It creates a disposable sandbox containing the selected published `SKILL.md` and a synthetic incident `CASE.md`.

It only marks **PASS** when ALL these independent checks are met:
1. Codex completed its turn successfully.
2. The Codex JSONL tool trace includes a successful read of the Skill's `SKILL.md`.
3. The trace includes a successful read of `CASE.md`.
4. The final Agent message contains the case ID that was **not** included in the prompt.
5. The Agent honestly labels unavailable live-app reproduction as `NOT_RUN`.

A different CLI trace shape, absent file read, unauthenticated process, missing runtime, or incomplete turn cannot be reported as a successful activation. `PASS` proves this **single synthetic case** invoked and used the Skill's instructions; it does not certify all future Agent behaviors, other models, unrelated host plugins, or real production apps.

## Execute in an AUTHORIZED local Codex environment

From the public repo root, with Codex CLI installed and authenticated via the official browser sign-in:

```powershell
codex login status
python -m tools.verify_codex_activation --skill verified-change-loop --out agent-activation-report.json
```

Run the other two Skills separately:

```powershell
python -m tools.verify_codex_activation --skill feature-journey-map --out report-journey.json
python -m tools.verify_codex_activation --skill skill-evaluation-gate --out report-evaluation.json
```

The runner does **not** sign in automatically, copy credentials, upload private files, change local installed Skills, write to the target project, or execute source scripts. It uses the signed-in Codex CLI locally in an ephemeral temporary directory and requests `read-only` sandboxing. Codex execution may consume your account quota or API credits; the user must authorize that separately if needed.

### Result statuses

| Status | Meaning |
| --- | --- |
| `PASS` | Observed real Codex turn plus required Skill read, fixture read, case-ID response, honest NOT_RUN |
| `FAIL` | Agent attempted but missing required evidence or behavior, or failed/timed out |
| `NOT_RUN` | No usable Codex CLI or authenticated Codex session; never silently transformed into PASS |

Return codes: PASS=0, FAIL=1, NOT_RUN=2.

## Automated tests in GitHub Actions

The CI suite exercises the assessment logic using synthetic trace fixtures and negative cases. **A mocked trace PASS inside a unit test is not a real invocation**. Public GitHub Actions does NOT have access to the user's locally signed-in Codex session, so the workflow makes no assertion of real agent activation.

The production-host E2E criterion remains **NOT_RUN** until the report from an actual Codex run is reviewed. Do not commit raw Codex logs or auth credentials; reports are intended to be reviewed before publishing. Never accept a user-provided report without authenticity checks.

Official docs: [Build Skills](https://learn.chatgpt.com/docs/build-skills) · [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
