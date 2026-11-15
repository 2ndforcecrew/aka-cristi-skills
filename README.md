# AKA.CRISTI Skills

**FROM EXPERIENCE TO CAPABILITY.**

A curated public collection of reusable agent workflows and a safe, local-only Skill installer. This is separate from the **private** development repository; no internal rules, credentials, customer data, or private history are distributed here.

## Included Skills

| Skill | Purpose |
| --- | --- |
| [Verified Change Loop](skills/verified-change-loop/SKILL.md) | Reproduce → diagnose → minimum fix → replay → compare → handoff |
| [Feature Journey Map](skills/feature-journey-map/SKILL.md) | Map real entry, setup, user action, success and failure paths |
| [Skill Evaluation Gate](skills/skill-evaluation-gate/SKILL.md) | Evidence, independently reviewed results and approval boundaries |

These are methodology Skills, not third-party licensed packages. Some methods were adapted from user-supplied verification-engineering fieldnotes attributed to Lauren Tan; that attribution was not independently confirmed, and these are **not official third-party Skills**.

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
- This initial release is CLI-based, **not a one-click graphical installer**.

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
