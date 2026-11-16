# Issue #31 security review — BLOCKED

Review of PR #30 baseline d3590a333c411569636bc6961c82704ec28560e2. Fixed code: 33905d59fd6fde55989930a46358c2e60b940de9. This is not a release or installation recommendation. No suppression or bulk SAFE label was added.

## Individual review

security-findings.json preserves all 255 original rows, original severity/location/fingerprint, preliminary judgment, individual rationale, evidence and residual risk. Rule + canonical file + original line + fingerprint identifies 250 groups: five same-line pairs remain separately documented, not discarded. Original source hashes refer to Git blobs; Windows CRLF differences are not source logic drift.

| Original group | Reviewed outcome |
| --- | --- |
| 44 NEEDS_REVIEW | 41 specific detection claims FALSE_POSITIVE; 1 FIXED_CONFIRMED_RISK; 2 BLOCKED_EVIDENCE (#247, #250) |
| 96 preliminary false positives | 96 independently reviewed FALSE_POSITIVE, each with source references and residual risk |
| 115 historical records | 115 HISTORICAL_DATA_REVIEWED; underlying historical risks not re-certified |

Original severity: HIGH 38 / MEDIUM 215 / LOW 2. The 115 historical matches are serialized scanner/triage fields (72 report, 43 triage). Each JSON value/pointer and source/line hash was checked; independent QA verified all 115. They remain in the full source/archive. The installer requires a SKILL.md entry and the packager copies committed blobs; no historical excerpt was executed, silently excluded or accepted as trusted instructions. FALSE_POSITIVE rejects only the specific detector interpretation, not file/package/host safety. Actual sudo operations, trusted PATH/hooks, native keyring, OAuth scopes and content allowlist limits remain explicit residuals.

## Confirmed defects and fixes

1. Failed atomic writes blindly restored the backup, overwriting concurrent edits or recreating a deleted file. Removed that blind restoration; retain backup and original exception. Commit e75840c4e66407b185492ab28924f2aa99d4ee99. RED two failures; GREEN edit/deletion/retry regressions.
2. Independent QA reproduced a second-read ownership defect: user edits after preview could be deleted by uninstall. Revalidate ownership and idempotent state on the second read before backup/write. Commit 33905d59fd6fde55989930a46358c2e60b940de9. RED one failure; GREEN refuses the edit and handles concurrently installed/removed blocks without writing. Independent QA replay preserved the edit.

Only tools/chef_global_rules.py and its tests change runtime behavior. There is no cross-process compare-and-swap: writes between the final read and os.replace remain a residual. Do not describe these fixes as universal concurrency safety. Native DACL, real disk-failure injection and hostile directory replacement are NOT_RUN.

## Scanner provenance and coverage

Recovered local original JSON (560,940 bytes), flags, version, stderr, summary, triage and driver. Raw JSON SHA256: 961fb7759e27c04cc94cff7da02b274f08898d7c197ffafbb813ae1f1101cce8. SkillSpector 2.12.0 used scan <staged target> --no-llm --format json, stdout captured separately and parsed after exit, no --output. Original: DO_NOT_INSTALL, 255 findings, 98.1%, 104 full / 2 partial / 0 entirely uninspected. Original external 67-score/24-finding report is UNAVAILABLE; this is a different scan.

Installed scanner editable source lacks static_patterns_supply_chain.py. Preserve that installation; separately use isolated clean NVIDIA/SkillSpector source commit d501c0d5035c2ed6385740a384d942bb05651fda with existing dependencies. No install/update, permission change or hosted LLM. Executable SHA alone cannot establish historical editable-engine code.

Checkpoint scans below are at e75840c, BEFORE the QA-discovered second-read fix and BEFORE these audit documents:

| Input / engine | Findings | Recommendation | Coverage |
| --- | ---: | --- | ---: |
| Full source / installed engine | 254 | DO_NOT_INSTALL | 98.1% |
| Actual deterministic source package / installed engine | 254 | DO_NOT_INSTALL | 98.1% |
| Full source / clean engine | 255 | DO_NOT_INSTALL | 96.2% |
| Actual deterministic source package / clean engine | 254 | DO_NOT_INSTALL | 98.1% |

Clean source adds SC4: OSV.dev unreachable, limited fallback for 15 dependencies. This is a coverage blocker, not proof dependencies are vulnerable or safe. Absence from another scan does not clear intermittent lookup failure. Twelve installed-engine analyzers are degraded; clean engine restores supply-chain analysis but still reports partial coverage. Full source and actual package have the same 107 tracked files; git archive applies CRLF under current Windows Git configuration, while tools.release_package stores exact committed blobs. Both byte sets were scanned.

Exact final-head source and actual package will be rescanned after this report commit; immutable SHA/archive/output digests and results belong in the Draft PR verification record, avoiding recursive report hashes. Checkpoint scans do not certify the final code/documents. New rescan-only findings stay BLOCKED until reconciled; original dispositions are not silently transferred. The actual package is the existing deterministic source ZIP requiring Python >=3.11; no filtered runtime bundle is substituted. Standalone EXE binary-security acceptance is NOT_RUN; CI EXE smoke proves function only.

## Test evidence

Windows 10 Pro 19045 / PowerShell / Python 3.13.11 / Git 2.56.0.windows.4 / Codex CLI 0.169.0. Local commands use py -3.13 because the python WindowsApps alias is not reliable.

| Check | Result |
| --- | --- |
| First fix targeted rules / transaction | PASS: 14 / 15 total; each 1 symlink skip |
| First fix full regression | PASS: 268 total; 12 skips |
| Second fix targeted rules / transaction | PASS: 16 / 15 total; each 1 symlink skip |
| Second fix full regression | PASS: 270 total; 258 passed, 12 skips |
| Independent QA second-fix rules suite | PASS: 16 total; 1 symlink skip; reproduced defect now refused |
| Ruff changed Python files | PASS |
| Exact final-head remote CI | PENDING at report creation; see Draft PR |
| Real disk failure, native keyring/DACL, external three-platform UAT | NOT_RUN |

Command: py -3.13 -B -m unittest discover -s tests -p test_*.py -v. Full suite includes Validator, Builder/Lifecycle, Agent Adapters, preview-conflict zero writes and second-run authorization tests. Isolated profile/Codex roots; private log hashes and RED/GREEN summaries in ledger. Twelve local skips are symlink-privilege limitations; no privilege was enabled. CI must provide its own platform evidence; SKIP is not PASS.

## Preservation and release gate

Independent branch: security/issue31-findings-review-20261116. Remote backup backup/pre-universal-skill-upgrade-20261116 = a2c9d6f828e15412ce6e9c03804421128aecfc04. Local backup/pr30-d3590a3 preserves PR #30. Original dirty checkout and prior PR #30 checkout are retained, with baseline hashes/status for final comparison. Private raw logs and source scan outputs remain outside Git; only sanitized review evidence is committed.

Release remains BLOCKED: #247/#250 real Agent host-config/MCP isolation and descendant cleanup; incomplete scanner/supply-chain coverage; missing original 67/24 report; external UAT; final-read-to-replace concurrency and native-storage evidence. No main merge, Release, production change or security-permission change is authorized.
