import tempfile
import unittest
from pathlib import Path
from tools.codex_subagents import (
    ROLE_NAMES, AgentInstallError, install, plan, uninstall, verify
)


class CodexSubagentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / "codex-home"
        self.original = self.home / "agents" / "research.toml"

    def test_preview_is_readonly(self):
        for role in ROLE_NAMES:
            self.assertEqual(plan(role, self.home)["action"], "INSTALL")
        self.assertFalse(self.home.exists())

    def test_install_and_verify_all_roles(self):
        for role in ROLE_NAMES:
            self.assertTrue(install(role, self.home, apply=True)["applied"])
            result = verify(role, self.home)
            self.assertEqual(result["integrity"], "PASS")
            self.assertEqual(result["agent_spawn"], "NOT_RUN")
        self.assertEqual(len(list((self.home / "agents").glob("*.toml"))), 4)

    def test_existing_unmanaged_role_refused(self):
        self.original.parent.mkdir(parents=True)
        self.original.write_text("name = 'private-research'\n", encoding="utf-8")
        self.assertEqual(plan("research", self.home)["action"], "CONFLICT_UNMANAGED")
        with self.assertRaises(AgentInstallError):
            install("research", self.home, apply=True)
        self.assertEqual(self.original.read_text(), "name = 'private-research'\n")

    def test_modified_role_never_deleted(self):
        install("research", self.home, apply=True)
        self.original.write_text(self.original.read_text() + "\n# user edit\n")
        with self.assertRaises(AgentInstallError):
            uninstall("research", self.home, apply=True)
        self.assertTrue(self.original.exists())

    def test_uninstall_archives_without_destroying(self):
        install("research", self.home, apply=True)
        preview = uninstall("research", self.home)
        self.assertEqual(preview["action"], "UNINSTALL_PREVIEW")
        removed = uninstall("research", self.home, apply=True)
        self.assertTrue(Path(removed["archive"]).exists())
        self.assertFalse(self.original.exists())

    def test_idempotent_install(self):
        install("research", self.home, apply=True)
        self.assertFalse(install("research", self.home, apply=True)["applied"])

    def test_modified_source_upgrades_and_keeps_backup(self):
        source = Path(__file__).resolve().parents[1] / "agents"
        with tempfile.TemporaryDirectory() as td:
            custom = Path(td).resolve()
            for role in ROLE_NAMES:
                (custom / (role + ".toml")).write_bytes((source / (role + ".toml")).read_bytes())
            install("research", self.home, custom, apply=True)
            path = custom / "research.toml"
            path.write_text(path.read_text() + "\n# public update\n")
            self.assertEqual(plan("research", self.home, custom)["action"], "UPGRADE")
            result = install("research", self.home, custom, apply=True)
            self.assertTrue(Path(result["backup"]).exists())

    def test_symlink_target_rejected(self):
        self.home.joinpath("agents").mkdir(parents=True)
        outside = self.home / "outside.toml"
        outside.write_text("preserve")
        try:
            self.original.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        with self.assertRaises(AgentInstallError):
            plan("research", self.home)
        self.assertEqual(outside.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
