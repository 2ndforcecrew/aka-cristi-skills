"""Fail-closed Codex probe environment regression: no real agents or secrets."""
import tempfile
import unittest
from pathlib import Path

from tools.codex_probe_isolation import IsolationError, probe_environment


class ProbeIsolationTests(unittest.TestCase):
    def test_missing_home_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(IsolationError):
                probe_environment(Path(d), environ={})

    def test_dedicated_home_drops_secret_environment(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            workspace = Path(d) / "case"
            workspace.mkdir()
            resolved, env = probe_environment(
                workspace,
                environ={"AKA_CODEX_PROBE_HOME": str(home),
                         "SECRET_TOKEN": "do-not-copy", "PATH": "safe"},
            )
            self.assertEqual(resolved, home.resolve())
            self.assertEqual(env["CODEX_HOME"], str(home.resolve()))
            self.assertNotIn("SECRET_TOKEN", env)

    def test_mcp_registration_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            (home / "config.toml").write_text(
                '[mcp_servers.foo]\ncommand="node"\n', encoding="utf-8"
            )
            with self.assertRaises(IsolationError):
                probe_environment(Path(d) / "case",
                                  environ={"AKA_CODEX_PROBE_HOME": str(home)})

    def test_plugin_configuration_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            (home / "config.toml").write_text(
                '[plugins.foo]\nenabled=true\n', encoding="utf-8"
            )
            with self.assertRaises(IsolationError):
                probe_environment(Path(d) / "case",
                                  environ={"AKA_CODEX_PROBE_HOME": str(home)})


if __name__ == "__main__":
    unittest.main()
