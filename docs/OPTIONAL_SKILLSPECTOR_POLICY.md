# Third-party scanner policy — 2026-11-16

AKA.CRISTI Skills is independent of NVIDIA SkillSpector. SkillSpector is an optional external static-audit tool, not a runtime dependency, product feature, or required publication gate.

## Workflow separation

- `.github/workflows/security-scan-v2134.yml` is **manual only** (`workflow_dispatch`). It does not run on each PR or gate merge/release by itself.
- Preserve previous security findings, audit outputs and scanner instructions; do not delete or mislabel evidence as a PASS.
- Do not substitute scanner status for security review, host-MCP isolation, process lifetime enforcement, actual multi-agent acceptance, build/test, signature/provenance validation, or external user installation testing.
- `.github/workflows/tests.yml` and the Windows Job Object regression remain independent quality checks.
- Historical `DO_NOT_INSTALL` decisions are records of the scan, **not** a certification of this candidate. A changed policy does not invalidate or resolve actual findings.

## Release decision

A publication must be based on verified project-specific release checks (CI, safe installer, runtime scope and permissions, package provenance/signature, realistic install acceptance). Unverified security controls are disclosed and must not be labelled verified. GitHub repository rulesets may additionally require status checks and must be inspected before merging; this repository change does not automatically alter branch protection.
