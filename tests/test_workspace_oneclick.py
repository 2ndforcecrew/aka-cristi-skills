"""One-click setup orchestration: Mock GitHub, real public assets, temp dirs.

No real network, browser, keyring or home-directory writes. The fake client
mirrors tests/test_personal_workspace.py FakeGitHub (same repository/file
contract) and additionally models authorize-once Device Flow, connect counting,
challenge delivery and injectable failures.
"""
import contextlib
import copy
import io
import json
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.personal_workspace import WorkspaceController, WorkspaceError
from tools.workspace_oneclick import OneClickSetup

ALLOWED_FAKE_CALLS = {'inspect_account', 'connect', 'repo_info', 'create_private_repo',
                      'initialize_repo', 'fetch_snapshot'}


def _tree_snapshot(path: Path) -> object:
    if not path.exists():
        return None
    if path.is_file():
        info = path.stat()
        return (info.st_mtime_ns, info.st_size)
    return {str(p.relative_to(path)): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(path.rglob('*'))}


class OneClickFakeGitHub:
    """Mock GitHub client with authorize-once connect and failure hooks."""

    def __init__(self) -> None:
        self.login = 'alice'
        self.repositories: dict = {}
        self.remote_files: dict = {}
        self.writes: list = []
        self.calls: list = []
        self.revision = 'a' * 40
        self.authorized = False
        self.connect_calls = 0
        self.challenges: list = []
        self.client_id_missing = False
        self.fail_initialize_code: str | None = None

    def inspect_account(self) -> dict:
        self.calls.append(('inspect_account',))
        if not self.authorized:
            raise WorkspaceError('NOT_CONNECTED')
        return {'login': self.login, 'secure_storage': True}

    def connect(self, **kwargs: object) -> dict:
        self.calls.append(('connect',))
        self.connect_calls += 1
        if self.client_id_missing:
            raise WorkspaceError('OAUTH_CLIENT_ID_REQUIRED')
        cancel_event = kwargs.get('cancel_event')
        if isinstance(cancel_event, threading.Event) and cancel_event.is_set():
            raise WorkspaceError('AUTH_CANCELLED')
        on_challenge = kwargs.get('on_challenge')
        if callable(on_challenge):
            challenge = {'verification_uri': 'https://github.com/login/device',
                         'user_code': 'ABCD-EFGH'}
            self.challenges.append(challenge)
            on_challenge(challenge)
        self.authorized = True
        return {'login': self.login, 'secure_storage': True}

    def repo_info(self, owner: str, name: str) -> dict:
        self.calls.append(('repo_info', owner, name))
        if name not in self.repositories:
            raise WorkspaceError('REPO_NOT_FOUND')
        return copy.deepcopy(self.repositories[name])

    def create_private_repo(self, name: str, confirmed: bool = False) -> dict:
        assert confirmed
        self.calls.append(('create_private_repo', name))
        self.writes.append(('create', name))
        repo = {'id': 1, 'owner': self.login, 'name': name,
                'full_name': self.login + '/' + name, 'private': True,
                'html_url': 'https://github.com/' + self.login + '/' + name,
                'default_branch': 'main', 'permissions': {'push': True}}
        self.repositories[name] = repo
        return copy.deepcopy(repo)

    def initialize_repo(self, owner: str, name: str, files: dict, confirmed: bool = False) -> dict:
        assert confirmed
        self.calls.append(('initialize_repo', name))
        if self.fail_initialize_code is not None:
            raise WorkspaceError(self.fail_initialize_code)
        encoded = {path: text.encode('utf-8') for path, text in files.items()}
        if encoded == self.remote_files:
            # Real GhClient returns the existing revision without new writes.
            return {'source_revision': self.revision}
        self.writes.append(('initialize', name))
        self.remote_files = encoded
        return {'source_revision': self.revision}

    def fetch_snapshot(self, owner: str, name: str) -> dict:
        self.calls.append(('fetch_snapshot', owner, name))
        if not self.remote_files:
            raise WorkspaceError('REPO_NOT_FOUND')
        return {'manifest': json.loads(self.remote_files['workspace.json']),
                'files': {k: v for k, v in self.remote_files.items() if k != 'workspace.json'},
                'source_revision': self.revision}


class OneClickTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.client = OneClickFakeGitHub()
        self.options = {'state_dir': self.base / 'state', 'codex_home': self.base / 'codex',
                        'skills_root': self.base / 'skills', 'client': self.client,
                        'source': Path(__file__).resolve().parents[1]}
        self.controller = WorkspaceController(**self.options)
        self.events: list = []
        self.challenges: list = []
        self.setup = OneClickSetup(
            self.controller, on_step=lambda step, state: self.events.append((step, state)))

    def test_happy_path_completes_all_six_steps(self) -> None:
        result = self.setup.run(confirmed=True, on_challenge=self.challenges.append)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['completed'], list(OneClickSetup.STEPS))
        self.assertIsNone(result['code'])
        self.assertEqual(result['repository'], 'alice/my-agent-workspace')
        self.assertEqual(result['sync_status'], 'SYNCED')
        self.assertEqual(result['chatgpt_status'], 'PENDING_VERIFICATION')
        status = self.controller.status()
        self.assertEqual(status['sync_mode'], 'manual')
        self.assertEqual(status['chatgpt_status'], 'PENDING_VERIFICATION')
        skills = self.controller.installed_skills()
        self.assertEqual(len(skills), 4)
        self.assertTrue(all(item['status'] == 'INSTALLED' for item in skills))
        self.assertEqual((self.options['codex_home'] / 'AGENTS.md').read_bytes(),
                         (self.options['source'] / 'templates' / 'AGENTS.global.md').read_bytes())
        self.assertEqual(self.client.connect_calls, 1)
        self.assertEqual(self.client.writes,
                         [('create', 'my-agent-workspace'), ('initialize', 'my-agent-workspace')])
        self.assertEqual(self.challenges, [{'verification_uri': 'https://github.com/login/device',
                                            'user_code': 'ABCD-EFGH'}])
        expected = [(step, state) for step in OneClickSetup.STEPS for state in ('started', 'done')]
        self.assertEqual(self.events, expected)

    def test_consent_required_with_zero_writes(self) -> None:
        plan = self.setup.plan()
        self.assertEqual([entry['name'] for entry in plan['steps']], list(OneClickSetup.STEPS))
        self.assertTrue(all(entry['writes'] for entry in plan['steps']))
        with self.assertRaises(WorkspaceError) as caught:
            self.setup.run(confirmed=False)
        self.assertEqual(caught.exception.code, 'CONFIRMATION_REQUIRED')
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.connect_calls, 0)
        self.assertEqual(self.client.calls, [])
        self.assertIsNone(self.controller.status()['repository'])
        self.assertEqual(self.events, [])

    def test_second_run_resumes_without_second_authorization(self) -> None:
        first = self.setup.run(confirmed=True, on_challenge=self.challenges.append)
        self.assertEqual(first['status'], 'COMPLETED')
        second = self.setup.run(confirmed=True)
        self.assertEqual(second['status'], 'COMPLETED')
        self.assertEqual(second['completed'], list(OneClickSetup.STEPS))
        self.assertEqual(self.client.connect_calls, 1)
        self.assertEqual(len(self.client.challenges), 1)
        self.assertEqual(self.client.writes,
                         [('create', 'my-agent-workspace'), ('initialize', 'my-agent-workspace')])
        self.assertEqual(self.controller.status()['sync_status'], 'SYNCED')

    def test_existing_repo_reuses_without_overwrite(self) -> None:
        self.client.create_private_repo('my-agent-workspace', confirmed=True)
        self.client.writes.clear()
        result = self.setup.run(confirmed=True)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['step'], 'repository')
        self.assertEqual(result['code'], 'REUSE_REQUIRED' if 'REUSE_REQUIRED' in __import__('tools.personal_workspace', fromlist=['SAFE_ERRORS']).SAFE_ERRORS else 'OPERATION_FAILED')
        self.assertEqual(self.client.writes, [])
        # Existing private repositories require separate consent in the manual wizard.

    def test_initialize_mismatch_stops_before_sync(self) -> None:
        self.client.fail_initialize_code = 'INITIALIZATION_CONFLICT'
        result = self.setup.run(confirmed=True)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['step'], 'initialize')
        # The controller sanitizes INITIALIZATION_CONFLICT (not in SAFE_ERRORS).
        self.assertEqual(result['code'], 'OPERATION_FAILED')
        self.assertEqual(result['completed'], ['connect', 'repository'])
        self.assertFalse((self.options['codex_home'] / 'AGENTS.md').exists())
        self.assertNotIn('fetch_snapshot', [call[0] for call in self.client.calls])

    def test_preview_conflict_stops_with_zero_writes(self) -> None:
        first = self.setup.run(confirmed=True)
        self.assertEqual(first['status'], 'COMPLETED')
        path = self.options['codex_home'] / 'AGENTS.md'
        path.write_text('keep local rules')
        writes_before = list(self.client.writes)
        result = self.setup.run(confirmed=True)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['step'], 'preview')
        self.assertEqual(result['code'], 'SYNC_CONFLICT')
        self.assertEqual(result['completed'], ['connect', 'repository', 'initialize'])
        self.assertEqual(self.client.writes, writes_before)
        self.assertEqual(path.read_text(), 'keep local rules')

    def test_missing_oauth_client_id_stops_at_step_one(self) -> None:
        self.client.client_id_missing = True
        result = self.setup.run(confirmed=True)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['step'], 'connect')
        self.assertEqual(result['code'], 'OAUTH_CLIENT_ID_REQUIRED')
        self.assertEqual(result['completed'], [])
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.connect_calls, 1)
        self.assertNotIn('my-agent-workspace', self.client.repositories)

    def test_cancel_during_connect(self) -> None:
        cancel = threading.Event()
        cancel.set()
        result = self.setup.run(confirmed=True, cancel_event=cancel)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['step'], 'connect')
        self.assertEqual(result['code'], 'AUTH_CANCELLED')
        self.assertEqual(result['completed'], [])
        self.assertEqual(self.client.writes, [])
        self.assertNotIn('my-agent-workspace', self.client.repositories)

    def test_chatgpt_never_connected(self) -> None:
        self.assertEqual(self.controller.status()['chatgpt_status'], 'NOT_CONNECTED')
        result = self.setup.run(confirmed=True)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['chatgpt_status'], 'PENDING_VERIFICATION')
        verification = self.controller.request_chatgpt_verification()
        self.assertFalse(verification['connected'])
        self.assertNotEqual(verification['status'], 'CONNECTED')
        self.assertNotIn('Connected', json.dumps(result))
        self.assertNotIn('Connected', json.dumps(self.controller.status()))

    def test_no_real_network_and_no_real_home_writes(self) -> None:
        home = Path.home()
        watched = [home / '.codex', home / '.config' / 'gh', home / '.aka-personal-workspace']
        before = {str(path): _tree_snapshot(path) for path in watched}
        with (patch('urllib.request.build_opener', side_effect=AssertionError('real network')),
              patch('urllib.request.urlopen', side_effect=AssertionError('real network')),
              patch('webbrowser.open', side_effect=AssertionError('browser opened'))):
            result = self.setup.run(confirmed=True)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertTrue({call[0] for call in self.client.calls} <= ALLOWED_FAKE_CALLS)
        for path in watched:
            self.assertEqual(_tree_snapshot(path), before[str(path)])
        settings_text = ''.join(p.read_text(encoding='utf-8')
                                for p in self.options['state_dir'].glob('*.json'))
        self.assertNotIn('ghp_', settings_text)
        self.assertNotIn('token', settings_text.lower())

    def test_cli_one_click_plan_without_apply_writes_nothing(self) -> None:
        from tools.personal_workspace import main
        out = io.StringIO()
        with patch('tools.personal_workspace.WorkspaceController',
                   return_value=self.controller), contextlib.redirect_stdout(out):
            result = main(['one-click'])
        self.assertEqual(result, 0)
        plan = json.loads(out.getvalue())
        self.assertEqual([entry['name'] for entry in plan['steps']], list(OneClickSetup.STEPS))
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.connect_calls, 0)

    def test_cli_one_click_apply_stopped_returns_nonzero(self) -> None:
        from tools.personal_workspace import main
        self.client.client_id_missing = True
        out = io.StringIO()
        with patch('tools.personal_workspace.WorkspaceController',
                   return_value=self.controller), contextlib.redirect_stdout(out):
            exit_code = main(['one-click', '--apply'])
        self.assertEqual(exit_code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload['status'], 'STOPPED')
        self.assertEqual(payload['step'], 'connect')

    def test_cli_one_click_apply_runs_and_prints_completed(self) -> None:
        from tools.personal_workspace import main
        out = io.StringIO()
        with patch('tools.personal_workspace.WorkspaceController',
                   return_value=self.controller), contextlib.redirect_stdout(out):
            result = main(['one-click', '--apply'])
        self.assertEqual(result, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload['status'], 'COMPLETED')
        self.assertEqual(payload['repository'], 'alice/my-agent-workspace')


if __name__ == '__main__':
    unittest.main()
