"""Personal workspace controller and CLI. No automatic remote writes or push.

Settings contain public identifiers only. OAuth tokens belong to the native OS
credential store. Live account/repository operations are explicit GUI/CLI actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools.fs_safety import checked_path
from tools.workspace_auth import AuthClient
from tools.workspace_github import GhClient, WorkspaceError, validate_manifest
from tools.workspace_lock import LockBusy, exclusive_lock
from tools.workspace_oneclick import OneClickSetup
from tools.workspace_sync import SyncEngine

DEFAULT_REPOSITORY = 'my-agent-workspace'
CHATGPT_GUIDE = 'https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt-deep-resear'
PUBLIC_FILES = {
    'rules/AGENTS.md': 'templates/AGENTS.global.md',
    **{f'agents/{name}.toml': f'agents/{name}.toml' for name in ('research', 'coding', 'qa', 'automation')},
    **{f'skills/{name}/SKILL.md': f'skills/{name}/SKILL.md' for name in (
        'chef-orchestrator', 'verified-change-loop', 'feature-journey-map', 'skill-evaluation-gate')},
}
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
SAFE_ERRORS = frozenset({
    'OAUTH_CLIENT_ID_REQUIRED', 'OAUTH_CLIENT_ID_INVALID', 'NOT_CONNECTED',
    'AUTH_CANCELLED', 'AUTH_TIMEOUT', 'AUTH_DENIED', 'AUTH_EXPIRED', 'AUTH_FAILED',
    'SECURE_STORAGE_REQUIRED', 'NETWORK_ERROR', 'REPO_NOT_FOUND', 'REUSE_REQUIRED', 'REPO_NOT_PRIVATE',
    'OWNER_MISMATCH', 'PERMISSION_DENIED', 'ACCOUNT_CHANGED', 'API_CONFLICT',
    'MANIFEST_INVALID', 'HASH_MISMATCH', 'CONFLICT', 'PREVIEW_REQUIRED',
    'STALE_REMOTE_PREVIEW', 'STALE_PREVIEW', 'SOURCE_INVALID', 'SETTINGS_INVALID',
    'SETTINGS_CHANGED', 'REPOSITORY_REQUIRED', 'NAME_INVALID', 'CENTRAL_REPOSITORY_FORBIDDEN',
    'CONFIRMATION_REQUIRED', 'OPERATION_FAILED', 'SYNC_CONFLICT',
    'SECURE_STORAGE_FAILED', 'INVALID_CREDENTIAL', 'HTTP_401', 'HTTP_403',
    'AUTH_REQUIRED', 'AUTHENTICATION_REQUIRED', 'BROWSER_OPEN_FAILED',
    'CHALLENGE_DISPLAY_FAILED', 'REDIRECT_REFUSED', 'INVALID_RESPONSE',
    'DISCONNECT_UNAVAILABLE', 'FILESYSTEM_ERROR', 'ROLLBACK_CONFLICT',
    'LOCK_BUSY', 'STALE_PLAN', 'INVALID_PLAN', 'BACKUP_INTEGRITY',
})


def _error(code: str) -> WorkspaceError:
    return WorkspaceError(code)


def _atomic_json(path: Path, value: Any) -> None:
    checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        os.chmod(path.parent, 0o700)
    fd, staged = tempfile.mkstemp(prefix='.workspace-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write('\n')
        os.replace(staged, path)
    finally:
        if os.path.exists(staged):
            os.unlink(staged)


class WorkspaceController:
    def __init__(self, state_dir: Path | None = None, codex_home: Path | None = None,
                 skills_root: Path | None = None, source: Path | None = None,
                 client: Any = None):
        self.state_dir = checked_path(state_dir or Path.home() / '.aka-personal-workspace')
        self.codex_home = checked_path(codex_home or os.environ.get('CODEX_HOME') or Path.home() / '.codex')
        self.skills_root = checked_path(skills_root or Path.home() / '.agents' / 'skills')
        roots = (self.state_dir, self.codex_home, self.skills_root)
        if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(roots) for b in roots[i + 1:]):
            raise _error('SETTINGS_INVALID')
        self.source = checked_path(source or Path(__file__).resolve().parents[1])
        self._settings_path = checked_path(self.state_dir / 'settings.json')
        self._settings = self._load_settings()
        self._external_client = client is not None
        self.client = client if client is not None else self._new_client()
        self._account: dict[str, Any] | None = None
        self._plan: dict[str, Any] | None = None
        self._engines: dict[str, SyncEngine] = {}
        self._sync_status = 'NOT_RUN'
        self._mutex = threading.RLock()

    def _new_client(self) -> GhClient:
        config = self.state_dir / 'auth'
        return GhClient(config, auth=AuthClient(config, client_id=self._settings.get('oauth_client_id') or None))

    def _load_settings(self) -> dict[str, Any]:
        default = {'schema_version': 1, 'setup_seen': False, 'owner': None,
                   'repository': None, 'oauth_client_id': '', 'chatgpt_requested': False}
        if not self._settings_path.exists():
            return default
        try:
            if self._settings_path.stat().st_size > 16 * 1024:
                raise ValueError()
            value = json.loads(self._settings_path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or set(value) != set(default) or value['schema_version'] != 1:
                raise ValueError()
            if type(value['setup_seen']) is not bool or type(value['chatgpt_requested']) is not bool:
                raise ValueError()
            for key, pattern in (('owner', LOGIN), ('repository', NAME)):
                if value[key] is not None and (not isinstance(value[key], str) or not pattern.fullmatch(value[key])):
                    raise ValueError()
            self._client_id(value['oauth_client_id'])
            if (value['repository'] or '').casefold() == 'aka-cristi-agent-rules':
                raise ValueError()
            return value
        except (OSError, ValueError, TypeError):
            raise _error('SETTINGS_INVALID') from None

    def _save(self, **changes: Any) -> None:
        # No stale process may silently replace another process's selection.
        checked_path(self.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        lock = checked_path(self.state_dir / 'settings.lock')
        try:
            with exclusive_lock(lock):
                if self._load_settings() != self._settings:
                    raise _error('SETTINGS_CHANGED')
                value = {**self._settings, **changes}
                _atomic_json(self._settings_path, value)
                self._settings = value
        except LockBusy:
            raise _error('SETTINGS_CHANGED') from None

    def _audit(self, event: str, code: str) -> None:
        # Audit writes are best-effort and contain no exception text or content.
        safe_code = code if code in SAFE_ERRORS else 'OPERATION_FAILED'
        path = checked_path(self.state_dir / 'events.json')
        events: list[Any] = []
        try:
            if path.exists() and path.stat().st_size <= 128 * 1024:
                obj = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(obj, list):
                    events = [{'event': 'WORKSPACE_ERROR', 'code': entry['code']}
                              for entry in obj if isinstance(entry, dict) and entry.get('code') in SAFE_ERRORS][-99:]
            events.append({'event': event, 'code': safe_code, 'at': datetime.now(timezone.utc).isoformat()})
            _atomic_json(path, events)
        except (OSError, ValueError):
            pass

    def _operation(self, name: str, action: Callable[[], Any]) -> Any:
        with self._mutex:
            try:
                with exclusive_lock(self.state_dir / 'operation.lock'):
                    if self._load_settings() != self._settings:
                        raise _error('SETTINGS_CHANGED')
                    return action()
            except LockBusy:
                raise _error('SETTINGS_CHANGED') from None
            except Exception as exc:
                code = getattr(exc, 'code', 'OPERATION_FAILED')
                code = code if code in SAFE_ERRORS else 'OPERATION_FAILED'
                self._audit(name, code)
                raise _error(code) from None

    @staticmethod
    def _client_id(value: Any) -> str:
        if not isinstance(value, str) or len(value) > 100 or (value and not re.fullmatch(r'[A-Za-z0-9._-]+', value)):
            raise _error('OAUTH_CLIENT_ID_INVALID')
        if re.match(r'(?i)(gh[pousr]_|github_pat_|sk-|Bearer)', value):
            raise _error('OAUTH_CLIENT_ID_INVALID')
        return value

    def configure_oauth_client(self, client_id: str) -> dict[str, Any]:
        value = self._client_id(client_id.strip())
        def action() -> dict[str, Any]:
            self._save(oauth_client_id=value)
            if not self._external_client:
                self.client = self._new_client()
            self._account = None
            self._plan = None
            return {'status': 'CONFIGURED', 'credential_storage': 'NATIVE_OS_REQUIRED'}
        return self._operation('CONFIGURE_OAUTH', action)

    def status(self) -> dict[str, Any]:
        owner, repo = self._settings['owner'], self._settings['repository']
        return {'github_account': self._account['login'] if self._account else None,
                'repository': f'{owner}/{repo}' if owner and repo else None,
                'sync_status': self._sync_status, 'sync_mode': 'manual',
                'chatgpt_status': 'PENDING_VERIFICATION' if self._settings['chatgpt_requested'] else 'NOT_CONNECTED',
                'wizard_needed': not self._settings['setup_seen'],
                'oauth_client_configured': bool(self._settings['oauth_client_id'] or os.environ.get('AKA_WORKSPACE_OAUTH_CLIENT_ID'))}

    def _inspect(self) -> dict[str, Any]:
        account = self.client.inspect_account()
        if not isinstance(account, dict) or not LOGIN.fullmatch(str(account.get('login', ''))) or account.get('secure_storage') is not True:
            raise _error('NOT_CONNECTED')
        self._account = account
        return account

    def connect(self, cancel_event: threading.Event | None = None,
                on_challenge: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            try:
                account = self._inspect()
            except Exception as exc:
                # A failed identity/network check must not trigger a second grant.
                code = getattr(exc, 'code', '')
                if code not in ('NOT_CONNECTED', 'AUTH_REQUIRED', 'TOKEN_MISSING', 'HTTP_401', 'INVALID_CREDENTIAL'):
                    raise
                account = self.client.connect(cancel_event=cancel_event, on_challenge=on_challenge)
                if not isinstance(account, dict) or account.get('secure_storage') is not True or not LOGIN.fullmatch(str(account.get('login', ''))):
                    raise _error('NOT_CONNECTED')
                self._account = account
            changed = self._settings['owner'] not in (None, account['login'])
            self._save(owner=account['login'], repository=None if changed else self._settings['repository'], setup_seen=True)
            self._plan = None
            return {'status': 'CONNECTED', 'login': account['login'], 'secure_storage': True}
        return self._operation('CONNECT', action)

    def disconnect(self, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            raise _error('CONFIRMATION_REQUIRED')
        def action() -> dict[str, Any]:
            auth = getattr(self.client, 'auth', None)
            if auth is None or not callable(getattr(auth, 'disconnect', None)):
                raise _error('DISCONNECT_UNAVAILABLE')
            auth.disconnect()  # Deletes only this app's native credential namespace.
            self._account = None
            self._plan = None
            self._save(owner=None, repository=None, setup_seen=False)
            self._sync_status = 'NOT_RUN'
            return {'status': 'DISCONNECTED'}
        return self._operation('DISCONNECT', action)

    def skip_setup(self) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            self._save(setup_seen=True)
            return {'status': 'SKIPPED', 'sync_mode': 'manual'}
        return self._operation('SKIP_SETUP', action)

    def _repo(self) -> dict[str, Any]:
        account = self._inspect()
        if self._settings['owner'] != account['login']:
            raise _error('ACCOUNT_CHANGED')
        name = self._settings['repository']
        if not name:
            raise _error('REPOSITORY_REQUIRED')
        if name.casefold() == 'aka-cristi-agent-rules':
            raise _error('CENTRAL_REPOSITORY_FORBIDDEN')
        return self._verified_repo(self.client.repo_info(account['login'], name), account['login'], name)

    @staticmethod
    def _verified_repo(repo: Any, owner: str, name: str) -> dict[str, Any]:
        if (not isinstance(repo, dict) or repo.get('owner') != owner or repo.get('name') != name
                or repo.get('full_name') != f'{owner}/{name}'):
            raise _error('OWNER_MISMATCH')
        if repo.get('private') is not True or repo.get('permissions', {}).get('push') is not True:
            raise _error('REPO_NOT_PRIVATE')
        if repo.get('html_url') != f'https://github.com/{owner}/{name}':
            raise _error('OWNER_MISMATCH')
        return repo

    def select_repository(self, name: str = DEFAULT_REPOSITORY, confirmed: bool = False,
                          reuse: bool = False) -> dict[str, Any]:
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in ('.', '..'):
            raise _error('NAME_INVALID')
        if name.casefold() == 'aka-cristi-agent-rules':
            raise _error('CENTRAL_REPOSITORY_FORBIDDEN')
        def action() -> dict[str, Any]:
            account = self._inspect()
            try:
                repo = self.client.repo_info(account['login'], name)
            except Exception as exc:
                if getattr(exc, 'code', None) != 'REPO_NOT_FOUND':
                    raise
                if reuse:
                    raise _error('REPO_NOT_FOUND') from None
                if not confirmed:
                    return {'status': 'CONFIRM_CREATE_REQUIRED', 'name': name, 'private': True}
                repo = self.client.create_private_repo(name, confirmed=True)
            else:
                self._verified_repo(repo, account['login'], name)
                if not reuse or not confirmed:
                    return {'status': 'REUSE_REQUIRED', 'name': name, 'private': True}
            repo = self._verified_repo(repo, account['login'], name)
            self._save(owner=account['login'], repository=name, setup_seen=True)
            self._plan = None
            self._sync_status = 'NOT_RUN'
            return {'status': 'SELECTED', 'repository': repo['full_name'], 'private': True}
        return self._operation('SELECT_REPOSITORY', action)

    def initialize(self, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            raise _error('CONFIRMATION_REQUIRED')
        def action() -> dict[str, Any]:
            repo = self._repo()
            files: dict[str, str] = {}
            entries = []
            for exported, relative in PUBLIC_FILES.items():
                path = checked_path(self.source / relative)
                if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                    raise _error('SOURCE_INVALID')
                content = path.read_bytes()
                files[exported] = content.decode('utf-8')
                target = 'codex/AGENTS.md' if exported == 'rules/AGENTS.md' else (
                    'codex/' + exported if exported.startswith('agents/') else exported)
                entries.append({'path': exported, 'target': target, 'sha256': hashlib.sha256(content).hexdigest()})
            manifest = {'schema_version': 1, 'owner': repo['owner'], 'repository': repo['name'],
                        'sync_mode': 'manual', 'files': entries}
            validate_manifest(manifest, repo['owner'], repo['name'])
            files['workspace.json'] = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
            result = self.client.initialize_repo(repo['owner'], repo['name'], files, confirmed=True)
            self._plan = None
            return {'status': 'INITIALIZED', 'files': len(files), **result}
        return self._operation('INITIALIZE', action)

    def _engine(self) -> SyncEngine:
        owner, repo = self._settings['owner'], self._settings['repository']
        if not owner or not repo:
            raise _error('REPOSITORY_REQUIRED')
        key = hashlib.sha256(f'{owner}/{repo}'.casefold().encode()).hexdigest()
        if key not in self._engines:
            self._engines[key] = SyncEngine(self.state_dir / 'sync' / key, self.codex_home, self.skills_root)
        return self._engines[key]

    def _snapshot(self) -> dict[str, Any]:
        repo = self._repo()
        value = self.client.fetch_snapshot(repo['owner'], repo['name'])
        validate_manifest(value['manifest'], repo['owner'], repo['name'])
        return value

    def check_updates(self) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            snapshot = self._snapshot()
            plan = self._engine().preview(**snapshot)
            return {'status': 'CHECKED', 'source_revision': snapshot['source_revision'],
                    'changes': len([c for c in plan['changes'] if c['action'] not in ('UNCHANGED', 'ADOPT')]),
                    'conflicts': len(plan['conflicts']), 'sync_mode': 'manual'}
        return self._operation('CHECK_UPDATES', action)

    def preview_changes(self) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            self._plan = self._engine().preview(**self._snapshot())
            self._sync_status = 'CONFLICT' if self._plan['conflicts'] else 'PREVIEW_READY'
            return self._plan
        return self._operation('PREVIEW', action)

    def sync_now(self, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            raise _error('CONFIRMATION_REQUIRED')
        def action() -> dict[str, Any]:
            if self._plan is None:
                raise _error('PREVIEW_REQUIRED')
            latest = self._snapshot()
            if latest['source_revision'] != self._plan['source_revision']:
                raise _error('STALE_REMOTE_PREVIEW')
            if self._plan['conflicts']:
                raise _error('SYNC_CONFLICT')
            result = self._engine().apply(self._plan, confirmed=True)
            self._sync_status = result['status']
            self._plan = None
            return result
        return self._operation('SYNC', action)

    def installed_skills(self) -> list[dict[str, Any]]:
        if not self._settings['repository']:
            return []
        return self._engine().installed_skills()

    def backup_history(self) -> list[dict[str, Any]]:
        return self._engine().backups() if self._settings['repository'] else []

    def restore_previous(self, backup_id: str, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            raise _error('CONFIRMATION_REQUIRED')
        def action() -> dict[str, Any]:
            result = self._engine().restore(backup_id, confirmed=True)
            self._sync_status = result['status']
            self._plan = None
            return result
        return self._operation('RESTORE', action)

    def error_logs(self) -> list[dict[str, Any]]:
        path = checked_path(self.state_dir / 'events.json')
        try:
            events = json.loads(path.read_text(encoding='utf-8')) if path.is_file() and path.stat().st_size <= 128 * 1024 else []
            # Never echo arbitrary edited event fields back into a public report.
            return [{'event': 'WORKSPACE_ERROR', 'code': event['code']} for event in events
                    if isinstance(event, dict) and event.get('code') in SAFE_ERRORS][-100:]
        except (OSError, ValueError, TypeError):
            return []

    def repository_url(self) -> str:
        return str(self._repo()['html_url'])

    def chatgpt_guide(self) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            self._save(chatgpt_requested=True)
            return {'url': CHATGPT_GUIDE, 'status': 'PENDING_VERIFICATION',
                    'steps': ['在自己的 ChatGPT 设置中打开 GitHub App/Plugin 并授权自己的账号。',
                              '仅选择自己的 my-agent-workspace 私人仓库。',
                              '在支持 GitHub 的 ChatGPT 会话实际读取该仓库，并单独保留验证证据。'],
                    'limitation': '本地安装器没有可信的 ChatGPT 授权回调，不能自动证明连接或修改 Memory/内部 Skills。'}
        return self._operation('CHATGPT_GUIDE', action)

    def request_chatgpt_verification(self) -> dict[str, Any]:
        return {'status': 'PENDING_VERIFICATION' if self._settings['chatgpt_requested'] else 'NOT_CONNECTED',
                'verification': 'BLOCKED_NO_TRUSTED_CHATGPT_CALLBACK',
                'connected': False, 'authorization_required': True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Personal AI Workspace: manual pull, explicit writes only')
    parser.add_argument('action', choices=['status', 'connect', 'skip', 'select', 'initialize', 'check',
                                         'preview', 'sync', 'skills', 'backups', 'restore', 'logs',
                                         'repository-url', 'chatgpt-guide', 'chatgpt-verify', 'configure-oauth', 'disconnect',
                                         'one-click'])
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--codex-home', type=Path)
    parser.add_argument('--skills-root', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--name', default=DEFAULT_REPOSITORY)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup-id')
    parser.add_argument('--oauth-client-id', default='')
    args = parser.parse_args(argv)
    try:
        controller = WorkspaceController(args.state_dir, args.codex_home, args.skills_root, args.source)
        commands: dict[str, Callable[[], Any]] = {
            'disconnect': lambda: controller.disconnect(args.apply),
            'status': controller.status, 'connect': lambda: controller.connect(on_challenge=_cli_challenge), 'skip': controller.skip_setup,
            'select': lambda: controller.select_repository(args.name, args.apply, args.reuse),
            'initialize': lambda: controller.initialize(args.apply), 'check': controller.check_updates,
            'preview': lambda: _public_plan(controller.preview_changes()),
            # CLI sync obtains and prints a fresh preview but requires --apply to write.
            'sync': lambda: _cli_sync(controller, args.apply), 'skills': controller.installed_skills,
            'backups': controller.backup_history,
            'restore': lambda: controller.restore_previous(args.backup_id or '', args.apply),
            'logs': controller.error_logs, 'repository-url': controller.repository_url,
            'chatgpt-guide': controller.chatgpt_guide, 'chatgpt-verify': controller.request_chatgpt_verification,
            'configure-oauth': lambda: controller.configure_oauth_client(args.oauth_client_id),
            'one-click': lambda: _cli_one_click(controller, args.apply),
        }
        result = commands[args.action]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # A one-click partial failure must not look successful to CI or agents.
        if args.action == "one-click" and isinstance(result, dict) and result.get("status") == "STOPPED":
            return 2
        return 0
    except Exception as exc:
        code = getattr(exc, 'code', 'OPERATION_FAILED')
        print(json.dumps({'status': 'BLOCKED', 'code': code if code in SAFE_ERRORS else 'OPERATION_FAILED'}))
        return 2


def _cli_one_click(controller: WorkspaceController, apply: bool) -> dict[str, Any]:
    # Without --apply only the enumerated writes are printed; nothing is written.
    setup = OneClickSetup(controller)
    if not apply:
        return setup.plan()
    return setup.run(confirmed=True)


def _cli_challenge(challenge: dict[str, Any]) -> None:
    # User code is intentionally shown to the person authorizing, never audited.
    uri, code = challenge.get('verification_uri'), challenge.get('user_code')
    if uri == 'https://github.com/login/device' and isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9-]{1,32}', code):
        print(f'GitHub device authorization: {uri}  user code: {code}', file=sys.stderr)


def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {key: plan[key] for key in ('changes', 'conflicts', 'source_revision')}


def _cli_sync(controller: WorkspaceController, apply: bool) -> dict[str, Any]:
    plan = controller.preview_changes()
    if not apply:
        return {'status': 'PREVIEW_ONLY', **_public_plan(plan)}
    return controller.sync_now(confirmed=True)


if __name__ == '__main__':
    raise SystemExit(main())
