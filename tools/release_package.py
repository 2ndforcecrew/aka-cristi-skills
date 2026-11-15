"""Deterministic, source-commit-linked public candidate archive builder.

Only committed Git blobs are packaged. This does not create signatures or publish.
"""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from tools.fs_safety import checked_path

COMMIT = re.compile(r'^[0-9a-f]{40}$')
VERSION = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?$')
MAX_BYTES = 32 * 1024 * 1024


def git(repo, *arguments):
    proc = subprocess.run(['git', '-C', str(repo), *arguments], capture_output=True,
                          check=False, timeout=30)
    if proc.returncode:
        raise ValueError('Cannot read requested Git source snapshot')
    return proc.stdout


def build(repo, commit, version, output):
    if not COMMIT.fullmatch(commit) or not VERSION.fullmatch(version):
        raise ValueError('Exact lowercase source commit and semantic version required')
    if git(repo, 'rev-parse', '--verify', commit + '^{commit}').decode().strip() != commit:
        raise ValueError('Source commit mismatch')
    output = checked_path(output)
    name = f'aka-cristi-skills-{version}.zip'
    archive, manifest = output/name, output/'release-manifest.json'
    if archive.exists() or manifest.exists():
        raise ValueError('Refusing to replace release artifacts')
    entries = []
    total = 0
    for entry in git(repo, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        path = raw_name.decode('utf-8')
        pure = PurePosixPath(path)
        if mode not in (b'100644', b'100755') or kind != b'blob' or pure.is_absolute() or '..' in pure.parts or '\\' in path:
            raise ValueError('Unsupported source filesystem entry')
        contents = git(repo, 'cat-file', 'blob', oid.decode('ascii'))
        total += len(contents)
        if total > MAX_BYTES or len(entries) >= 2000:
            raise ValueError('Source package exceeds public package bounds')
        entries.append((path, contents, mode))
    output.mkdir(parents=True, exist_ok=True)
    # Fixed order, timestamps and stored bytes avoid zlib/platform variance.
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
        for path, contents, mode in sorted(entries):
            info = zipfile.ZipInfo(f'aka-cristi-skills-{commit}/{path}', (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if mode == b'100755' else 0o100644) << 16
            z.writestr(info, contents)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    record = {'schema_version': 1, 'version': version, 'archive': name,
              'sha256': digest, 'source_commit': commit,
              'repository': '2ndforcecrew/aka-cristi-skills',
              'python': '>=3.11', 'platforms': ['Windows', 'macOS', 'Linux'],
              'runtime_acceptance': 'NOT_RUN', 'format': 'deterministic-zip-stored-v1'}
    with manifest.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return {'archive': str(archive), 'manifest': str(manifest), 'sha256': digest,
            'source_commit': commit, 'signed': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--commit', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.repo, args.commit, args.version, args.out), indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps({'status': 'FAIL', 'reason': 'Candidate packaging failed; no release published'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
