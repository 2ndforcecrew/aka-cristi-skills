"""Fail-closed, bounded GitHub transport for a user's private workspace.

No credentials are returned or logged. OAuth and OS credential access are
delegated to workspace_auth
repository operations use its bounded HTTPS API.
The historical GhClient name is retained for the public controller contract.
"""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, unquote, urlsplit

from tools.fs_safety import checked_path

PUBLIC_PATHS = frozenset({
    'rules/AGENTS.md', 'agents/research.toml', 'agents/coding.toml',
    'agents/qa.toml', 'agents/automation.toml',
    'skills/chef-orchestrator/SKILL.md', 'skills/verified-change-loop/SKILL.md',
    'skills/feature-journey-map/SKILL.md', 'skills/skill-evaluation-gate/SKILL.md',
})
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024
SAFE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z')
REVISION = re.compile(r'[0-9a-f]{40}\Z')


class WorkspaceError(ValueError):
    """A fixed code only, never subprocess/network text."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _fail(code):
    raise WorkspaceError(code)


def _name(value, login=False):
    if not isinstance(value, str) or not (LOGIN if login else SAFE_NAME).fullmatch(value):
        _fail('NAME_INVALID')
    if not login and value.casefold() == 'aka-cristi-agent-rules':
        _fail('CENTRAL_REPOSITORY_FORBIDDEN')
    return value


def _payload_path(path):
    if not isinstance(path, str) or '\\' in path or len(path) > 240:
        _fail('MANIFEST_INVALID')
    parts = PurePosixPath(path).parts
    if not parts or str(PurePosixPath(path)) != path or any(p in ('.', '..') or p.startswith('.') for p in parts):
        _fail('MANIFEST_INVALID')
    if any(re.search(r'(?i)(token|secret|credential|password|oauth|chat|auth|\.env)', p) for p in parts):
        _fail('MANIFEST_INVALID')
    if path == 'rules/AGENTS.md':
        return 'codex/AGENTS.md'
    if len(parts) == 2 and parts[0] == 'agents' and re.fullmatch(r'[A-Za-z0-9_-]+\.toml', parts[1]):
        return 'codex/' + path
    if len(parts) >= 3 and parts[0] == 'skills' and all(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', p) for p in parts[1:]):
        return path
    _fail('MANIFEST_INVALID')


def validate_manifest(manifest, owner, name):
    """Return validated path/hash entries with exact target mappings."""
    if not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'owner', 'repository', 'sync_mode', 'files'}:
        _fail('MANIFEST_INVALID')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or manifest['owner'] != owner or manifest['repository'] != name or manifest['sync_mode'] != 'manual':
        _fail('MANIFEST_INVALID')
    entries = manifest['files']
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        _fail('MANIFEST_INVALID')
    paths = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'path', 'target', 'sha256'}:
            _fail('MANIFEST_INVALID')
        path = entry['path']
        target = _payload_path(path)
        if path in paths or target != entry['target'] or not isinstance(entry['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
            _fail('MANIFEST_INVALID')
        paths.add(path)
    return entries


class GhClient:
    # NOTE (WP-E, 2026-11-24, scan #279/TM3): the `executable` argument is a
    # dead legacy parameter, retained only for the public controller contract.
    # It is validated (non-empty str) and stored, but this module imports no
    # subprocess and never executes it: all transport goes through
    # tools.workspace_auth.AuthClient over bounded HTTPS (see
    # docs/PERSONAL_WORKSPACE_GITHUB_SECURITY.md, "The legacy `executable`
    # argument does not execute a process"). Do not reintroduce an execution
    # path keyed off this value; remove the parameter instead if the
    # controller contract is ever revised. Covered by
    # tests/test_workspace_github.py::test_executable_argument_is_inert.
    def __init__(self, config_dir: Path, executable='gh', timeout=30, auth=None):
        try:
            self.config_dir = checked_path(config_dir)
            global_config = Path(os.environ.get('GH_CONFIG_DIR', Path.home() / '.config' / 'gh')).absolute()
            if self.config_dir == global_config or self.config_dir == Path.home() or self.config_dir == Path(self.config_dir.anchor):
                _fail('CONFIG_UNSAFE')
            if self.config_dir.exists() and not self.config_dir.is_dir():
                _fail('CONFIG_UNSAFE')
        except (OSError, ValueError):
            _fail('CONFIG_UNSAFE')
        if not isinstance(executable, str) or not executable or not isinstance(timeout, (int, float)) or timeout <= 0:
            _fail('CONFIG_INVALID')
        self.executable = executable
        self.timeout = timeout
        if auth is None:
            from tools.workspace_auth import AuthClient
            try:
                auth = AuthClient(self.config_dir)
            except Exception as error:
                self._auth_error(error)
        self.auth = auth

    def _auth_error(self, error):
        code = getattr(error, 'code', 'AUTH_FAILED')
        if code == 'HTTP_404':
            code = 'REPO_NOT_FOUND'
        elif code == 'HTTP_409':
            code = 'API_CONFLICT'
        if not isinstance(code, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', code):
            code = 'AUTH_FAILED'
        raise WorkspaceError(code) from None

    def _api(self, endpoint, method='GET', data=None):
        if not isinstance(endpoint, str) or not endpoint or endpoint.startswith('//') or '\\' in endpoint or any(ord(char) < 32 or ord(char) == 127 for char in endpoint):
            _fail('INVALID_API_PATH')
        try:
            parsed = urlsplit(endpoint)
            decoded = unquote(parsed.path)
        except ValueError:
            _fail('INVALID_API_PATH')
        if parsed.scheme or parsed.netloc or parsed.fragment or '\\' in decoded or any(part in ('.', '..') for part in decoded.split('/')):
            _fail('INVALID_API_PATH')
        path = endpoint if endpoint.startswith('/') else '/' + endpoint
        try:
            return self.auth.api(method, path, data)
        except Exception as error:
            self._auth_error(error)

    def inspect_account(self):
        try:
            result = self.auth.inspect_account()
        except Exception as error:
            self._auth_error(error)
        if not isinstance(result, dict) or result.get('secure_storage') is not True:
            _fail('SECURE_STORAGE_REQUIRED')
        _name(result.get('login'), login=True)
        return {'login': result['login'], 'secure_storage': True}

    def connect(self, cancel_event=None, timeout=180, on_challenge=None):
        try:
            result = self.auth.connect(cancel_event=cancel_event, timeout=timeout, on_challenge=on_challenge)
        except Exception as error:
            self._auth_error(error)
        if not isinstance(result, dict) or result.get('secure_storage') is not True:
            _fail('SECURE_STORAGE_REQUIRED')
        _name(result.get('login'), login=True)
        return {'login': result['login'], 'secure_storage': True}

    def repo_info(self, owner, name):
        _name(owner, login=True)
        _name(name)
        if self.inspect_account()['login'].casefold() != owner.casefold():
            _fail('OWNER_MISMATCH')
        value = self._api(f'repos/{owner}/{name}')
        if not isinstance(value, dict) or not isinstance(value.get('owner'), dict) or not isinstance(value.get('permissions'), dict):
            _fail('REPO_UNSAFE')
        canonical_owner = value['owner'].get('login')
        if not isinstance(canonical_owner, str) or canonical_owner.casefold() != owner.casefold():
            _fail('REPO_UNSAFE')
        if value.get('private') is not True or value.get('name') != name or value.get('full_name') != f'{canonical_owner}/{name}' or value.get('permissions', {}).get('push') is not True or value.get('html_url') != f'https://github.com/{canonical_owner}/{name}' or type(value.get('id')) is not int:
            _fail('REPO_UNSAFE')
        branch = value.get('default_branch')
        if not isinstance(branch, str) or not branch or len(branch) > 240:
            _fail('REPO_UNSAFE')
        return {**{key: value[key] for key in ('id', 'name', 'full_name', 'private', 'html_url', 'default_branch')}, 'owner': canonical_owner, 'permissions': {'push': True}}

    def create_private_repo(self, name, confirmed=False):
        if confirmed is not True:
            _fail('CONFIRMATION_REQUIRED')
        _name(name)
        owner = self.inspect_account()['login']
        try:
            self.repo_info(owner, name)
        except WorkspaceError as error:
            if error.code != 'REPO_NOT_FOUND':
                raise
        else:
            _fail('REPO_EXISTS')
        self._api('user/repos', 'POST', {'name': name, 'private': True, 'auto_init': False})
        return self.repo_info(owner, name)

    def _content(self, owner, name, path, revision):
        value = self._api(f'repos/{owner}/{name}/contents/{quote(path, safe="/")}?ref={revision}')
        try:
            if value.get('type') != 'file' or value.get('encoding') != 'base64' or type(value.get('size')) is not int or not 0 <= value['size'] <= MAX_FILE:
                _fail('CONTENT_INVALID')
            content = base64.b64decode(''.join(value['content'].split()), validate=True)
            if len(content) != value['size'] or len(content) > MAX_FILE:
                _fail('CONTENT_INVALID')
            return content
        except WorkspaceError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError):
            _fail('CONTENT_INVALID')

    def fetch_snapshot(self, owner, name):
        repo = self.repo_info(owner, name)
        value = self._api(f'repos/{owner}/{name}/commits/{quote(repo["default_branch"], safe="")}')
        revision = value.get('sha') if isinstance(value, dict) else None
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            _fail('REVISION_INVALID')
        try:
            manifest = json.loads(self._content(owner, name, 'workspace.json', revision))
        except (ValueError, UnicodeError):
            _fail('MANIFEST_INVALID')
        entries = validate_manifest(manifest, owner, name)
        tree = self._api(f'repos/{owner}/{name}/git/trees/{revision}?recursive=1')
        if not isinstance(tree, dict) or tree.get('truncated') is not False or not isinstance(tree.get('tree'), list):
            _fail('CONTENT_INVALID')
        nodes = {}
        for node in tree['tree']:
            if not isinstance(node, dict) or not isinstance(node.get('path'), str) or node['path'] in nodes:
                _fail('CONTENT_INVALID')
            nodes[node['path']] = node
        for path in ['workspace.json', *[entry['path'] for entry in entries]]:
            node = nodes.get(path, {})
            if node.get('mode') != '100644' or node.get('type') != 'blob':
                _fail('CONTENT_INVALID')
        files = {}
        total = 0
        for entry in entries:
            content = self._content(owner, name, entry['path'], revision)
            total += len(content)
            if total > MAX_TOTAL:
                _fail('SNAPSHOT_TOO_LARGE')
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                _fail('HASH_MISMATCH')
            files[entry['path']] = content
        return {'manifest': manifest, 'files': files, 'source_revision': revision}

    def initialize_repo(self, owner, name, files, confirmed=False):
        if confirmed is not True:
            _fail('CONFIRMATION_REQUIRED')
        if not isinstance(files, dict) or set(files) != PUBLIC_PATHS | {'workspace.json'}:
            _fail('EXPORT_INVALID')
        try:
            if any(not isinstance(v, str) or len(v.encode()) > MAX_FILE for v in files.values()):
                _fail('EXPORT_INVALID')
            if sum(len(files[path].encode()) for path in PUBLIC_PATHS) > MAX_TOTAL:
                _fail('EXPORT_INVALID')
        except UnicodeError:
            _fail('EXPORT_INVALID')
        try:
            manifest = json.loads(files['workspace.json'])
        except (ValueError, UnicodeError):
            _fail('MANIFEST_INVALID')
        entries = validate_manifest(manifest, owner, name)
        if {entry['path'] for entry in entries} != PUBLIC_PATHS:
            _fail('EXPORT_INVALID')
        for entry in entries:
            content = files[entry['path']].encode()
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                _fail('HASH_MISMATCH')
            if re.search(rb'(?i)(gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*["\']?[^\s"\']{8,})', content):
                _fail('EXPORT_CREDENTIALS_FORBIDDEN')
        repo = self.repo_info(owner, name)
        # List refs; an empty array is the only accepted empty-repository proof.
        base = f'repos/{owner}/{name}'
        try:
            refs = self._api(base + '/git/matching-refs/')
        except WorkspaceError as error:
            if error.code != 'API_CONFLICT':
                raise
            refs = []  # GitHub documents 409 for an empty Git repository.
        if not isinstance(refs, list):
            _fail('REPO_UNSAFE')
        if not refs:
            # The Contents API refuses a collision without a matching SHA.
            # Seed public metadata; retries recognize only this exact seed.
            self._api(base + '/contents/workspace.json', 'PUT', {
                'message': 'Initialize public workspace manifest',
                'content': base64.b64encode(files['workspace.json'].encode()).decode(),
                'branch': repo['default_branch']})
        head = self._api(base + '/git/ref/heads/' + quote(repo['default_branch'], safe=''))
        try:
            parent = head['object']['sha']
            if not REVISION.fullmatch(parent):
                _fail('REVISION_INVALID')
        except (KeyError, TypeError):
            _fail('REVISION_INVALID')
        existing_tree = self._api(base + '/git/trees/' + parent + '?recursive=1')
        if not isinstance(existing_tree, dict) or existing_tree.get('truncated') is not False or not isinstance(existing_tree.get('tree'), list):
            _fail('INITIALIZATION_CONFLICT')
        blobs = {}
        for node in existing_tree['tree']:
            if not isinstance(node, dict):
                _fail('INITIALIZATION_CONFLICT')
            if node.get('type') == 'tree' and node.get('mode') == '040000':
                continue
            if node.get('type') != 'blob' or node.get('mode') != '100644' or not isinstance(node.get('path'), str) or node['path'] in blobs:
                _fail('INITIALIZATION_CONFLICT')
            blobs[node['path']] = node
        if set(blobs) == set(files):
            snapshot = self.fetch_snapshot(owner, name)
            if snapshot['source_revision'] != parent or snapshot['manifest'] != manifest or snapshot['files'] != {p: files[p].encode() for p in PUBLIC_PATHS}:
                _fail('INITIALIZATION_CONFLICT')
            return {'source_revision': parent}
        if set(blobs) != {'workspace.json'} or self._content(owner, name, 'workspace.json', parent) != files['workspace.json'].encode():
            _fail('INITIALIZATION_CONFLICT')
        tree = self._api(base + '/git/trees', 'POST', {'tree': [
            {'path': path, 'mode': '100644', 'type': 'blob', 'content': content}
            for path, content in sorted(files.items())]})
        if not isinstance(tree, dict) or not REVISION.fullmatch(str(tree.get('sha', ''))):
            _fail('REVISION_INVALID')
        commit = self._api(base + '/git/commits', 'POST', {'message': 'Initialize public workspace assets', 'tree': tree['sha'], 'parents': [parent]})
        if not isinstance(commit, dict) or not REVISION.fullmatch(str(commit.get('sha', ''))):
            _fail('REVISION_INVALID')
        # No force: refuse concurrent diverging head updates.
        self._api(base + '/git/refs/heads/' + quote(repo['default_branch'], safe=''), 'PATCH', {'sha': commit['sha'], 'force': False})
        result = self.fetch_snapshot(owner, name)
        if result['source_revision'] != commit['sha'] or result['files'] != {p: files[p].encode() for p in PUBLIC_PATHS}:
            _fail('INITIALIZATION_CONFLICT')
        return {'source_revision': commit['sha']}


# Preferred descriptive name; the established controller contract uses GhClient.
GitHubClient = GhClient
