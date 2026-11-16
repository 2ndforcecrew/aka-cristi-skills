# SkillSpector 2.13.4 upgrade — pinned CI verification (2026-11-16)

**Status: development candidate / no installation or release clearance.**

## Scope
- Previous SkillSpector version in PR #32 security reports: 2.12.0.
- New upstream version: **2.13.4**, source repository [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector), pinned exact source commit `54824463814a0be01360792523ec7245a69190fc`. Do not install by floating branch or unverified mirror.
- New independent GitHub Actions workflow: `.github/workflows/security-scan-v2134.yml`. It checks out the PR head, installs the pinned scanner in its disposable Python 3.13 runner, scans **both the complete working tree and the exact deterministic Git-blob ZIP from that revision**, and assesses both results with `tools.scan_report_gate`.
- Original 2.12.0 scanner, original 255-finding ledger, full-source 303 and package 304 reports, raw report hashes and findings dispositions remain unchanged. Windows 10 host installation is **not** overwritten or upgraded by this PR.
- Pre-upgrade Git snapshot: `backup/pre-scan-v2134-20261116` at `fffabade7863f8e6c4cf5bf7aafcac7995dec188`. New branch stacks on Draft PR #32.

## Why upgrade
2.13.4 improves source/archive inspection, parser boundaries and coverage diagnostics. Better scanning is **not** proof of safety. Release Gate #8 stays BLOCKED until actual results, scan limitations and remaining risks receive independent review. See upstream [2.13.4 release notes](https://github.com/NVIDIA/SkillSpector/blob/54824463814a0be01360792523ec7245a69190fc/docs/release/skillspector-2.13.4.md).

## Interpretation
- The scanner's unsuppressed `risk_assessment.recommendation`, execution success, source/package exact hashes and completeness take priority over test counts.
- Scanner outputs with `DO_NOT_INSTALL`, `CAUTION`, partial coverage, errors, suppressed findings or nonzero exit codes **cannot** produce green release clearance.
- A `STATIC_SCAN_PASS_ONLY` result is expressly **not** release approval. Actual dependencies, signed publisher provenance, native host configuration/MCP constraints, process tree cleanup, independent user acceptance and original missing external 67/24 scan are separate gates.
- GitHub CI uploads **only a sanitized numerical summary** (SHA256 of raw output, score/recommendation, coverage, item count, status). Raw reports remain transient inside the CI runner; never upload unredacted local agent histories, credentials or detailed outputs.
- Fixed CLI uses `--no-llm` to keep source contents out of hosted LLM providers. Dependency vulnerability lookups may still send declared dependency names/versions to OSV.dev; unavailable OSV verification is a limitation, never interpreted as safe.

## Verification on GitHub
Open the check named **Security rescan v2.13.4 (source and exact candidate)** on the draft PR. If it fails, inspect the sanitized audit artifact and logs, then address actual risks or analyzer coverage without deleting/suppressing findings.

Locally, only after separately reviewing tool installation, run from a disposable checkout:

```sh
python -m unittest tests.test_scan_report_gate -v
python -m compileall -q tools tests
```

The original full-source `DO_NOT_INSTALL` finding remains the authoritative warning until a new successful scan and independent security review expressly supersede it.

## Agent-isolation gaps (separate from scanner version)
Security ledger findings #247 and #250 concern live Codex host config/MCP permissions and descendant process termination on timeout. These cannot be proven by a static scanner upgrade or the prior four-agent task completion alone. Require a disposable host profile, explicit tool/MCP deny policy, bounded real process-tree cleanup and observable independent test evidence before marking these live-agent controls PASS.
