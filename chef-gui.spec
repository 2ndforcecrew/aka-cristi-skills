# Candidate one-file/windowed Windows build. Only nine explicit public data files.
# PyInstaller executes this reviewed spec as Python; never load an untrusted spec.
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(SPECPATH).resolve()))
from tools.fs_safety import checked_path

root = checked_path(SPECPATH)
commit = os.environ.get('CHEF_SOURCE_COMMIT', '')
if not re.fullmatch(r'[0-9a-f]{40}', commit):
    raise ValueError('CHEF_SOURCE_COMMIT must be the exact reviewed source commit')
public_files = (
    'templates/AGENTS.global.md',
    'agents/research.toml', 'agents/coding.toml', 'agents/qa.toml', 'agents/automation.toml',
    'skills/chef-orchestrator/SKILL.md', 'skills/verified-change-loop/SKILL.md',
    'skills/feature-journey-map/SKILL.md', 'skills/skill-evaluation-gate/SKILL.md',
)
datas, hashes = [], {}
for name in public_files:
    path = checked_path(root / name)
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Missing/nonregular public bundle data: ' + name)
    hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    datas.append((str(path), 'public-source/' + Path(name).parent.as_posix()))
metadata = checked_path(os.environ.get('CHEF_BUILD_METADATA_DIR', str(root / 'build' / 'gui-metadata')))
metadata.mkdir(parents=True, exist_ok=True)
manifest = checked_path(metadata / 'bundled-public-data.json')
manifest.write_text(json.dumps({'source_commit': commit, 'files': hashes}, indent=2, sort_keys=True), encoding='utf-8')
datas.append((str(manifest), '.'))
a = Analysis(
    [str(root / 'tools' / 'gui_installer.py')],
    pathex=[str(root)], binaries=[], datas=datas,
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='AKA-CRISTI-CHEF-Setup', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    uac_admin=False,
)
