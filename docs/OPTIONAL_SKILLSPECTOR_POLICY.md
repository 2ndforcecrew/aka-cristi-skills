# Third-party scanner policy — 2026-11-16

AKA.CRISTI Skills is independent of NVIDIA SkillSpector. SkillSpector is an optional external static-audit tool, not a runtime dependency, product feature, or required publication gate.

## Workflow separation

- `.github/workflows/security-scan-v2134.yml` is **manual only** (`workflow_dispatch`). It does not run on each PR or gate merge/release by itself.
- Preserve previous security findings, audit outputs and scanner instructions; do not delete or mislabel evidence as a PASS.
- Do not substitute scanner status for security review, host-MCP isolation, process lifetime enforcement, actual multi-agent acceptance, build/test, signature/provenance validation, or external user installation testing.
- `.github/workflows/tests.yml` and the Windows Job Object regression remain independent quality checks.
- Historical `DO_NOT_INSTALL` decisions are records of the scan, **not** a certification of this candidate. A changed policy does not invalidate or resolve actual findings.

## Historical scan data is excluded from scan input (WP-A, 2026-11-24)

### Exclusion-mechanism check: NOT supported

Checked in order (WP-A, 2026-11-24, branch `feat/muse-scan-triage-20261124`):

1. `skillspector scan --help` (local SkillSpector 2.12.0): **no `--exclude` /
   `--ignore` option exists.** The only adjacent mechanisms are `--baseline`
   (suppress findings by fingerprint) and `--use-shipped-baseline`.
2. No `.skillspector*` config file exists in the repo.
3. `.github/workflows/security-scan-v2134.yml` previously ran
   `skillspector scan .` with no exclusion of any kind.
4. `tools/scan_report_gate.py` has no exclusion-list logic — and it actively
   rejects suppression: any report with `suppressed_count != 0` is
   `BLOCKED_INVALID_REPORT`. So `--baseline` is incompatible with this repo's
   fail-closed gate, and suppression is the wrong tool anyway: it hides
   conclusions, while what needs excluding is non-source *input*.

**Conclusion: path exclusion is NOT supported by the scanner. Do not claim
otherwise, and do not work around it with a baseline.**

Caveat: the check ran on local 2.12.0; CI pins 2.13.4
(`git+https://github.com/NVIDIA/SkillSpector.git@54824463814a0be01360792523ec7245a69190fc`).
WP-G re-checks `scan --help` on 2.13.4 at the next rescan. The staging approach
below does not depend on the scanner version, so the conclusion stands either
way. The new scan's own report corroborates it: its "Scope exclusions" list
contains only `.git/` metadata and one binary `.gz` file — no ignore file was
honoured, and every committed evidence JSON was scanned.

### Staging instead of scanner exclusion

The workflow scans a staged copy of the checkout, built by
`.github/scripts/stage_scan_source.py` from the list in
`.github/scan-exclusions.txt`. The script fails closed: every pattern must
match at least one path, the output directory must be empty and outside the
repo, and the staged tree is re-checked for leaked excluded paths. It writes
a staging manifest (sha256 of every staged file **and** every excluded file,
plus source commit and worktree-clean flag) that the workflow archives next to
the scan summary, so "what was scanned" stays auditable. Precedent: the old
review did the same thing — `security-findings.json`
`original_scan.scan_arguments` is
`scan <exact staged source archive root> --no-llm --format json`.

Excluded paths and reasons (the list in `.github/scan-exclusions.txt` is
authoritative; this is a copy):

- `security-findings.json` — the old 255-item review ledger; historical scan
  data, not runtime source.
- `docs/evidence/` (whole directory) — historical scan outputs and attempt
  records, not runtime source. (The `.gz` inside it was already skipped by
  the scanner itself as binary content.)
- `.github/scan-exclusions.txt` and `.github/scripts/stage_scan_source.py`
  themselves — staging tooling, not shipped source; excluding them avoids
  self-referential scan noise. Their hashes are recorded in the manifest as
  excluded files, so the mechanism itself stays auditable.

**What is excluded is the scan input, not the disposition.** The 165
findings these files attracted in the 2026-11-24 rescan (48 in
`security-findings.json`, 72 in `docs/evidence/skillspector-baseline-report.json`,
43 in `docs/evidence/skillspector-baseline-triage.json`, 2 in
`docs/evidence/chef-dual-engine-v03-live-attempt.json`) are dispositioned item
by item as HISTORICAL_DATA_REVIEWED in
`~/workspace/aka-skills-review/wp-a-historical-165.md`, each with its old
source (old finding_id / old report line). Nothing was deleted: `git status`
after WP-A confirms `security-findings.json` and `docs/evidence/*` untouched.

Scope limit: staging applies to the **full-source scan only**. The
deterministic package scan still contains the evidence files, because
`tools/release_package.py` archives every committed blob; findings on those
paths in the package scan are dispositioned by the same WP-A file, not by
exclusion. The triage summary `docs/TRIAGE-2026-11-24.md` is already in the
exclusion list; any further triage summary placed under `docs/` must be added
to `.github/scan-exclusions.txt` as an exact path before the next rescan —
until then it is scanned.

Build caches are hard-excluded by the staging script itself
(`__pycache__` directories and `*.pyc` files, plus `.mypy_cache/` and
`.ruff_cache/`): they are machine-generated, change on every local run,
and are not scan input. They are skipped silently and do not appear in
the manifest's `excluded` count, which is reserved for the
exclusion-file patterns. A fresh CI checkout has no caches, so CI
staging is unaffected; a local re-scan relies on this exclusion instead
of requiring a manual cleanup first.

## Release decision

A publication must be based on verified project-specific release checks (CI, safe installer, runtime scope and permissions, package provenance/signature, realistic install acceptance). Unverified security controls are disclosed and must not be labelled verified. GitHub repository rulesets may additionally require status checks and must be inspected before merging; this repository change does not automatically alter branch protection.
