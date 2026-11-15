"""Packaging tests and synthetic gh process contract tests; not live signature proof."""
import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import release_package, verify_release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        for command in (['init', '-q'], ['config', 'user.name', 'Test'],
                        ['config', 'user.email', 'test@example.invalid']):
            subprocess.run(['git', '-C', str(self.repo), *command], check=True)
        (self.repo / 'README.md').write_text('Public fixture\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'fixture'], check=True)
        self.commit = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()

    def build(self, folder):
        return release_package.build(self.repo, self.commit, '0.3.0-rc.1', self.root / folder)

    def test_package_is_deterministic_and_uses_committed_bytes(self):
        first = self.build('one')
        (self.repo / 'README.md').write_text('Uncommitted data must not ship')
        second = self.build('two')
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertEqual(Path(first['archive']).read_bytes(), Path(second['archive']).read_bytes())
        manifest = json.loads(Path(first['manifest']).read_text())
        self.assertEqual(manifest['source_commit'], self.commit)
        self.assertEqual(manifest['sha256'], hashlib.sha256(Path(first['archive']).read_bytes()).hexdigest())
        with zipfile.ZipFile(first['archive']) as z:
            self.assertEqual(z.read(f'aka-cristi-skills-{self.commit}/README.md'), b'Public fixture\n')

    def test_rejects_invalid_or_mismatched_source_commit(self):
        for commit in ['main', '0'*40, '--help']:
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                release_package.build(self.repo, commit, '0.3.0-rc.1', self.root/'out')

    def test_refuses_to_overwrite_existing_artifact(self):
        self.build('out')
        with self.assertRaises(ValueError):
            self.build('out')

    def test_recorded_git_symlinks_are_not_packaged(self):
        oid = subprocess.check_output(['git', '-C', str(self.repo), 'hash-object', '-w', '--stdin'], input=b'elsewhere').decode().strip()
        subprocess.run(['git', '-C', str(self.repo), 'update-index', '--add', '--cacheinfo', f'120000,{oid},link'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'symlink fixture'], check=True)
        self.commit = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()
        with self.assertRaises(ValueError):
            self.build('out')
        self.assertFalse((self.root/'out').exists())

    def test_windows_311_reparse_attributes_rejected_for_release_paths(self):
        from types import SimpleNamespace
        import stat
        data = self.build('out')
        archive = Path(data['archive'])
        marked = self.root
        original = Path.lstat
        def reported(path, *args, **kwargs):
            if path == marked:
                return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x400)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'lstat', reported):
            with self.assertRaises(ValueError):
                verify_release.regular(archive)
            with self.assertRaises(ValueError):
                verify_release.extract_archive(archive, self.commit, self.root/'extract')
            with self.assertRaises(ValueError):
                self.build('more')

    @unittest.skipUnless(__import__('os').name == 'nt', 'Actual Windows junction test')
    def test_actual_windows_junction_refused_for_all_release_paths(self):
        target = self.root/'junction-target'
        target.mkdir()
        junction = self.root/'junction'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)], capture_output=True)
        self.assertEqual(result.returncode, 0, 'Cannot create Windows junction test fixture')
        self.addCleanup(lambda: __import__('os').rmdir(junction) if junction.exists() else None)
        (target/'file.zip').write_bytes(b'fixture')
        with self.assertRaises(ValueError):
            verify_release.regular(junction/'file.zip')
        data = self.build('out')
        with self.assertRaises(ValueError):
            verify_release.extract_archive(Path(data['archive']), self.commit, junction/'extract')
        with self.assertRaises(ValueError):
            release_package.build(self.repo, self.commit, '0.3.0-rc.1', junction/'output')
        self.assertFalse((target/'output').exists())

    def test_bad_digest_and_missing_bundle_fail_before_gh(self):
        data = self.build('out')
        archive = Path(data['archive'])
        with patch('tools.verify_release.subprocess.run') as run:
            with self.assertRaises(ValueError):
                verify_release.verify_archive(archive, self.commit, '0'*64)
            with self.assertRaises(ValueError):
                verify_release.verify_archive(archive, self.commit, data['sha256'], bundle=self.root/'missing')
            run.assert_not_called()

    def test_gh_policy_pins_identity_digest_and_ref(self):
        data = self.build('out')
        outputs = [subprocess.CompletedProcess([], 0, b'gh version 2.102.0\n', b''),
                   subprocess.CompletedProcess([], 0, b'[{"verificationResult":{}}]', b'')]
        with patch('tools.verify_release.shutil.which', return_value='/trusted/gh'), patch('tools.verify_release.subprocess.run', side_effect=outputs) as run:
            result = verify_release.verify_archive(Path(data['archive']), self.commit, data['sha256'])
        self.assertEqual(result['status'], 'PASS')
        command = run.call_args_list[1].args[0]
        for flag, expected in [('--repo', '2ndforcecrew/aka-cristi-skills'),
                ('--source-digest', self.commit), ('--signer-digest', self.commit),
                ('--source-ref', 'refs/heads/main'),
                ('--signer-workflow', '2ndforcecrew/aka-cristi-skills/.github/workflows/release-candidate.yml')]:
            self.assertEqual(command[command.index(flag)+1], expected)
        self.assertLessEqual(run.call_args_list[1].kwargs['timeout'], 120)

    def test_gh_missing_old_failed_empty_or_malformed_attestation_fails_closed(self):
        data = self.build('out')
        archive = Path(data['archive'])
        with patch('tools.verify_release.shutil.which', return_value=None), self.assertRaises(ValueError):
            verify_release.verify_archive(archive, self.commit, data['sha256'])
        cases = [
            [subprocess.CompletedProcess([], 0, b'gh version 2.101.0', b'')],
            [subprocess.CompletedProcess([], 0, b'gh version 2.102.0', b''), subprocess.CompletedProcess([], 1, b'[]', b'private diagnostic')],
            [subprocess.CompletedProcess([], 0, b'gh version 2.102.0', b''), subprocess.CompletedProcess([], 0, b'[]', b'')],
            [subprocess.CompletedProcess([], 0, b'gh version 2.102.0', b''), subprocess.CompletedProcess([], 0, b'not-json', b'')],
        ]
        for outputs in cases:
            with self.subTest(outputs=outputs), patch('tools.verify_release.shutil.which', return_value='/trusted/gh'), patch('tools.verify_release.subprocess.run', side_effect=outputs), self.assertRaises(ValueError):
                verify_release.verify_archive(archive, self.commit, data['sha256'])

    def test_timeout_and_archive_change_before_extraction_fail_closed(self):
        data = self.build('out')
        archive = Path(data['archive'])
        with patch('tools.verify_release.shutil.which', return_value='/trusted/gh'), patch('tools.verify_release.subprocess.run', side_effect=subprocess.TimeoutExpired(['gh'], 10)), self.assertRaises(ValueError):
            verify_release.verify_archive(archive, self.commit, data['sha256'])
        with self.assertRaises(ValueError):
            verify_release.extract_archive(archive, self.commit, self.root/'extract', '0'*64)
        self.assertFalse((self.root/'extract').exists())

    def test_safe_extract_rejects_traversal_duplicate_and_symlink_before_writes(self):
        root = f'aka-cristi-skills-{self.commit}'
        for names in [[f'{root}/../escape'], [f'{root}/x', f'{root}/X'], [f'{root}/CON']]:
            archive = self.root/'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for name in names:
                    z.writestr(name, 'bad')
            destination = self.root/'extract'
            with self.subTest(names=names), self.assertRaises(ValueError):
                verify_release.extract_archive(archive, self.commit, destination)
            self.assertFalse(destination.exists())
        with zipfile.ZipFile(self.root/'bad.zip', 'w') as z:
            info = zipfile.ZipInfo(f'{root}/link')
            info.external_attr = 0o120777 << 16
            z.writestr(info, 'elsewhere')
        with self.assertRaises(ValueError):
            verify_release.extract_archive(self.root/'bad.zip', self.commit, self.root/'extract')

    def test_extract_refuses_existing_destination_and_preserves_it(self):
        data = self.build('out')
        dest = self.root/'extract'
        verify_release.extract_archive(Path(data['archive']), self.commit, dest)
        contents = (dest/'README.md').read_bytes()
        with self.assertRaises(ValueError):
            verify_release.extract_archive(Path(data['archive']), self.commit, dest)
        self.assertEqual((dest/'README.md').read_bytes(), contents)


if __name__ == '__main__':
    unittest.main()
