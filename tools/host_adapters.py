"""Bounded, preview-first host installation adapters; never claim live activation.

Claude project Skill discovery follows https://code.claude.com/docs/en/skills.
The file adapter does not configure native roles, tools, MCP or credentials.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from . import skill_installer

HOSTS = ('codex', 'claude', 'hermes', 'chatgpt')


def lifecycle(installed='NOT_RUN'):
    return {'installed': installed, 'loaded': 'NOT_RUN', 'invoked': 'NOT_RUN',
            'completed_verified': 'NOT_RUN'}


class HostAdapter:
    """Common inspect/preview/install/verify/live_activation/uninstall contract.

    File operations use existing guarded installer primitives. Only inspect
    starts a subprocess, exclusively --version, with a five-second timeout.
    Nothing reads host authentication or initiates an inference request.
    """
    def __init__(self, host, project=None):
        if host not in HOSTS:
            raise ValueError('Unknown host')
        self.host = host
        self.project = None
        if host == 'claude':
            if project is None:
                raise ValueError('Claude adapter requires an explicit project directory')
            self.project = skill_installer.checked(project)
            if not self.project.is_dir():
                raise ValueError('Project must already exist')
        elif host == 'codex' and project is not None:
            raise ValueError('Codex adapter uses existing user-scope installer; omit --project')

    def _blocked(self):
        if self.host in ('hermes', 'chatgpt'):
            return {'host': self.host, 'status': 'BLOCKED', **lifecycle(),
                    'reason': 'No verified host installation or invocation adapter'}
        return None

    def _target(self):
        if self.host == 'claude':
            return {'target': 'directory', 'root': self.project / '.claude' / 'skills'}
        return {'target': 'codex'}

    def inspect(self):
        blocked = self._blocked()
        if blocked:
            return blocked
        result = {'host': self.host, 'status': 'INSPECTED', **lifecycle(),
                  'authorization': 'User-managed; not inspected',
                  'version': None, 'version_status': 'NOT_INSTALLED',
                  'scope': 'project' if self.project else 'user',
                  'native_roles': 'NOT_IMPLEMENTED', 'mcp': 'NOT_IMPLEMENTED'}
        executable = shutil.which(self.host)
        if not executable:
            return result
        try:
            run = subprocess.run([executable, '--version'], capture_output=True,
                                 timeout=5, check=False)
        except subprocess.TimeoutExpired:
            return {**result, 'version_status': 'TIMEOUT'}
        except OSError:
            return {**result, 'version_status': 'ERROR'}
        # Publish only a bounded semver token; never raw CLI output or paths.
        output = run.stdout.decode('utf-8', errors='replace') if isinstance(run.stdout, bytes) else (run.stdout or '')
        match = re.search(r'(?<![\w.])(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)(?![\w.])', output[:512])
        return {**result, 'version': match.group(1) if match and run.returncode == 0 else None,
                'version_status': 'OBSERVED' if match and run.returncode == 0 else 'UNRECOGNIZED'}

    def preview(self, source):
        blocked = self._blocked()
        if blocked:
            return blocked
        return {'host': self.host, **lifecycle(),
                **skill_installer.inspect(source, **self._target())}

    def install(self, source, apply=False):
        blocked = self._blocked()
        if blocked:
            return blocked
        result = skill_installer.install(source, apply=apply, **self._target())
        return {'host': self.host, **lifecycle('PASS' if apply else 'NOT_RUN'), **result}

    def verify(self, name):
        blocked = self._blocked()
        if blocked:
            return blocked
        result = skill_installer.verify(name, **self._target())
        return {'host': self.host, **lifecycle(result['integrity']), **result}

    def live_activation(self):
        blocked = self._blocked()
        if blocked:
            return blocked
        return {'host': self.host, 'status': 'NOT_RUN', **lifecycle(),
                'reason': 'A file adapter cannot prove host loading or inference. '
                          'Run an authorized host-specific evidence probe separately; '
                          'this operation never spends quota.'}

    def uninstall(self, name, apply=False):
        blocked = self._blocked()
        if blocked:
            return blocked
        result = skill_installer.remove(name, apply=apply, **self._target())
        return {'host': self.host, **lifecycle(), **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Preview-first host Skill adapter (no live inference)')
    parser.add_argument('host', choices=HOSTS)
    parser.add_argument('action', choices=['inspect','preview','install','verify','live-activation','uninstall'])
    parser.add_argument('value', nargs='?')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        adapter = HostAdapter(args.host, args.project)
        # Explicit dispatch table: args.action is argparse-constrained, but
        # never resolve a method by name from input (no getattr dispatch).
        # Each entry closes over the exact method and arguments it needs.
        actions = {
            'inspect': lambda: adapter.inspect(),
            'live-activation': lambda: adapter.live_activation(),
            'preview': lambda: adapter.preview(args.value),
            'install': lambda: adapter.install(args.value, apply=args.apply),
            'verify': lambda: adapter.verify(args.value),
            'uninstall': lambda: adapter.uninstall(args.value, apply=args.apply),
        }
        if args.action not in ('inspect', 'live-activation') and not args.value:
            parser.error('This action requires a Skill source path or name')
        result = actions[args.action]()
        print(json.dumps(result, indent=2))
        if result.get('status') in ('BLOCKED','NOT_RUN'):
            return 2
        if str(result.get('action', '')).startswith('conflict'):
            return 1
        return 0
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({'host': args.host, 'status':'FAIL',
                          'reason':'Unsafe, modified or missing local files; inspect your selected project.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
