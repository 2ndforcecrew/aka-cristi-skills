import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import Mock

from tools.workspace_github import GhClient, WorkspaceError, PUBLIC_PATHS


class FakeClient(GhClient):
    def __init__(self, root):
        super().__init__(root, auth=Mock())
        self.calls = []
        self.responses = {}

    def inspect_account(self):
        return {'login': 'alice', 'secure_storage': True}

    def _api(self, endpoint, method='GET', data=None):
        self.calls.append((endpoint, method, data))
        value = self.responses.get((endpoint, method))
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise WorkspaceError('REPO_NOT_FOUND')
        return value


def repo(**extra):
    result = {'id': 12, 'owner': {'login': 'alice'}, 'name': 'work',
              'full_name': 'alice/work', 'private': True,
              'html_url': 'https://github.com/alice/work',
              'default_branch': 'main', 'permissions': {'push': True}}
    result.update(extra)
    return result


def exports():
    files = {path: 'public text\n' for path in PUBLIC_PATHS}
    manifest = {'schema_version': 1, 'owner': 'alice', 'repository': 'work',
                'sync_mode': 'manual', 'files': [
                    {'path': path, 'target': 'codex/AGENTS.md' if path == 'rules/AGENTS.md'
                     else ('codex/' + path if path.startswith('agents/') else path),
                     'sha256': hashlib.sha256(data.encode()).hexdigest()}
                    for path, data in files.items()]}
    files['workspace.json'] = json.dumps(manifest)
    return files


class GitHubTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.client = FakeClient(self.base / 'managed')
        self.client.responses[('repos/alice/work', 'GET')] = repo()

    def assert_code(self, code, fn):
        with self.assertRaises(WorkspaceError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)

    def test_owner_private_and_identity_checked(self):
        self.assertEqual(self.client.repo_info('alice', 'work')['id'], 12)
        for bad in ({'private': False}, {'owner': {'login': 'mallory'}},
                    {'full_name': 'alice/other'}, {'permissions': {'push': False}}):
            self.client.responses[('repos/alice/work', 'GET')] = repo(**bad)
            self.assert_code('REPO_UNSAFE', lambda: self.client.repo_info('alice', 'work'))
        self.assert_code('OWNER_MISMATCH', lambda: self.client.repo_info('bob', 'work'))

    def test_production_auth_adapter_request_integration(self):
        from tools.workspace_auth import AuthClient
        store = Mock()
        store.get_password.return_value = 'mock-in-memory-credential'
        calls = []
        created = False

        class Response:
            def __init__(self, url, payload):
                self.url = url
                self.body = json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def geturl(self):
                return self.url

            def read(self, count):
                return self.body[:count]

        def request(req, timeout):
            nonlocal created
            calls.append((req.method, req.full_url))
            self.assertEqual(req.get_header('Authorization'), 'Bearer mock-in-memory-credential')
            if req.full_url == 'https://api.github.com/user':
                return Response(req.full_url, {'login': 'alice'})
            if req.full_url == 'https://api.github.com/repos/alice/work':
                if not created:
                    raise urllib.error.HTTPError(req.full_url, 404, 'missing', {}, None)
                return Response(req.full_url, repo())
            if req.full_url == 'https://api.github.com/user/repos' and req.method == 'POST':
                self.assertEqual(json.loads(req.data), {'name': 'work', 'private': True, 'auto_init': False})
                created = True
                return Response(req.full_url, repo())
            self.fail('unexpected API request')

        directory = self.base / 'integration'
        auth = AuthClient(directory, store=store, request=request)
        client = GhClient(directory, auth=auth)
        self.assertEqual(client.inspect_account()['login'], 'alice')
        self.assert_code('REPO_NOT_FOUND', lambda: client.repo_info('alice', 'work'))
        self.assertEqual(client.create_private_repo('work', confirmed=True)['owner'], 'alice')
        self.assertEqual(client.repo_info('alice', 'work')['full_name'], 'alice/work')
        self.assertIn(('POST', 'https://api.github.com/user/repos'), calls)
        for endpoint in ('//evil.example/x', 'https://evil.example/x', '../user', '/repos/%2e%2e/user', 'user#fragment', 'user\\other'):
            self.assert_code('INVALID_API_PATH', lambda endpoint=endpoint: client._api(endpoint))

    def test_account_comparison_accepts_canonical_case(self):
        self.client.responses[('repos/ALICE/work', 'GET')] = repo()
        self.assertEqual(self.client.repo_info('ALICE', 'work')['owner'], 'alice')
        self.client.responses[('repos/alice/work', 'GET')] = repo(owner={'login': 'Alice'}, full_name='Alice/work', html_url='https://github.com/Alice/work')
        self.assertEqual(self.client.repo_info('alice', 'work')['owner'], 'Alice')

    def test_connect_forwards_device_challenge_callback(self):
        auth = Mock()
        client = GhClient(self.base / 'challenge', auth=auth)
        auth.connect.return_value = {'login': 'alice', 'secure_storage': True}
        callback = Mock()
        cancellation = Mock()
        client.connect(cancel_event=cancellation, timeout=42, on_challenge=callback)
        auth.connect.assert_called_once_with(cancel_event=cancellation, timeout=42, on_challenge=callback)

    def test_creation_requires_consent_and_refuses_collision(self):
        self.assert_code('CONFIRMATION_REQUIRED', lambda: self.client.create_private_repo('work'))
        self.assert_code('REPO_EXISTS', lambda: self.client.create_private_repo('work', confirmed=True))
        self.assertFalse(any(method == 'POST' for _, method, _ in self.client.calls))

    def test_creation_verifies_result(self):
        self.client.responses[('repos/alice/work', 'GET')] = WorkspaceError('REPO_NOT_FOUND')
        def api(endpoint, method='GET', data=None):
            if method == 'POST':
                self.assertEqual(data, {'name': 'work', 'private': True, 'auto_init': False})
                self.client.responses[('repos/alice/work', 'GET')] = repo()
                return repo()
            return FakeClient._api(self.client, endpoint, method, data)
        self.client._api = api
        self.assertTrue(self.client.create_private_repo('work', confirmed=True)['private'])

    def test_initialization_consent_allowlist_and_hash(self):
        self.assert_code('CONFIRMATION_REQUIRED', lambda: self.client.initialize_repo('alice', 'work', exports()))
        bad = exports()
        bad['.env'] = 'secret'
        self.assert_code('EXPORT_INVALID', lambda: self.client.initialize_repo('alice', 'work', bad, True))
        bad = exports()
        bad['rules/AGENTS.md'] = 'changed'
        self.assert_code('HASH_MISMATCH', lambda: self.client.initialize_repo('alice', 'work', bad, True))
        self.assertFalse(any(method != 'GET' for _, method, _ in self.client.calls))

    def test_snapshot_exact_revision_and_hash(self):
        files = exports()
        revision = 'a' * 40
        self.client.responses[('repos/alice/work/commits/main', 'GET')] = {'sha': revision}
        self.client.responses[(f'repos/alice/work/git/trees/{revision}?recursive=1', 'GET')] = {'truncated': False, 'tree': [{'path': path, 'type': 'blob', 'mode': '100644'} for path in files]}
        for path, value in files.items():
            self.client.responses[(f'repos/alice/work/contents/{path}?ref={revision}', 'GET')] = {
                'type': 'file', 'encoding': 'base64', 'size': len(value.encode()),
                'content': base64.b64encode(value.encode()).decode()}
        result = self.client.fetch_snapshot('alice', 'work')
        self.assertEqual(result['source_revision'], revision)
        self.assertEqual(len(result['files']), 9)
        path = next(iter(PUBLIC_PATHS))
        self.client.responses[(f'repos/alice/work/contents/{path}?ref={revision}', 'GET')]['content'] = base64.b64encode(b'x' * len(files[path].encode())).decode()
        self.assert_code('HASH_MISMATCH', lambda: self.client.fetch_snapshot('alice', 'work'))

    def test_initialization_success_retry_collision_and_idempotency(self):
        files = exports()
        parent = 'b' * 40
        commit = 'a' * 40
        base = 'repos/alice/work'
        self.client.responses[(base + '/git/matching-refs/', 'GET')] = []
        self.client.responses[(base + '/contents/workspace.json', 'PUT')] = {}
        self.client.responses[(base + '/git/ref/heads/main', 'GET')] = {'object': {'sha': parent}}
        tree_endpoint = base + '/git/trees/' + parent + '?recursive=1'
        self.client.responses[(tree_endpoint, 'GET')] = {'truncated': False, 'tree': [{'path': 'workspace.json', 'type': 'blob', 'mode': '100644'}]}
        self.client.responses[(base + '/contents/workspace.json?ref=' + parent, 'GET')] = {'type': 'file', 'encoding': 'base64', 'size': len(files['workspace.json'].encode()), 'content': base64.b64encode(files['workspace.json'].encode()).decode()}
        self.client.responses[(base + '/git/trees', 'POST')] = {'sha': 'c' * 40}
        self.client.responses[(base + '/git/commits', 'POST')] = {'sha': commit}
        self.client.responses[(base + '/git/refs/heads/main', 'PATCH')] = {}
        snapshot = {'source_revision': commit, 'manifest': json.loads(files['workspace.json']), 'files': {p: files[p].encode() for p in PUBLIC_PATHS}}
        self.client.fetch_snapshot = Mock(return_value=snapshot)
        self.assertEqual(self.client.initialize_repo('alice', 'work', files, True)['source_revision'], commit)
        patches = [data for _, method, data in self.client.calls if method == 'PATCH']
        self.assertEqual(patches, [{'sha': commit, 'force': False}])
        self.client.calls.clear()
        self.client.responses[(base + '/git/matching-refs/', 'GET')] = [{'ref': 'refs/heads/main'}]
        self.client.responses[(tree_endpoint, 'GET')]['tree'].append({'path': 'private.txt', 'type': 'blob', 'mode': '100644'})
        self.assert_code('INITIALIZATION_CONFLICT', lambda: self.client.initialize_repo('alice', 'work', files, True))
        self.assertFalse(any(method != 'GET' for _, method, _ in self.client.calls))
        self.client.responses[(tree_endpoint, 'GET')] = {'truncated': False, 'tree': [{'path': p, 'type': 'blob', 'mode': '100644'} for p in files]}
        snapshot['source_revision'] = parent
        self.assertEqual(self.client.initialize_repo('alice', 'work', files, True)['source_revision'], parent)
        self.assertFalse(any(method != 'GET' for _, method, _ in self.client.calls))

    def test_snapshot_rejects_symlink_truncated_tree_and_unknown_target(self):
        files = exports()
        revision = 'a' * 40
        base = 'repos/alice/work'
        self.client.responses[(base + '/commits/main', 'GET')] = {'sha': revision}
        manifest = json.loads(files['workspace.json'])
        encoded = files['workspace.json'].encode()
        self.client.responses[(base + '/contents/workspace.json?ref=' + revision, 'GET')] = {'type': 'file', 'encoding': 'base64', 'size': len(encoded), 'content': base64.b64encode(encoded).decode()}
        endpoint = base + '/git/trees/' + revision + '?recursive=1'
        nodes = [{'path': p, 'type': 'blob', 'mode': '100644'} for p in files]
        self.client.responses[(endpoint, 'GET')] = {'truncated': True, 'tree': nodes}
        self.assert_code('CONTENT_INVALID', lambda: self.client.fetch_snapshot('alice', 'work'))
        self.client.responses[(endpoint, 'GET')]['truncated'] = False
        nodes[0]['mode'] = '120000'
        self.assert_code('CONTENT_INVALID', lambda: self.client.fetch_snapshot('alice', 'work'))
        manifest['files'][0]['target'] = 'codex/auth.json'
        files['workspace.json'] = json.dumps(manifest)
        self.assert_code('MANIFEST_INVALID', lambda: self.client.initialize_repo('alice', 'work', files, True))

    def test_plaintext_secret_in_export_rejected(self):
        files = exports()
        path = 'rules/AGENTS.md'
        files[path] = 'access_token = ghp_' + 'a' * 30
        manifest = json.loads(files['workspace.json'])
        for entry in manifest['files']:
            if entry['path'] == path:
                entry['sha256'] = hashlib.sha256(files[path].encode()).hexdigest()
        files['workspace.json'] = json.dumps(manifest)
        self.assert_code('EXPORT_CREDENTIALS_FORBIDDEN', lambda: self.client.initialize_repo('alice', 'work', files, True))
        self.assertFalse(self.client.calls)

    def test_private_central_repository_refused_before_any_api(self):
        self.assert_code('CENTRAL_REPOSITORY_FORBIDDEN', lambda: self.client.repo_info('alice', 'aka-cristi-agent-rules'))
        self.assert_code('CENTRAL_REPOSITORY_FORBIDDEN', lambda: self.client.create_private_repo('AKA-CRISTI-AGENT-RULES', confirmed=True))
        self.assertEqual(self.client.calls, [])

    def test_unsafe_paths_rejected(self):
        directory = self.base / 'target'
        directory.mkdir()
        link = self.base / 'link'
        try:
            link.symlink_to(directory, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows symlink privilege unavailable (WinError 1314)")
            raise
        self.assert_code('CONFIG_UNSAFE', lambda: GhClient(link, auth=Mock()))

    def test_auth_adapter_success_cancel_failure_timeout(self):
        auth = Mock()
        client = GhClient(self.base / 'other', auth=auth)
        auth.inspect_account.return_value = {'login': 'alice', 'secure_storage': True}
        auth.connect.return_value = auth.inspect_account.return_value
        self.assertEqual(client.inspect_account()['login'], 'alice')
        self.assertEqual(client.connect()['login'], 'alice')
        for code in ('AUTH_CANCELLED', 'AUTH_TIMEOUT', 'OAUTH_CLIENT_ID_REQUIRED'):
            auth.connect.side_effect = WorkspaceError(code)
            self.assert_code(code, client.connect)
        auth.inspect_account.return_value = {'login': 'alice', 'secure_storage': False}
        self.assert_code('SECURE_STORAGE_REQUIRED', client.inspect_account)
        auth.api.side_effect = WorkspaceError('HTTP_404')
        self.assert_code('REPO_NOT_FOUND', lambda: client._api('repos/alice/work'))
        auth.api.side_effect = ValueError('do not leak secret')
        self.assert_code('AUTH_FAILED', lambda: client._api('user'))
