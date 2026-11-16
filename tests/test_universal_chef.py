"""Real filesystem tests for portable CHEF configurations, no model calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import universal_chef as uc


class UniversalChefTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = (Path(self.temp.name).resolve() / "user-project")
        self.project.mkdir()

    def test_all_six_project_hosts_preview_without_writes(self):
        for host in ("workbuddy", "claude", "gemini", "opencode", "hermes", "generic"):
            with self.subTest(host=host):
                data = uc.inspect(host, self.project)
                self.assertEqual(data["status"], "PREVIEW")
                self.assertEqual(len(data["files"]), 5)
                self.assertEqual(len(data["skills"]), 0 if host == "hermes" else 4)
                self.assertFalse((self.project / ".aka-chef-install").exists())

    def test_native_agent_and_skill_install_verify_idempotence(self):
        for host in ("workbuddy", "claude", "gemini", "opencode", "generic"):
            project = self.project / host
            project.mkdir()
            uc.install(host, project, apply=True)
            report = uc.verify(host, project)
            self.assertEqual(report["status"], "FILES_VERIFIED")
            self.assertEqual(report["agent_spawn"], "NOT_RUN")
            second = uc.install(host, project, apply=True)
            self.assertEqual(second["status"], "FILES_VERIFIED")
            mapping = uc.FILES[host]
            for role in uc.ROLES:
                self.assertTrue((project / mapping[1] / ("aka_" + role + ".md")).is_file())
            for skill in uc.SKILLS:
                self.assertTrue((project / mapping[2] / skill / "SKILL.md").is_file())

    def test_existing_user_agents_md_preserved_with_only_managed_block(self):
        for host in ("opencode", "hermes", "generic"):
            project = self.project / host
            project.mkdir()
            original = b"# Existing private project policy\n\nNever delete private assets.\n"
            (project / "AGENTS.md").write_bytes(original)
            uc.install(host, project, apply=True)
            stored = (project / "AGENTS.md").read_bytes()
            self.assertTrue(stored.startswith(original))
            self.assertIn(b"AKA.CRISTI CHEF", stored)
            self.assertEqual(uc.verify(host, project)["status"], "FILES_VERIFIED")

    def test_modified_owned_role_causes_conflict_and_no_writes(self):
        project = self.project
        (project / ".codebuddy" / "agents").mkdir(parents=True)
        target = project / ".codebuddy" / "agents" / "aka_research.md"
        target.write_text("private user agent", encoding="utf-8")
        info = uc.inspect("workbuddy", project)
        self.assertEqual(info["status"], "CONFLICT")
        uc.install("workbuddy", project, apply=True)
        self.assertEqual(target.read_text(encoding="utf-8"), "private user agent")
        self.assertFalse((project / ".codebuddy" / "rules").exists())

    def test_modified_managed_rule_rejected_and_unchanged(self):
        project = self.project
        uc.install("gemini", project, apply=True)
        rules = project / "GEMINI.md"
        altered = rules.read_bytes().replace(b"CHEF role", b"UNSAFE replacement")
        rules.write_bytes(altered)
        self.assertEqual(uc.inspect("gemini", project)["status"], "CONFLICT")
        self.assertEqual(uc.verify("gemini", project)["status"], "FAIL")

    def test_hermes_explicit_user_skill_root(self):
        root = (Path(self.temp.name).resolve() / "isolated-hermes-skills")
        plan = uc.inspect("hermes", self.project, root)
        self.assertEqual(len(plan["skills"]), 4)
        self.assertFalse(root.exists())
        result = uc.install("hermes", self.project, apply=True, hermes_skills_root=root)
        self.assertEqual(result["status"], "FILES_VERIFIED")
        self.assertEqual(result["roles"], "FILES_PRESENT")  # templates, not host-native roles

    def test_user_global_rules_for_supported_hosts(self):
        from unittest.mock import patch
        home = self.project / "mock-home"
        home.mkdir()
        with patch("pathlib.Path.home", return_value=home):
            for host in ("workbuddy", "claude", "gemini", "opencode"):
                with self.subTest(host=host):
                    result = uc.install(host, apply=True, scope="user")
                    self.assertEqual(result["status"], "FILES_VERIFIED")
                    rule, roles, skills = uc.USER_FILES[host]
                    self.assertTrue((home / rule).is_file())
                    self.assertTrue((home / roles / "aka_research.md").is_file())
                    self.assertTrue((home / skills / "chef-orchestrator" / "SKILL.md").is_file())
            with self.assertRaises(ValueError):
                uc.inspect("hermes", scope="user")

    def test_symlink_ancestor_fails_closed(self):
        alias = self.project / "linked"
        target = self.project / "real"
        target.mkdir()
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ValueError):
            uc.inspect("workbuddy", alias)

    def test_uninstall_preserves_existing_rules_and_archives_owned_skills(self):
        original = b"# Private rules intact\n"
        path = self.project / "AGENTS.md"
        path.write_bytes(original)
        uc.install("opencode", self.project, apply=True)
        preview = uc.uninstall("opencode", self.project)
        self.assertEqual(preview["status"], "UNINSTALL_PREVIEW")
        self.assertIn(b"AKA.CRISTI", path.read_bytes())
        result = uc.uninstall("opencode", self.project, apply=True)
        self.assertEqual(result["status"], "UNINSTALLED")
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.project / ".opencode" / "agents" / "aka_qa.md").exists())
        self.assertFalse((self.project / ".opencode" / "skills" / "chef-orchestrator").exists())

    def test_modified_agent_blocks_uninstall(self):
        uc.install("workbuddy", self.project, apply=True)
        target = self.project / ".codebuddy" / "agents" / "aka_qa.md"
        target.write_text("custom edited", encoding="utf-8")
        result = uc.uninstall("workbuddy", self.project, apply=True)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertEqual(target.read_text(encoding="utf-8"), "custom edited")

    def test_codex_reuses_existing_native_core(self):
        with patch.object(uc.quick_install, "execute", return_value={"status": "PREVIEW"}) as mocked:
            data = uc.inspect("codex")
            self.assertEqual(data["host"], "codex")
            mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
