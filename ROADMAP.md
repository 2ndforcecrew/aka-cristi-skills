# Development roadmap

Existing gates [#8–#13](docs/SIX_GATE_STATUS.md) remain open. A new feature does not bypass security, release or independent acceptance requirements.

## Personal AI Workspace — implementation branch

- [x] Read-only first-run inspection, skip/resume setup and existing GUI integration.
- [x] Device authorization transport with native-only credential storage and explicit OAuth public client-ID configuration.
- [x] Own-account private repository validation, explicit create/reuse/init consent and public-only initialization; exercised with Mock API only.
- [x] Immutable-revision manual pull, conflict detection, pre-write private backups, restore/retry and cross-profile destination locks; real temporary filesystem tests.
- [x] Sync Center controls and independent ChatGPT connection guidance without fake Connected.
- [x] Pinned runtime/dev requirements and Windows EXE dependency inclusion.
- [ ] Feature-branch CI / Windows EXE checks — evidence tracked in Draft PR.
- [ ] Register/configure a real OAuth App and independently verify native keyring + OAuth on Windows/macOS/Linux.
- [ ] Independent clean Windows 11 standard-user install, second launch, proxy/permission/restore tests.
- [ ] Explicitly authorized future real private-repository create/read/write acceptance; forbidden in this development session.
- [ ] Trusted ChatGPT authorization verification adapter; current guide remains PENDING/NOT_CONNECTED.
- [ ] Release/security review, signed distributable and user acceptance. No automatic release, merge or production deployment.

See [implementation and installation](docs/PERSONAL_AI_WORKSPACE.md), [plan](docs/plans/2026-11-16-personal-ai-workspace.md) and the new growth record. Historical files are retained.
