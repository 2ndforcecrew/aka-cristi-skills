# AKA.CRISTI Skills

**中文说明：** [功能介绍、安装教程与安全限制（简体中文）](docs/README.zh-CN.md)

**[🇨🇳 中文功能说明 / 安装指南](README.zh-CN.md)** · [English](README.md)

**FROM EXPERIENCE TO CAPABILITY.**

A curated public collection of reusable agent workflows and a safe, local-only Skill installer. This is separate from the **private** development repository; no internal rules, credentials, customer data, or private history are distributed here.

## Included Skills

| Skill | Purpose |
| --- | --- |
| [Verified Change Loop](skills/verified-change-loop/SKILL.md) | Reproduce → diagnose → minimum fix → replay → compare → handoff |
| [Feature Journey Map](skills/feature-journey-map/SKILL.md) | Map real entry, setup, user action, success and failure paths |
| [Skill Evaluation Gate](skills/skill-evaluation-gate/SKILL.md) | Evidence, independently reviewed results and approval boundaries |

These are methodology Skills, not third-party licensed packages. Some methods were adapted from user-supplied verification-engineering fieldnotes attributed to Lauren Tan; that attribution was not independently confirmed, and these are **not official third-party Skills**.

## Development candidate: six gates remain blocked

This branch advances Issues #8–#13. **It is not an approved release or an installation recommendation.** The original external 24-finding report is missing. A new exact-baseline SkillSpector 2.12.0 `--no-llm` scan returned **56 / DO_NOT_INSTALL / 23 findings**; these are separate observations. [Security review](docs/SECURITY_REVIEW_2026-11-15.md).

Default unauthenticated remote bootstrap is now blocked. A commit-pinned GitHub ZIP is not a verified signature. The PowerShell alternative accepts reviewed local source or an archive with independently pinned digest/commit and verified GitHub provenance. Unverified Codex installer scripts are never automatically executed.

For development in a reviewed local checkout with Python 3.11+, the real Tk graphical window can be opened with:

```sh
python -m tools.gui_installer
```

Windows also has `start-gui.cmd` for source use and a [standalone EXE candidate build](.github/workflows/windows-gui-candidate.yml). The build uses only nine public data files, real widget/EXE smoke tests and GitHub provenance; it has no Authenticode certificate. It shows a diff and explicit consent, backs up changes, verifies files, and supports guarded rollback. Dependency auto-install and clean Windows 11 external UAT remain BLOCKED. [GUI limitations](docs/WINDOWS_GUI.md).

Read [release verification](docs/RELEASE_VERIFICATION.md), [host capability matrix](docs/HOST_CAPABILITY_MATRIX.md), [external UAT](docs/EXTERNAL_UAT.md), and [strict runtime evidence](docs/FOUR_AGENT_EVIDENCE_V03.md). Claude support is currently project-scoped file installation only; Hermes/ChatGPT are BLOCKED. One actual cloud Codex attempt exited 1 without attributable threads; it did **not** pass four-role acceptance.

## Install on Codex (Windows 11, macOS, Linux)

