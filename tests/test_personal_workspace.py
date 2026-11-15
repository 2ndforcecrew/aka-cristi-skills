"""Controller integration: Mock GitHub, real public assets and temporary files."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    from tools.personal_workspace import WorkspaceController, WorkspaceError
except ImportError:
    WorkspaceController = None
    WorkspaceError = ValueError


class FakeGitHub:
    def __init__(self):
        self.login = 'alice'
        self.repositories = {}
        self.remote_files = {}
        self.writes = []
        self.revision = 'a' * 40

    def inspect_account(self):
        return {'login': self.login, 'secure_storage': True}

    def connect(self, **kwargs):
        return self.inspect_account()

    def repo_info(self, owner, name):
        from tools.workspace_github import WorkspaceError as ApiError
        if name not in self.repositories:
            raise ApiError('REPO_NOT_FOUND')
        return copy.deepcopy(self.repositories[name])

    def create_private_repo(self, name, confirmed=False):
        assert confirmed
        self.writes.append(('create', name))
        repo = {'id': 1, 'owner': self.login, 'name': name,
                'full_name': self.login + '/' + name, 'private': True,
                'html_url': 'https://github.com/' + self.login + '/' + name,
                'default_branch': 'main', 'permissions': {'push': True}}
        self.repositories[name] = repo
        return copy.deepcopy(repo)

    def initialize_repo(self, owner, name, files, confirmed=False):
        assert confirmed
        self.writes.append(('initialize', name))
        self.remote_files = {p: text.encode('utf-8') for p, text in files.items()}
        return {'source_revision': self.revision}

    def fetch_snapshot(self, owner, name):
        from tools.workspace_github import WorkspaceError as ApiError
        if not self.remote_files:
            raise ApiError('REPO_NOT_FOUND')
        return {'manifest': json.loads(self.remote_files['workspace.json']),
                'files': {k: v for k, v in self.remote_files.items() if k != 'workspace.json'},
                'source_revision': self.revision}


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(WorkspaceController, 'workspace controller must exist')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.client = FakeGitHub()
        self.options = {'state_dir': self.base / 'state', 'codex_home': self.base / 'codex',
                        'skills_root': self.base / 'skills', 'client': self.client,
                        'source': Path(__file__).resolve().parents[1]}
        self.controller = WorkspaceController(**self.options)

    def prepare(self):
        self.controller.connect()
        self.controller.select_repository(confirmed=True)
        self.controller.initialize(confirmed=True)

    def test_first_run_skip_and_restart_remember_without_auto_writes(self):
        self.assertTrue(self.controller.status()['wizard_needed'])
        self.assertFalse(self.options['state_dir'].exists())
        self.controller.skip_setup()
        again = WorkspaceController(**self.options)
        self.assertFalse(again.status()['wizard_needed'])
        self.assertEqual(self.client.writes, [])

    def test_create_requires_separate_confirmation_and_own_private_identity(self):
        self.controller.connect()
        result = self.controller.select_repository()
        self.assertEqual(result['status'], 'CONFIRM_CREATE_REQUIRED')
        self.assertEqual(self.client.writes, [])
        self.controller.select_repository(confirmed=True)
        self.assertEqual(self.controller.status()['repository'], 'alice/my-agent-workspace')
        self.assertEqual(self.controller.repository_url(), 'https://github.com/alice/my-agent-workspace')
        self.assertEqual(self.client.writes, [('create', 'my-agent-workspace')])

    def test_existing_repo_needs_explicit_reuse(self):
        self.client.create_private_repo('my-agent-workspace', confirmed=True)
        self.client.writes.clear()
        self.controller.connect()
        self.assertEqual(self.controller.select_repository(confirmed=True)['status'], 'REUSE_REQUIRED')
        self.controller.select_repository(reuse=True, confirmed=True)
        self.assertEqual(self.client.writes, [])

    def test_public_foreign_and_central_repo_are_refused(self):
        self.controller.connect()
        self.client.create_private_repo('my-agent-workspace', confirmed=True)
        repo = self.client.repositories['my-agent-workspace']
        repo['private'] = False
        with self.assertRaises(WorkspaceError):
            self.controller.select_repository(reuse=True, confirmed=True)
        repo['private'] = True
        repo['owner'] = 'other'
        with self.assertRaises(WorkspaceError):
            self.controller.select_repository(reuse=True, confirmed=True)
        with self.assertRaises(WorkspaceError):
            self.controller.select_repository(name='aka-cristi-agent-rules', confirmed=True)

    def test_initialization_is_public_allowlist_not_local_private_file(self):
        self.options['codex_home'].mkdir()
        (self.options['codex_home'] / 'AGENTS.md').write_text('PRIVATE LOCAL CHAT CONTENT')
        self.controller.connect()
        self.controller.select_repository(confirmed=True)
        with self.assertRaises(WorkspaceError):
            self.controller.initialize()
        self.controller.initialize(confirmed=True)
        self.assertEqual(len(self.client.remote_files), 10)
        self.assertNotIn(b'PRIVATE LOCAL CHAT CONTENT', b'\n'.join(self.client.remote_files.values()))
        manifest = json.loads(self.client.remote_files['workspace.json'])
        self.assertEqual(manifest['owner'], 'alice')
        self.assertEqual(manifest['sync_mode'], 'manual')
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256(self.client.remote_files[item['path']]).hexdigest(), item['sha256'])

    def test_preview_and_real_filesystem_sync_restore(self):
        self.prepare()
        plan = self.controller.preview_changes()
        self.assertFalse(self.options['codex_home'].exists())
        self.assertFalse(plan['conflicts'])
        with self.assertRaises(WorkspaceError):
            self.controller.sync_now()
        result = self.controller.sync_now(confirmed=True)
        self.assertEqual(result['status'], 'SYNCED')
        self.assertTrue((self.options['codex_home'] / 'AGENTS.md').exists())
        self.assertEqual(len(self.controller.installed_skills()), 4)
        self.assertTrue(self.controller.backup_history())
        restored = self.controller.restore_previous(result['backup_id'], confirmed=True)
        self.assertEqual(restored['status'], 'RESTORED')
        self.assertFalse((self.options['codex_home'] / 'AGENTS.md').exists())

    def test_changed_remote_requires_new_preview_and_new_owner_is_blocked(self):
        self.prepare()
        self.controller.preview_changes()
        self.client.revision = 'b' * 40
        with self.assertRaises(WorkspaceError):
            self.controller.sync_now(confirmed=True)
        self.controller.preview_changes()
        self.client.login = 'bob'
        with self.assertRaises(WorkspaceError):
            self.controller.sync_now(confirmed=True)
        self.assertFalse(self.options['codex_home'].exists())

    def test_conflicting_local_rules_survive_sync(self):
        self.prepare()
        self.options['codex_home'].mkdir()
        path = self.options['codex_home'] / 'AGENTS.md'
        path.write_text('keep local rules')
        plan = self.controller.preview_changes()
        self.assertTrue(plan['conflicts'])
        with self.assertRaises(WorkspaceError):
            self.controller.sync_now(confirmed=True)
        self.assertEqual(path.read_text(), 'keep local rules')

    def test_same_repo_two_machines_use_separate_local_backups(self):
        self.prepare()
        self.controller.preview_changes()
        self.controller.sync_now(confirmed=True)
        other = WorkspaceController(state_dir=self.base / 'state2', codex_home=self.base / 'codex2',
                                    skills_root=self.base / 'skills2', client=self.client,
                                    source=self.options['source'])
        other.connect()
        other.select_repository(reuse=True, confirmed=True)
        other.preview_changes()
        other.sync_now(confirmed=True)
        self.assertEqual((self.base / 'codex2/AGENTS.md').read_bytes(),
                         (self.base / 'codex/AGENTS.md').read_bytes())
        self.assertNotEqual(self.controller.backup_history(), other.backup_history())

    def test_chatgpt_never_connected_by_gh_or_self_report(self):
        self.assertEqual(self.controller.status()['chatgpt_status'], 'NOT_CONNECTED')
        self.prepare()
        self.assertNotEqual(self.controller.request_chatgpt_verification()['status'], 'CONNECTED')
        self.assertNotIn('Connected', json.dumps(self.controller.status()))
        self.assertTrue(self.controller.chatgpt_guide()['url'].startswith('https://help.openai.com/'))

    def test_audit_does_not_contain_raw_backend_error(self):
        def fail():
            raise RuntimeError('ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 private raw response')
        self.client.inspect_account = fail
        with self.assertRaises(WorkspaceError) as cm:
            self.controller.connect()
        self.assertNotIn('ghp_', str(cm.exception))
        self.assertNotIn('ghp_', json.dumps(self.controller.error_logs()))

    def test_public_oauth_id_is_persisted_but_no_tokens(self):
        self.controller.configure_oauth_client('Iv1.public-client-id')
        self.assertIn('Iv1.public-client-id', '\n'.join(p.read_text() for p in self.options['state_dir'].glob('*.json')))
        with self.assertRaises(WorkspaceError):
            self.controller.configure_oauth_client('ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')


class RecoveryTests(unittest.TestCase):
    setUp = ControllerTests.setUp
    prepare = ControllerTests.prepare
    def test_selection_changed_by_second_process_invalidates_preview(self):
        self.prepare()
        self.controller.preview_changes()
        other = WorkspaceController(**self.options)
        other.select_repository(name='other-workspace', confirmed=True)
        with self.assertRaises(WorkspaceError) as cm:
            self.controller.sync_now(confirmed=True)
        self.assertEqual(cm.exception.code, 'SETTINGS_CHANGED')
        self.assertFalse(self.options['codex_home'].exists())

    def test_revoked_credential_connect_starts_explicit_new_grant(self):
        from tools.workspace_github import WorkspaceError as ApiError
        def revoked():
            raise ApiError('HTTP_401')
        self.client.inspect_account = revoked
        called = []
        def authorize(**kwargs):
            called.append(True)
            return {'login': 'alice', 'secure_storage': True}
        self.client.connect = authorize
        self.assertEqual(self.controller.connect()['status'], 'CONNECTED')
        self.assertEqual(called, [True])

    def test_abandoned_lockfile_does_not_block_restart(self):
        self.options['state_dir'].mkdir()
        (self.options['state_dir'] / 'settings.lock').touch()
        self.controller.skip_setup()
        self.assertFalse(WorkspaceController(**self.options).status()['wizard_needed'])

    def test_cli_device_user_code_visible_but_not_token(self):
        import contextlib
        import io
        from unittest.mock import patch
        from tools.personal_workspace import main
        from tools.workspace_github import WorkspaceError as ApiError
        def absent():
            raise ApiError('NOT_CONNECTED')
        self.client.inspect_account = absent
        def authorize(**kwargs):
            kwargs['on_challenge']({'user_code': 'ABCD-EFGH', 'verification_uri': 'https://github.com/login/device'})
            return {'login': 'alice', 'secure_storage': True}
        self.client.connect = authorize
        out, err = io.StringIO(), io.StringIO()
        with patch('tools.personal_workspace.WorkspaceController', return_value=self.controller), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = main(['connect'])
        self.assertEqual(result, 0)
        self.assertIn('ABCD-EFGH', err.getvalue())
        self.assertEqual(json.loads(out.getvalue())['status'], 'CONNECTED')


    def test_oauth_configuration_change_invalidates_old_write_capability(self):
        self.prepare()
        self.controller.preview_changes()
        other = WorkspaceController(**self.options)
        other.configure_oauth_client('Iv1.changed-public-id')
        with self.assertRaises(WorkspaceError) as cm:
            self.controller.initialize(confirmed=True)
        self.assertEqual(cm.exception.code, 'SETTINGS_CHANGED')
        self.assertEqual(len([w for w in self.client.writes if w[0] == 'initialize']), 1)

    def test_os_releases_settings_operation_lock_after_process_crash(self):
        import subprocess
        import sys
        script = ('import os,sys\nfrom pathlib import Path\n'
                  'from tools.workspace_lock import exclusive_lock\n'
                  'with exclusive_lock(Path(sys.argv[1])):\n    os._exit(7)\n')
        proc = subprocess.run([sys.executable, '-c', script,
                               str(self.options['state_dir'] / 'operation.lock')],
                              capture_output=True, timeout=10, check=False)
        self.assertEqual(proc.returncode, 7)
        self.controller.skip_setup()
        self.assertFalse(self.controller.status()['wizard_needed'])

    def test_disconnect_requires_consent_and_only_own_credential_backend(self):
        from types import SimpleNamespace
        deleted = []
        self.client.auth = SimpleNamespace(disconnect=lambda: deleted.append('own-native-namespace'))
        self.prepare()
        with self.assertRaises(WorkspaceError):
            self.controller.disconnect()
        self.assertEqual(deleted, [])
        self.assertEqual(self.controller.disconnect(confirmed=True)['status'], 'DISCONNECTED')
        self.assertEqual(deleted, ['own-native-namespace'])
        self.assertIsNone(self.controller.status()['github_account'])
        self.assertEqual(len([w for w in self.client.writes if w[0] == 'create']), 1)
