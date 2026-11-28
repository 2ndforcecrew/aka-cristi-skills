# AKA.CRISTI Skills — Release acceptance checklist (Codex-first)

Status: **v1.0.0-beta.2 PRE-RELEASE PUBLISHED** (not stable). Build, manifest and GitHub provenance checks passed for [beta.2](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2). Independent external UAT, Authenticode and real four-agent acceptance remain separate open requirements. Record exact candidate SHA, CI run links, SHA-256 and signatures; never substitute a prior commit's artifact or synthetic test for current release evidence.

## v1.0 supported surface
- Codex-first installer with four methodology Skills, global managed AGENTS.md, and four Codex role definitions.
- CLI and Windows GUI local-file preview, explicit consent, guarded apply, verify and rollback.
- Windows Job Object timeout containment has actual Windows regression evidence but is **not** an OS permission or MCP sandbox.
- Personal AI Workspace OAuth, account creation, synchronization, cross-vendor live activation and fully automated cross-agent orchestration are **experimental / NOT VERIFIED** until real end-to-end acceptance; do not advertise these as stable or automatically connected.

## Beta distribution comes BEFORE external UAT

**No circular gate:** It is valid to distribute an explicitly labelled **Pre-release / Beta** for independent Windows 11 installation testing. Successful external UAT is a **stable-release** requirement, not a prerequisite for getting the Beta into testers' hands.

Beta entry conditions:
1. Reviewed exact candidate commit and successful platform CI; no known unmitigated critical installer/credential exposure risk.
2. Windows EXE/source archive built from the exact approved SHA; publish independently verified SHA-256 and GitHub OIDC provenance, with an honest **NOT Authenticode signed** notice.
3. A GitHub Pre-release page, versioned test instructions, expected limitations and a bug-report channel; prefer a test profile or disposable Windows 11 VM.
4. Explicitly describe Codex role activation, OAuth workspace, ChatGPT/Hermes/Claude and third-party service integration as not guaranteed where actual acceptance is missing.
5. Collect independent results, fix reported defects, then run a newly signed release candidate and final stable readiness review.

Do not call a Beta "stable", fabricate signatures, copy a previously signed artifact to a changed commit, or disable local integrity safeguards.

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
| Public GitHub Pre-release | beta.2 tag and assets; README caveats and provenance attached | PUBLISHED (BETA); stable release NOT_PUBLISHED |

## Residual risks (§5.3)

Per §5.3 of the scan-triage plan (`plan-scan-triage-20261124.md`), the following three residual risks are disclosed as-is. They supplement — not repeat — the statements already in this document: the v1.0 surface note that Windows Job Object timeout containment "is not an OS permission or MCP sandbox", and the Credential/MCP scope checklist row ("preflight implemented; live acceptance pending"). Those statements do not spell out the three items below:

1. **No OS-level network/filesystem sandbox.** `tools/codex_probe_isolation.py` states in its own docstring that it does not provide filesystem/network OS sandboxing. `--sandbox read-only` is a Codex CLI sandbox parameter, not OS-enforced isolation. A real agent can still read files outside the workspace and reach the network (unless the CLI itself restricts it). This item cannot be turned into "isolated" on the basis of the existing evidence.
2. **MCP isolation completeness depends on CLI behaviour.** Preflight only inspects the `config.toml` in the dedicated home. Whether the CLI also reads MCP registrations from other locations (e.g. project-level `.codex/`, other global configuration sources, or MCP specified via environment variables) is not covered by preflight. The canary method (E-247-5) is behavioural evidence, not a completeness proof.
3. **POSIX descendant state after timeout is unconfirmed on the verify_* path.** Windows is covered by WP-B/WP-C. On Linux/macOS, the descendant state after a verify_* timeout remains NOT_VERIFIED until equivalent experiments are run on the corresponding platforms.

**Gate status:** #247/#250 remain BLOCKED until every item of the §5 evidence package is checked off. D2 live-machine evidence E-247-4 through E-247-8 is currently all NOT_VERIFIED.

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
