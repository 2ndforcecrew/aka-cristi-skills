# Universal Agent Skills — installation-first delivery

The primary product is **installable Agent Skills**, not a Windows EXE or Web Dashboard.

## Included in this branch
- New `chef-control-center` portable Skill with `SKILL.md`, event protocol, and offline Python journal.
- Added to the existing shared `quick_install.SKILLS` registry used by Codex and the portable `universal_chef` installer.
- Existing four Skills remain unchanged. A user installing the default bundle receives five Skill packages.
- Existing installer behavior stays preview-first, conflict-safe and approval-gated. Installation does not launch agents, spend quota or imply native host activation.

## Honest capability boundaries
- Agent hosts: Codex, Claude Code, Gemini CLI, OpenCode, WorkBuddy/CodeBuddy, Hermes and generic hosts retain their existing adapter-specific limitations.
- The event journal is append-only local telemetry, **not** live Agent discovery, autonomous orchestration, executable retry or approval enforcement.
- The optional Web Dashboard in PR #50 is a separate experimental viewer, not a dependency of this Skill.
- A file-integrity test is not a real-host invocation test.

## Validation gates before merging
1. Python unit tests, installer tests, security checks and CI.
2. Clean install and upgrade on each supported adapter; verify existing custom config is preserved.
3. Host-native discovery and invocation acceptance, recorded separately for each actual Agent.
4. Review safe journal storage, permissions and data retention; ensure no private payloads are logged.
5. Update installer counts/docs and user onboarding language consistently before release.
