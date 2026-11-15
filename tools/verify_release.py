"""Fail-closed local archive + GitHub keyless provenance verification.

Run this from reviewed/trusted source, never from an unverified archive.
SHA-256 pins and commits must come from the review decision, not a sibling download.
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from tools.fs_safety import checked_path

REPOSITORY = '2ndforcecrew/aka-cristi-skills'
WORKFLOW = REPOSITORY + '/.github/workflows/release-candidate.yml'
MIN_GH = (2, 102, 0)
COMMIT = re.compile(r'^[0-9a-f]{40}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
MAX_BYTES = 32 * 1024 * 1024


def regular(path):
    path = checked_path(path)
    if not path.is_file():
        raise ValueError('Required regular local file is missing')
    return path


def run_process(command, timeout):
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError('Provenance verifier unavailable or timed out') from exc
    if result.returncode:
        raise ValueError('Provenance verification failed; raw tool output withheld')
    return result.stdout.decode('utf-8', errors='strict')


def verify_archive(archive, expected_commit, expected_sha256,
                   source_ref='refs/heads/main', bundle=None, gh_bin='gh'):
    if not COMMIT.fullmatch(expected_commit) or not DIGEST.fullmatch(expected_sha256):
        raise ValueError('Exact source commit and SHA-256 pins required')
    if not re.fullmatch(r'refs/(heads|tags)/[A-Za-z0-9][A-Za-z0-9._/-]*', source_ref) or '..' in source_ref:
        raise ValueError('Invalid expected source ref')
    archive = regular(archive)
    if archive.stat().st_size > MAX_BYTES + 2 * 1024 * 1024:
        raise ValueError('Oversized archive')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Archive SHA-256 mismatch')
    bundle = regular(bundle) if bundle is not None else None
    gh = shutil.which(gh_bin)
    if not gh:
        raise ValueError('GitHub CLI 2.102.0+ required; install from official provider')
    version = run_process([gh, '--version'], 10)
    matched = re.search(r'gh version (\d+)\.(\d+)\.(\d+)', version)
    if not matched or tuple(map(int, matched.groups())) < MIN_GH:
        raise ValueError('GitHub CLI 2.102.0+ required for exact workflow identity checks')
    command = [gh, 'attestation', 'verify', str(archive), '--repo', REPOSITORY,
               '--signer-workflow', WORKFLOW, '--signer-digest', expected_commit,
               '--source-digest', expected_commit, '--source-ref', source_ref,
               '--predicate-type', 'https://slsa.dev/provenance/v1', '--format', 'json']
    if bundle:
        command += ['--bundle', str(bundle)]
    try:
        verified = json.loads(run_process(command, 120))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('No valid cryptographically verified provenance') from exc
    if not isinstance(verified, list) or not verified or not all(isinstance(v, dict) and isinstance(v.get('verificationResult'), dict) for v in verified):
        raise ValueError('Empty or unrecognized provenance verification result')
    # Protect the bytes verified by gh from a concurrent local archive replacement.
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Archive changed during verification')
    return {'status': 'PASS', 'sha256': digest, 'source_commit': expected_commit,
            'source_ref': source_ref, 'verifier': 'gh attestation verify',
            'publisher_workflow': WORKFLOW, 'runtime_activation': 'NOT_RUN'}


def extract_archive(archive, expected_commit, destination, expected_sha256=None):
    """Extract preverified bytes into a NEW destination; never executes contents.

    Public CLI calls verify_archive first. This low-level extractor alone is not
    an integrity/provenance check.
    """
    if not COMMIT.fullmatch(expected_commit):
        raise ValueError('Exact source commit required')
    archive = regular(archive)
    destination = checked_path(destination)
    if destination.exists():
        raise ValueError('New non-symlink extraction destination required')
    snapshot = archive.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(snapshot).hexdigest() != expected_sha256:
        raise ValueError('Archive changed after provenance verification')
    prefix = f'aka-cristi-skills-{expected_commit}'
    seen, entries, total = set(), [], 0
    with zipfile.ZipFile(io.BytesIO(snapshot)) as z:
        for info in z.infolist():
            path = PurePosixPath(info.filename)
            parts = path.parts
            key = info.filename.casefold()
            if (info.is_dir() or not parts or parts[0] != prefix or len(parts) < 2 or
                    path.is_absolute() or any(p in ('.', '..', '') for p in info.filename.split('/')) or
                    '\\' in info.filename or key in seen or
                    any(any(c in p for c in ':<>\"|?*') or p.endswith(('.', ' ')) or any(ord(c) < 32 for c in p) or
                        re.fullmatch(r'(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?', p, re.I)
                        for p in parts) or
                    stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)):
                raise ValueError('Unsafe archive entry')
            total += info.file_size
            if total > MAX_BYTES or len(entries) >= 2000:
                raise ValueError('Archive exceeds extraction bounds')
            seen.add(key)
            entries.append((info, Path(*parts[1:])))
        if not entries:
            raise ValueError('Empty archive')
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged = Path(tempfile.mkdtemp(prefix='aka-verified-', dir=destination.parent))
        try:
            for info, relative in entries:
                target = staged / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as handle:
                    handle.write(z.read(info))
            if destination.exists():
                raise ValueError('Destination appeared during extraction')
            os.rename(staged, destination)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--source-ref', default='refs/heads/main')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--extract-to', type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_archive(args.archive, args.expected_commit, args.expected_sha256, args.source_ref, args.bundle)
        if args.extract_to:
            result['extracted_to'] = str(extract_archive(args.archive, args.expected_commit, args.extract_to, args.expected_sha256))
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeError):
        print(json.dumps({'status': 'BLOCKED', 'reason': 'Archive integrity/provenance/extraction verification failed; nothing executed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
