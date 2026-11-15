# Personal AI Workspace implementation plan — 2026-11-16

Baseline main 757eab9f677c2072a097d40f36f1e702e6c22c72. PR #14 merged as 8e2b5c5. Existing Python3.11 stdlib/Tk installer, transaction backups, reparse guards, public data bundling. No existing personal workspace/auth/sync implementation found. Working tree clean before new branch feat/personal-ai-workspace-20261116. User's full task is approved execution scope, not a design approval request.

## Constraints
- Only Mock API/isolated filesystem tests in this session. Never authenticate a new real account, create a real repository, push private user data, merge main, publish a release or deploy any production website.
- Default my-agent-workspace/private/manual; owner must equal active GitHub login. No AKA.CRISTI central private repository access.
- Existing source files retained. New modules with bounded subprocess/API calls and fixed safe error codes, no raw token/stderr logging.
- System credential storage required; reject plaintext fallback. gh browser OAuth is preferred over embedded client IDs/passwords. Document granted scope and gh prerequisite.
- Initialization exports ONLY the nine public allowlisted assets, not local AGENTS/private state/chat history/credentials. Every GitHub write has explicit confirmation.
- Sync is manual pull only, manifest content hashes + immutable source revision, own local account/repo selection, preflight conflict checks and owned local snapshots; no remote code execution.
- ChatGPT authorization is independent. No real verification provider means NOT_CONNECTED/PENDING/BLOCKED, never Connected on self-report or GH login alone.

## Agreed module contracts for concurrent implementation

### GitHub adapter — tools/workspace_github.py
- WorkspaceError(code: str): ValueError with .code safe fixed identifier.
- GhClient(config_dir: Path, executable='gh', timeout=30): managed private gh config namespace, no token arguments/env logging; reject ambiguous/unsafe paths and plaintext oauth_token fallback. Do not touch existing global gh config or keys.
- inspect_account() -> {'login': str, 'secure_storage': True}; connect(cancel_event=None, timeout=180) -> same. Only CLI --web authorization, no password prompt. cancel/timeout terminates child process safely. Do not execute live auth in this task.
- repo_info(owner: str, name: str) -> {'id', 'owner': str, 'name', 'full_name', 'private': bool, 'html_url', 'default_branch', 'permissions': {'push': bool}}; owner/private verification fail closed. Missing repo represented WorkspaceError('REPO_NOT_FOUND').
- create_private_repo(name: str, confirmed=False) -> verified repo info; existing repo must not be overwritten; existing handling belongs controller via explicit reuse.
- initialize_repo(owner,name,files: dict[str,str],confirmed=False) -> {'source_revision': str}; idempotent owned initialization, rejects modified/existing mismatches, private+owner checks, no silent overwrite. Validate allowed export paths and reject credentials. No write invoked in task except mock transports.
- fetch_snapshot(owner,name) -> {'manifest': dict, 'files': dict[str,bytes], 'source_revision': str}; fetch workspace.json + allowed payloads at exact commit, bounded downloads. No archive/shell execution. Manifest contract below. Root controller verifies selected owner matches active account too.

### Sync backend — tools/workspace_sync.py
- SyncEngine(state_dir: Path, codex_home: Path, skills_root: Path)
- preview(manifest: dict, files: dict[str,bytes], source_revision: str) -> plan dict with 'changes','conflicts','source_revision', private internal payload permitted. 'changes' entries path/action/diff strings. Unknown manifest/paths/hash mismatch fail closed.
- apply(plan: dict, confirmed=False) -> {'status', 'backup_id', 'source_revision'}; backups before any write, stale preview/conflicts refuse; no push. Backups/local state owner-only and never logged raw contents.
- backups() -> list of {'id','created_at','status'}; restore(backup_id: str,confirmed=False) -> safe result; refuse post-sync user changes; no blind rollback if concurrent changes.
- installed_skills() -> list of {'name','status'}; audit_log() -> list of sanitized fixed-event/status data. Audit never full paths/user content/exception messages/secrets.
- Manifest schema: {'schema_version':1,'owner':'login','repository':'my-agent-workspace','sync_mode':'manual','files':[{'path':'rules/AGENTS.md','target':'codex/AGENTS.md','sha256':64hex}, ...]}. Allow ONLY rules/AGENTS.md -> codex/AGENTS.md; agents/<safe>.toml -> codex/agents/<safe>.toml; skills/<safe-name>/<safe relative file> -> skills/<safe-name>/<same file>. Reject traversal/.env/auth/chats/symlinks/reparse/oversize/duplicate paths. Require nonempty allowlist. First differing unowned local file is CONFLICT, not overwritten; equal content can be adopted with backup. Later edits conflict; tracked matching files update. Do not delete unspecified/unrelated files.

### Root controller / CLI — tools/personal_workspace.py
- WorkspaceController(state_dir=None,codex_home=None,skills_root=None,source=None,client=None)
- status() -> {'github_account':str|null,'repository':str|null,'sync_status':str,'chatgpt_status':str,'sync_mode':'manual','wizard_needed':bool}
- connect(cancel_event=None), skip_setup(), select_repository(name='my-agent-workspace',confirmed=False,reuse=False), initialize(confirmed=False), check_updates(), preview_changes(), sync_now(confirmed=False), installed_skills(), backup_history(), restore_previous(backup_id,confirmed=False), error_logs(), repository_url(), chatgpt_guide(), request_chatgpt_verification().
- Root builds public initialization manifest. All writes require explicit consent independently of connect. Local settings contain no tokens. First-run skipped/done state atomic and recoverable. CLI preview default, explicit --apply/write flags, sanitized JSON only.

### GUI — tools/workspace_gui.py (adapter calls only controller contract)
- WorkspaceWindow(parent, controller=None, wizard=False), real Tk Notebook for Sync Center/GitHub setup/ChatGPT; background queue, cancel/timeouts, explicit repo creation/initialization/apply/restore confirmations; full diff local display only.
- Show all requested controls (account/repo/Codex/ChatGPT/skills/check updates/preview/sync/backups/restore/logs) with functional handlers, no fake success.
- Integrate into existing tools/gui_installer.py with a Personal AI Workspace button; main launches first-run wizard outside --smoke-test, after installation offer wizard. Existing tests/--smoke-test must stay read-only. Workspace GUI tests use isolated injected controller, not real auth.

## Validation and delivery
1. Baseline tests. Tests first per module: auth success/cancel/failure/timeout/plaintext refusal; repo create/reuse/private owner validation; init whitelist, content integrity and no writes absent consent; sync first/changed/conflict/retry/backup/restore/multi-machine on actual temp files; ChatGPT unverified/never fake Connected; real Tk controls under Windows runner/Xvfb.
2. Existing Windows installer regression and PyInstaller code bundling unchanged public-data allowlist. Add workspace GUI smoke to CI without OAuth/network/repo writes. Do not run release candidate workflows or production deploy.
3. Add lint/type checks scoped to new modules with pinned dev dependencies, appropriate remaining code style. Full unittest + compileall + chosen lint/typecheck and CI Windows/macOS/Linux.
4. Independent reviewer, resolve material findings, commit/push independent branch, Draft PR refs #14, artifact reports/CI URLs; README/install/ROADMAP and growth-record progress in branch only. Real Win11 standard user/auth/ChatGPT integration BLOCKED where not observed.

