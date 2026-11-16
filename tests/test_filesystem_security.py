"""Concrete local security regressions, unrelated to the unprovided scanner report."""
import os
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import chef_global_rules as rules, codex_subagents as agents, skill_installer as skills


class FilesystemSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.actual = self.root / 'actual'
        self.actual.mkdir()
        self.link = self.root / 'alias'
        self.template = Path(__file__).resolve().parents[1] / 'templates/AGENTS.global.md'

    def require_symlink(self, path):
        try:
            path.symlink_to(self.actual, target_is_directory=True)
        except NotImplementedError:
            self.skipTest('symlinks unsupported')
        except OSError as exc:
            if getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable (WinError 1314)')
            raise

    def test_global_rules_refuse_symlink_ancestor_without_writing(self):
        self.require_symlink(self.link)
        with self.assertRaises(rules.GlobalRulesError):
            rules.apply('install', self.template, self.link / 'home', confirmed=True)
        self.assertFalse((self.actual / 'home').exists())

    def test_global_rules_refuse_symlink_backup_folder(self):
        home = self.root / 'home'
        home.mkdir()
        (home / 'AGENTS.md').write_text('user rules\n')
        self.require_symlink(home / '.aka-chef-backups')
        with self.assertRaises(rules.GlobalRulesError):
            rules.apply('install', self.template, home, confirmed=True)
        self.assertEqual((home / 'AGENTS.md').read_text(), 'user rules\n')
        self.assertEqual(list(self.actual.iterdir()), [])

    def test_roles_refuse_symlink_ancestor_without_writing(self):
        self.require_symlink(self.link)
        with self.assertRaises(agents.AgentInstallError):
            agents.install('research', self.link / 'home', apply=True)
        self.assertFalse((self.actual / 'home').exists())

    def test_skill_digest_independent_of_directory_enumeration(self):
        source = self.root / 'demo'
        source.mkdir()
        (source / 'SKILL.md').write_text('---\nname: demo\ndescription: demo\n---\ntext\n')
        for filename in ('a.txt', 'z.txt'):
            (source / filename).write_text(filename)
        real_walk = os.walk
        def walk_order(reverse):
            def walk(*args, **kwargs):
                for folder, dirs, files in real_walk(*args, **kwargs):
                    yield folder, sorted(dirs, reverse=reverse), sorted(files, reverse=reverse)
            return walk
        with patch.object(skills.os, 'walk', walk_order(False)):
            first = skills.package(source)['sha256']
        with patch.object(skills.os, 'walk', walk_order(True)):
            second = skills.package(source)['sha256']
        self.assertEqual(first, second)

    def test_metadata_size_checked_before_read(self):
        source = self.root / 'demo'
        source.mkdir()
        metadata = source / 'SKILL.md'
        metadata.write_bytes(b'x' * (2 * 1024 * 1024 + 1))
        with patch.object(Path, 'read_text', side_effect=AssertionError('oversized metadata read')):
            with self.assertRaises(skills.InstallError):
                skills.package(source)


@unittest.skipUnless(os.name == 'nt', 'Actual Windows junction filesystem test')
class WindowsJunctionTests(unittest.TestCase):
    def test_skill_package_refuses_nested_junction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source, outside = root / 'demo', root / 'outside'
            source.mkdir()
            outside.mkdir()
            (source / 'SKILL.md').write_text('---\nname: demo\ndescription: demo\n---\n')
            (outside / 'private.txt').write_text('must remain outside')
            created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(source / 'linked'),
                                      str(outside)], capture_output=True, check=False, timeout=10)
            self.assertEqual(created.returncode, 0, 'Windows junction creation failed')
            with self.assertRaises(skills.InstallError):
                skills.package(source)
            self.assertEqual((outside / 'private.txt').read_text(), 'must remain outside')
