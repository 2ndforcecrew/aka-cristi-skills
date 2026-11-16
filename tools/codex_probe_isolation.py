"""Fail-closed Codex probe identity and MCP configuration preflight.

Separates probe configuration and environment from everyday Codex settings.
This does NOT provide filesystem/network OS sandboxing.  Interactive auth must
be performed explicitly in a dedicated home; never copy host auth.json.
"""
from __future__ import annotations

import os
from pathlib import Path
import tomllib


class IsolationError(RuntimeError):
    """Preconditions for isolated execution were not met."""


def _resolved(path):
    return Path(path).expanduser().resolve()


def probe_environment(workspace, *, environ=None):
    """Return dedicated CODEX_HOME and a minimal subprocess environment."""
    env = dict(os.environ if environ is None else environ)
    custom_home = env.get("AKA_CODEX_PROBE_HOME", "").strip()
    if not custom_home:
        raise IsolationError("AKA_CODEX_PROBE_HOME is not set")
    home = _resolved(custom_home)
    host_home = _resolved(Path.home() / ".codex")
    configured_host = env.get("CODEX_HOME")
    if home == host_home or (configured_host and home == _resolved(configured_host)):
        raise IsolationError("Probe home must differ from the existing host Codex home")
    if not home.is_dir() or home.is_symlink():
        raise IsolationError("Dedicated probe home does not exist")
    if home == workspace.resolve() or home in workspace.resolve().parents:
        raise IsolationError("Probe home must not be the workspace or its ancestor")
    config = home / "config.toml"
    if config.is_symlink():
        raise IsolationError("Symlinked probe configuration is not permitted")
    if config.exists():
        try:
            obj = tomllib.loads(config.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise IsolationError("Invalid probe configuration") from exc
        if any(str(k).lower().startswith(("mcp", "plugin", "hook")) for k in obj):
            raise IsolationError("MCP, plugin and hook registrations are forbidden")
    safe = {"CODEX_HOME": str(home)}
    for name in ("PATH", "Path", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP",
                 "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                 "COMSPEC", "PATHEXT"):
        if env.get(name):
            safe[name] = env[name]
    return home, safe
