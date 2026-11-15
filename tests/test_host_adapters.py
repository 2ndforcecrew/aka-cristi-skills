"""Synthetic filesystem tests; none invokes a live agent host."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import host_adapters as adapters


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.source = Path(__file__).resolve().parents[1] / 'skills/verified-change-loop'
        self.adapter = adapters.HostAdapter('claude', project=self.project)

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_then_install_verify_uninstall_preserves_user_files(self):
        untouched = self.project / 'notes.txt'
        untouched.write_text('user notes', encoding='utf-8')
        preview = self.adapter.preview(self.source)
        self.assertEqual(preview['action'], 'install')
        self.assertFalse((self.project / '.claude').exists())
        self.assertFalse(self.adapter.install(self.source)['applied'])
        self.adapter.install(self.source, apply=True)
        result = self.adapter.verify('verified-change-loop')
        self.assertEqual(result['installed'], 'PASS')
        self.assertEqual(result['loaded'], 'NOT_RUN')
        self.assertEqual(result['invoked'], 'NOT_RUN')
        self.assertEqual(result['completed_verified'], 'NOT_RUN')
        removed = self.adapter.uninstall('verified-change-loop', apply=True)
        self.assertTrue(Path(removed['archive']).is_dir())
        self.assertEqual(untouched.read_text(), 'user notes')

    def test_changed_config_blocks_uninstall_and_upgrade(self):
        self.adapter.install(self.source, apply=True)
        file = self.project / '.claude/skills/verified-change-loop/SKILL.md'
        old = file.read_text(encoding='utf-8')
        file.write_text(old + '\nUser additions\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.adapter.uninstall('verified-change-loop', apply=True)
        with self.assertRaises(ValueError):
            self.adapter.install(self.source, apply=True)
        self.assertEqual(file.read_text(encoding='utf-8'), old + '\nUser additions\n')

    def test_symlink_parent_rejected(self):
        destination = self.root / 'elsewhere'
        destination.mkdir()
        try:
            (self.project / '.claude').symlink_to(destination, target_is_directory=True)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        with self.assertRaises(ValueError):
            self.adapter.install(self.source, apply=True)
        self.assertEqual(list(destination.iterdir()), [])

    def test_unsupported_hosts_never_mutate(self):
        for host in ('hermes', 'chatgpt'):
            adapter = adapters.HostAdapter(host, project=self.project)
            for result in (adapter.inspect(), adapter.preview(self.source),
                           adapter.install(self.source, apply=True),
                           adapter.verify('verified-change-loop'),
                           adapter.live_activation(),
                           adapter.uninstall('verified-change-loop', apply=True)):
                self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(list(self.project.iterdir()), [])

    def test_claude_requires_explicit_existing_project(self):
        with self.assertRaises(ValueError):
            adapters.HostAdapter('claude')
        with self.assertRaises(ValueError):
            adapters.HostAdapter('claude', project=self.root / 'missing')

    def test_live_activation_does_not_invoke_cli_or_promote_install(self):
        self.adapter.install(self.source, apply=True)
        with patch('tools.host_adapters.subprocess.run') as call:
            result = self.adapter.live_activation()
        call.assert_not_called()
        self.assertEqual(result['status'], 'NOT_RUN')
        self.assertEqual(result['invoked'], 'NOT_RUN')

    def test_version_probe_is_bounded_and_does_not_publish_raw_output(self):
        import subprocess
        with patch('tools.host_adapters.shutil.which', return_value='/tmp/claude'), \
             patch('tools.host_adapters.subprocess.run', side_effect=subprocess.TimeoutExpired('claude', 5)) as call:
            result = self.adapter.inspect()
        self.assertEqual(call.call_args.kwargs['timeout'], 5)
        self.assertEqual(result['version_status'], 'TIMEOUT')
        self.assertNotIn('stdout', result)

    def test_unknown_host_rejected(self):
        with self.assertRaises(ValueError):
            adapters.HostAdapter('made-up-host', project=self.project)
