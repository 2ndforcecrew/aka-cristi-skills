"""Exercise the spec's explicit data collection with fake PyInstaller build classes.

This checks our allowlist/metadata logic, not a real executable build.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch

from tools.gui_installer import BUNDLED_PUBLIC_FILES

REPO = Path(__file__).resolve().parents[1]


class BuildDataTests(unittest.TestCase):
    def build_spec(self, root, metadata):
        collected = {}
        def analysis(scripts, **kwargs):
            collected.update(kwargs)
            return types.SimpleNamespace(pure=[], scripts=scripts, binaries=[], datas=kwargs['datas'])
        with patch.dict(os.environ, {'CHEF_SOURCE_COMMIT': 'a' * 40, 'CHEF_BUILD_METADATA_DIR': str(metadata)}):
            runpy.run_path(str(REPO / 'chef-gui.spec'), init_globals={
                'SPECPATH': str(root), 'Analysis': analysis,
                'PYZ': lambda *args: None, 'EXE': lambda *args, **kwargs: None,
            })
        return collected

    def public_tree(self, root):
        for name in BUNDLED_PUBLIC_FILES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, target)

    def test_spec_bundles_only_explicit_public_data_and_matching_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root, metadata = base / 'checkout', base / 'metadata'
            self.public_tree(root)
            private = root / '.codex' / 'auth.json'
            private.parent.mkdir()
            private.write_text('synthetic-not-a-real-token')
            result = self.build_spec(root, metadata)
            self.assertEqual(len(result['datas']), len(BUNDLED_PUBLIC_FILES) + 1)
            self.assertNotIn(str(private), str(result['datas']))
            manifest = json.loads((metadata / 'bundled-public-data.json').read_text())
            self.assertEqual(set(manifest['files']), set(BUNDLED_PUBLIC_FILES))
            for name, digest in manifest['files'].items():
                self.assertEqual(digest, hashlib.sha256((root / name).read_bytes()).hexdigest())

    def test_spec_refuses_symlinked_public_data(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root, metadata = base / 'checkout', base / 'metadata'
            self.public_tree(root)
            target = root / BUNDLED_PUBLIC_FILES[0]
            original = target.read_bytes()
            target.unlink()
            external = base / 'external.md'
            external.write_bytes(original)
            try:
                target.symlink_to(external)
            except OSError:
                self.skipTest('Symlink creation unavailable')
            with self.assertRaises(ValueError):
                self.build_spec(root, metadata)
