# AKA.CRISTI Skills — Release acceptance checklist (Codex-first)

Status: **CANDIDATE / NOT PUBLISHED**. Record exact candidate SHA, CI run links, SHA-256 and signatures; never substitute a prior commit's artifact or synthetic test for current release evidence.

## v1.0 supported surface
- Codex-first installer with four methodology Skills, global managed AGENTS.md, and four Codex role definitions.
- CLI and Windows GUI local-file preview, explicit consent, guarded apply, verify and rollback.
- Windows Job Object timeout containment has actual Windows regression evidence but is **not** an OS permission or MCP sandbox.
- Personal AI Workspace OAuth, account creation, synchronization, cross-vendor live activation and fully automated cross-agent orchestration are **experimental / NOT VERIFIED** until real end-to-end acceptance; do not advertise these as stable or automatically connected.

## Release checklist

| Check | Evidence required | Current state |
| --- | --- | --- |
| PR integration | PR targeting main, no unresolved conflicts, exact merged commit | PENDING |
| Core CI | All Windows/macOS/Linux and package-quality jobs green for merged SHA | PASS only on previous PR-head run; merged SHA pending |
| Job lifetime | Windows Job Object regression green, with actual parent/child/unrelated-process checks | PASS on earlier PR-head CI; merged SHA pending |
| Host activation | Four real named Codex child roles, traceable parent/thread and completion; exact version and commit; no raw credentials uploaded | Historic scoped evidence exists, needs release-specific review |
| Credential/MCP scope | dedicated probe home, no unintended host configuration/secret inheritance; residual sandbox limits documented | preflight implemented; live security acceptance pending |
| Provenance | deterministic package exact commit; artifact digest; GitHub OIDC attestation verified against exact repo/workflow/ref | release SHA not yet built |
| Windows EXE | actual frozen EXE starts in clean profile, provenance verified; distinguish GitHub attestation from Authenticode | release SHA not yet built; Authenticode NOT_SIGNED |
| Fresh Windows 11 UAT | independent standard user install → verify → reinstall → rollback/uninstall, with missing prerequisites and failure recovery | NOT_RUN |
| Public GitHub Release | tag matches approved main SHA; documented caveats and supported scope; attach artifact/digests/provenance | NOT_PUBLISHED |

## Instructions for independent Windows 11 tester
1. Obtain the **exact release candidate** only after verifying independently reviewed GitHub SHA-256 and source/signer provenance. Do not run arbitrary third-party installers.
2. Record Windows edition/build, Python and Codex CLI versions, standard-user status, source SHA and archive SHA-256; use a tester alias (no names, tokens, screenshots with private data).
3. In a clean profile, inspect the GUI, choose **preview**, verify that no files changed, inspect the exact AGENTS.md before/after diff.
4. With explicit authorization, apply to an isolated new profile; verify all four Skills and roles and managed global rules, then repeat the install to prove idempotence.
5. Test cancellation and rollback; confirm pre-existing AGENTS.md byte contents remain intact. Test a deliberately mismatched/stale source; it must **fail closed** without deleting unrelated user data.
6. If the tester has an authorized Codex account and independently opts in to quota use, run a separate read-only synthetic Skill case and four-role invocation; otherwise record **NOT_RUN** (do not simulate a PASS).
7. Capture sanitized pass/fail, timestamps, steps and versioned evidence hashes; document each failure and fix. Do not submit raw credentials, user profile data, or unredacted model logs.

## Optional scanner policy
SkillSpector is an optional manual third-party audit, **not** the release trigger. Code review, installer safety, provenance, privacy and real runtime acceptance remain requirements. The historical scanner reports are preserved.

## Release steps when verified
- Review main-branch integration and status checks.
- Dispatch `release-candidate.yml` on the exact reviewed `main` commit for deterministic source archive, attestation, exact signer verification.
- Dispatch `windows-gui-candidate.yml` on the exact reviewed `main` commit, verify EXE provenance and SHA-256, and record no Authenticode signature unless actually provided.
- Only after independent review and a fresh supported-host UAT, create the version tag and publish release assets with installation guide, rollback instructions and limitations.