Requirements: [Git](https://git-scm.com/downloads) and Python 3.11+. Open Terminal / PowerShell and run:

```sh
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills
python -m tools.skill_installer preview skills/verified-change-loop --target codex
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer verify verified-change-loop --target codex
```

The preview command is read-only; only the explicit `--apply` alters your local user Skill folder `~/.agents/skills`. **Install and file-integrity verification do not prove the agent has loaded or executed the Skill.** You may need to start a new Codex session; verify manually inside your target host.

Other Skills:

```sh
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

## Manage an installed Skill

```sh
python -m tools.skill_installer verify verified-change-loop --target codex
python -m tools.skill_installer rollback verified-change-loop --target codex --apply
python -m tools.skill_installer uninstall verified-change-loop --target codex --apply
```

- Upgrade: run the same install command using a newer version of the local source checkout. Existing managed version is backed up before replacing it.
- Uninstall: archives files rather than deleting them permanently. The installer does **not** overwrite unowned or locally edited Skills.
- Rollback requires a previous managed version backup; it is unavailable on a first-time installation.
- For isolated testing, use `--target directory --root ./test-agent-skills` instead of `--target codex`.

## Security & compatibility

- Only local directories are accepted. The installer does not fetch network code, execute Skill scripts, install dependencies, modify permissions, or upload secrets.
- Package validation rejects symlink entries and invalid frontmatter. This is **not a malware scanner, digital signature, or complete security review**; inspect Skills before installing.
- Current supported adapter: Codex user-scoped Agent Skills; custom folders are supported for sandbox tests. **Hermes, Claude, ChatGPT Plugins, other agent hosts and fully automatic activation are NOT verified.**
- Preview before applying, and do not run on untrusted sources.
- The established installer remains CLI-based; the development Tk GUI has a standalone candidate build pipeline but has no clean Windows 11 external UAT yet.

## Validation

```sh
python -m unittest discover -s tests -v
```

Tests cover preview, installation, upgrade, rollback, uninstall, conflicts and symlinks. See GitHub Actions for public repository CI results. These tests do not substitute for a real user's host activation test.

## Roadmap

Cross-platform host adapters, UX-friendly installation, package signing, reproducible releases, external user acceptance tests, and security review are planned, not delivered.

## Verify actual Codex Agent activation

Installing a Skill only verifies files were copied. To **prove one real Agent call**, run the isolated, read-only Codex activation test on a machine where Codex CLI is installed and signed in:

```powershell
codex login status
python -m tools.verify_codex_activation --skill verified-change-loop --out agent-activation-report.json
```

See [Real Agent Activation Verification](docs/AGENT_ACTIVATION_VERIFICATION.md) for the evaluation contract, other Skill names, and limitations. GitHub Actions only tests the verification machinery with synthetic traces; **it cannot verify a real Codex call without authorized Codex runtime access**. Live activation is NOT_RUN until separately observed.

## CHEF orchestration + global AGENTS.md (portable starter)

For the same **workflow principles** across Codex projects, install the sanitized public CHEF rules and orchestration Skill. This does not transfer anyone's private memories, repository permissions or third-party Agent connections.

```powershell
python -m tools.chef_global_rules preview
python -m tools.chef_global_rules install --apply
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
```

The global installer **appends an owned section** to `~/.codex/AGENTS.md` or `CODEX_HOME/AGENTS.md`, without replacing existing rules. You can safely uninstall only the managed section using `python -m tools.chef_global_rules uninstall --apply`.

Read [CHEF Global Rules + Multi-Agent Starter](docs/CHEF_GLOBAL_AND_MULTIAGENT.md) for setup, safe rollback, real Agent verification and the distinction between orchestration policy and actual connected worker agents.

## CHEF V0.2: native Codex multi-agent roles

After installing the CHEF global rules and Skill, you can also add four **native Codex custom subagents**: `aka_research`, `aka_coding`, `aka_qa`, and `aka_automation`.

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

This operation manages only the installer-owned TOMLs in `~/.codex/agents` (or `$CODEX_HOME/agents`). It never replaces existing unowned agents or changes `config.toml`. **Installation does not prove any subagent was spawned.** Open a fresh Codex session and run a read-only handoff test with evidence of actual subagent threads.

[Installation, safety and real Agent verification instructions](docs/CODEX_NATIVE_SUBAGENTS_V02.md).

## Actual four-Agent runtime acceptance (Codex)

Configuration and CI unit tests alone do not prove native Subagents were spawned. For a signed-in Codex CLI, use the **strict live probe**:

```powershell
python -m tools.codex_subagents install --apply
codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

The live probe requests `aka_research`, `aka_coding`, `aka_qa`, and `aka_automation` on a synthetic read-only task. It checks **actual** root/child rollout records; it rejects role-label-only simulations. No Codex login on this machine yields `NOT_RUN`, not PASS. See [four-Agent runtime acceptance](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md).
