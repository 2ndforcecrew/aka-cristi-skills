import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.chef_global_rules import GlobalRulesError, START, END, apply, plan


class GlobalRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "fake-codex"
        self.template = self.base / "public-template.md"
        self.template.write_text("# CHEF\n\nOnly public principles.\n", encoding="utf-8")
        self.rules = self.home / "AGENTS.md"

    def test_preview_does_not_touch_home(self):
        x = apply("install", self.template, self.home)
        self.assertEqual(x["state"], "create")
        self.assertFalse(self.home.exists())

    def test_create_verify_uninstall(self):
        x = apply("install", self.template, self.home, confirmed=True)
        self.assertTrue(x["applied"])
        self.assertIn(START, self.rules.read_text())
        self.assertEqual(plan("verify", self.template, self.home)["state"], "PASS")
        x = apply("uninstall", self.template, self.home, confirmed=True)
        self.assertTrue(x["applied"])
        self.assertEqual(plan("verify", self.template, self.home)["state"], "NOT_INSTALLED")

    def test_existing_rules_untouched_outside_managed_block(self):
        self.home.mkdir()
        original = "# Existing global rules\nDo not overwrite.\n"
        self.rules.write_text(original, encoding="utf-8")
        self.assertEqual(apply("install", self.template, self.home)["state"], "append")
        x = apply("install", self.template, self.home, confirmed=True)
        self.assertTrue(Path(x["backup"]).exists())
        text = self.rules.read_text()
        self.assertTrue(text.startswith(original.rstrip("\n")))
        x = apply("uninstall", self.template, self.home, confirmed=True)
        self.assertEqual(self.rules.read_text(), original)
        self.assertTrue(Path(x["backup"]).exists())

    def test_append_preserves_existing_bytes_and_trailing_blank_lines(self):
        self.home.mkdir()
        for original in (b"private policy\r\nnext\r\n", b"private policy\n\n\n", b"\n\n"):
            self.rules.write_bytes(original)
            apply("install", self.template, self.home, confirmed=True)
            self.assertTrue(self.rules.read_bytes().startswith(original))

    def test_equivalent_crlf_managed_block_is_verified_without_rewrite(self):
        from tools.chef_global_rules import managed_block
        self.home.mkdir()
        original = ("private rules\r\n\r\n" + managed_block(self.template).replace("\n", "\r\n") + "\r\n").encode()
        self.rules.write_bytes(original)
        self.assertEqual(plan("verify", self.template, self.home)["state"], "PASS")
        self.assertFalse(apply("install", self.template, self.home, confirmed=True)["applied"])
        self.assertEqual(self.rules.read_bytes(), original)
        self.assertEqual(plan("uninstall", self.template, self.home)["state"], "remove_managed_block")

    def test_idempotent_install(self):
        apply("install", self.template, self.home, confirmed=True)
        self.assertFalse(apply("install", self.template, self.home, confirmed=True)["applied"])

    def test_modified_managed_block_must_not_be_overwritten(self):
        apply("install", self.template, self.home, confirmed=True)
        self.rules.write_text(self.rules.read_text().replace("Only public", "Privately edited"),
                              encoding="utf-8")
        before = self.rules.read_text()
        self.assertEqual(plan("install", self.template, self.home)["state"], "conflict_modified")
        with self.assertRaises(GlobalRulesError):
            apply("uninstall", self.template, self.home, confirmed=True)
        with self.assertRaises(GlobalRulesError):
            apply("install", self.template, self.home, confirmed=True)
        self.assertEqual(self.rules.read_text(), before)

    def test_mismatched_markers_fail_closed(self):
        self.home.mkdir()
        self.rules.write_text("Original\n" + START, encoding="utf-8")
        with self.assertRaises(GlobalRulesError):
            plan("install", self.template, self.home)

    def test_symlink_target_refused(self):
        target = self.base / "outside.md"
        target.write_text("sensitive", encoding="utf-8")
        self.home.mkdir()
        try:
            self.rules.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unsupported in test runner")
        with self.assertRaises(GlobalRulesError):
            plan("install", self.template, self.home)
        self.assertEqual(target.read_text(), "sensitive")

    def test_failed_atomic_write_preserves_concurrent_user_edit_and_backup(self):
        self.home.mkdir()
        original = b"original policy\r\n\r\n"
        changed = b"concurrent user policy\r\n"
        self.rules.write_bytes(original)
        def interrupted_write(path, text):
            path.write_bytes(changed)
            raise OSError("simulated failed commit")
        with patch("tools.chef_global_rules.write_atomic", side_effect=interrupted_write):
            with self.assertRaises(OSError):
                apply("install", self.template, self.home, confirmed=True)
        self.assertEqual(self.rules.read_bytes(), changed)
        backups = list((self.home / ".aka-chef-backups").glob("*.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_failed_atomic_write_does_not_recreate_concurrently_deleted_rules(self):
        self.home.mkdir()
        self.rules.write_bytes(b"original policy\n")
        def interrupted_write(path, text):
            path.unlink()
            raise OSError("simulated failed commit")
        with patch("tools.chef_global_rules.write_atomic", side_effect=interrupted_write):
            with self.assertRaises(OSError):
                apply("install", self.template, self.home, confirmed=True)
        self.assertFalse(self.rules.exists())
        self.assertEqual(len(list((self.home / ".aka-chef-backups").glob("*.md"))), 1)

    def test_failed_write_retains_original_bytes_and_allows_retry(self):
        self.home.mkdir()
        original = b"original policy\r\n\r\n"
        self.rules.write_bytes(original)
        with patch("tools.chef_global_rules.write_atomic", side_effect=OSError("before commit")):
            with self.assertRaises(OSError):
                apply("install", self.template, self.home, confirmed=True)
        self.assertEqual(self.rules.read_bytes(), original)
        result = apply("install", self.template, self.home, confirmed=True)
        self.assertTrue(result["applied"])
        self.assertTrue(self.rules.read_bytes().startswith(original))

    def test_wrong_template_not_accepted(self):
        self.template.write_text(START + "\nunsafe\n" + END, encoding="utf-8")
        with self.assertRaises(GlobalRulesError):
            plan("install", self.template, self.home)

    def test_public_repository_template_has_no_private_identity(self):
        template = Path(__file__).resolve().parents[1] / "templates" / "AGENTS.global.md"
        content = template.read_text(encoding="utf-8")
        self.assertIn("INSPECT", content)
        self.assertNotIn("2ndforcecrew@gmail.com", content)
        self.assertNotIn("PRIVATE KEY", content)


if __name__ == "__main__":
    unittest.main()
