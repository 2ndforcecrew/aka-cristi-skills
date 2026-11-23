"""Fail-closed Codex probe environment regression: no real agents or secrets."""
import tempfile
import unittest
from pathlib import Path

from tools.codex_probe_isolation import IsolationError, probe_environment

# Must mirror the allowlist in tools/codex_probe_isolation.py exactly.
# Any key outside this set must never reach a child CLI process.
ALLOWED_PROBE_ENV_KEYS = frozenset({
    "CODEX_HOME", "PATH", "Path", "SystemRoot", "SYSTEMROOT", "WINDIR",
    "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA",
    "LOCALAPPDATA", "COMSPEC", "PATHEXT",
})
SECRET_SENTINELS = ("SECRET_TOKEN", "GH_TOKEN", "OPENAI_API_KEY")


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


class ProbeIsolationAdversarialTests(unittest.TestCase):
    """E-247-1: pin the preflight's fail-closed behaviour, nothing more.

    These tests assert what probe_environment() actually does. Where the
    literal WP-D wording differs from the code, the test pins the code and
    the docstring says so -- see test_host_codex_home_value_is_overridden
    and test_symlinked_home_is_canonicalized.
    """

    def test_auth_json_in_dedicated_home_is_never_read_or_copied(self):
        sentinel = "SENTINEL-auth-do-not-copy-2471"
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            workspace = Path(d) / "case"
            workspace.mkdir()
            (home / "auth.json").write_text(
                '{"access_token": "' + sentinel + '"}', encoding="utf-8")
            before = (home / "auth.json").read_bytes()
            resolved, env = probe_environment(
                workspace,
                environ={"AKA_CODEX_PROBE_HOME": str(home),
                         "SECRET_TOKEN": sentinel, "PATH": "safe"})
            self.assertEqual(resolved, home.resolve())
            self.assertEqual(env["CODEX_HOME"], str(home.resolve()))
            self.assertTrue(set(env) <= ALLOWED_PROBE_ENV_KEYS)
            self.assertNotIn("SECRET_TOKEN", env)
            self.assertFalse(any(sentinel in str(v) for v in env.values()))
            # The file itself is untouched, and no copy leaked into workspace.
            self.assertEqual((home / "auth.json").read_bytes(), before)
            self.assertFalse((workspace / "auth.json").exists())
            self.assertFalse(any(p.name == "auth.json"
                                 for p in workspace.iterdir()))

    def test_nested_mcp_plugin_hook_registrations_rejected(self):
        configs = {
            "mcp_servers nested": '[mcp_servers.x]\ncommand="node"\n',
            "plugins nested": '[plugins.x]\nenabled=true\n',
            "hooks nested": '[hooks.x]\ncommand="x"\n',
            "mcp_servers bare": '[mcp_servers]\nfoo={command="node"}\n',
            "mcp exact": '[mcp]\ncommand="node"\n',
            "uppercase MCP_SERVERS": '[MCP_SERVERS.x]\ncommand="node"\n',
            "mixed-case Plugins": '[Plugins.x]\nenabled=true\n',
            "uppercase HOOKS": '[HOOKS.x]\ncommand="x"\n',
            "mixed-case McpServers": '[McpServers.x]\ncommand="node"\n',
        }
        for label, text in configs.items():
            with self.subTest(config=label):
                with tempfile.TemporaryDirectory() as d:
                    home = Path(d) / "probe"
                    home.mkdir()
                    (home / "config.toml").write_text(text, encoding="utf-8")
                    with self.assertRaises(IsolationError):
                        probe_environment(
                            Path(d) / "case",
                            environ={"AKA_CODEX_PROBE_HOME": str(home)})

    def test_benign_config_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            (home / "config.toml").write_text(
                '[model]\nname="gpt-test"\n', encoding="utf-8")
            resolved, env = probe_environment(
                Path(d) / "case",
                environ={"AKA_CODEX_PROBE_HOME": str(home), "PATH": "safe"})
            self.assertEqual(resolved, home.resolve())
            self.assertTrue(set(env) <= ALLOWED_PROBE_ENV_KEYS)

    def test_probe_home_equal_to_configured_codex_home_rejected(self):
        # Rejection fires when the probe home itself equals the host home
        # or equals the pre-configured CODEX_HOME value.
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            with self.subTest(case="AKA home == CODEX_HOME value"):
                with self.assertRaises(IsolationError):
                    probe_environment(
                        Path(d) / "case",
                        environ={"AKA_CODEX_PROBE_HOME": str(home),
                                 "CODEX_HOME": str(home)})
            with self.subTest(case="AKA home == host ~/.codex"):
                host_home = str(Path.home() / ".codex")
                with self.assertRaises(IsolationError):
                    probe_environment(
                        Path(d) / "case",
                        environ={"AKA_CODEX_PROBE_HOME": host_home,
                                 "CODEX_HOME": host_home})

    def test_host_codex_home_value_is_overridden_not_inherited(self):
        # Literal WP-D wording ("CODEX_HOME pointing at host home is
        # rejected") does NOT match the code: when AKA_CODEX_PROBE_HOME is
        # a dedicated home, a stray host CODEX_HOME is silently replaced
        # by the dedicated home in the returned env, not rejected. This
        # test pins that override behaviour; rejection only triggers when
        # the probe home itself equals the host/configured home (above).
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            resolved, env = probe_environment(
                Path(d) / "case",
                environ={"AKA_CODEX_PROBE_HOME": str(home),
                         "CODEX_HOME": str(Path.home() / ".codex"),
                         "PATH": "safe"})
            self.assertEqual(resolved, home.resolve())
            self.assertEqual(env["CODEX_HOME"], str(home.resolve()))
            self.assertNotEqual(env["CODEX_HOME"],
                                str(Path.home() / ".codex"))

    def test_symlinked_home_is_canonicalized_not_rejected(self):
        # probe_environment() resolves the home BEFORE the is_symlink()
        # check, so a symlink to a real directory is canonicalized and
        # accepted -- the is_symlink() branch cannot fire for the home
        # itself. Pin the actual behaviour here; rejecting symlinked
        # homes would need a tools/ change (check before resolve()).
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real"
            real.mkdir()
            link = Path(d) / "link"
            link.symlink_to(real, target_is_directory=True)
            resolved, env = probe_environment(
                Path(d) / "case",
                environ={"AKA_CODEX_PROBE_HOME": str(link)})
            self.assertEqual(resolved, real.resolve())
            self.assertEqual(env["CODEX_HOME"], str(real.resolve()))

    def test_symlink_to_host_home_is_rejected(self):
        # Canonicalization still protects the host home: a symlink that
        # resolves onto ~/.codex is rejected by the host-home check.
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / "link"
            link.symlink_to(Path.home() / ".codex", target_is_directory=True)
            with self.assertRaises(IsolationError):
                probe_environment(
                    Path(d) / "case",
                    environ={"AKA_CODEX_PROBE_HOME": str(link)})

    def test_dangling_symlink_home_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / "link"
            link.symlink_to(Path(d) / "missing", target_is_directory=True)
            with self.assertRaises(IsolationError):
                probe_environment(
                    Path(d) / "case",
                    environ={"AKA_CODEX_PROBE_HOME": str(link)})

    def test_secret_env_vars_outside_allowlist_are_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "probe"
            home.mkdir()
            environ = {"AKA_CODEX_PROBE_HOME": str(home), "PATH": "safe"}
            for name in SECRET_SENTINELS:
                environ[name] = "sentinel-" + name
            environ["AWS_SECRET_ACCESS_KEY"] = "sentinel-aws"
            _, env = probe_environment(Path(d) / "case", environ=environ)
            self.assertTrue(set(env) <= ALLOWED_PROBE_ENV_KEYS)
            for name in list(SECRET_SENTINELS) + ["AWS_SECRET_ACCESS_KEY"]:
                self.assertNotIn(name, env)
            self.assertFalse(any("sentinel-" in str(v) for v in env.values()))


if __name__ == "__main__":
    unittest.main()
