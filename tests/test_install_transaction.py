"""Real filesystem transaction tests; no runtime activation is simulated."""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import install_transaction as txn

REPO = Path(__file__).resolve().parents[1]


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "codex"
        self.skills = self.root / "skills"

    def preview(self):
        return txn.preview(REPO, self.home, self.skills)

    def test_preview_readonly_has_rules_diff(self):
        plan = self.preview()
        self.assertFalse(self.home.exists())
        self.assertIn("AKA.CRISTI CHEF GLOBAL START", plan["rules_diff"])
        self.assertEqual(len(plan["additions"]), 8)
        self.assertEqual(plan["activation"], "NOT_RUN")

    def test_apply_needs_explicit_consent(self):
        with self.assertRaises(txn.TransactionError):
            txn.install(self.preview(), consent=False)
        self.assertFalse(self.home.exists())

    def test_stale_preview_refuses_all_writes(self):
        plan = self.preview()
        self.home.mkdir()
        (self.home / "AGENTS.md").write_text("new private rules", encoding="utf-8")
        with self.assertRaises(txn.TransactionError):
            txn.install(plan, consent=True)
        self.assertEqual((self.home / "AGENTS.md").read_text(), "new private rules")
        self.assertFalse(self.skills.exists())

    def test_install_undo_preserves_original_rules_and_unrelated_files(self):
        self.home.mkdir()
        original = b"personal policy\r\n"
        (self.home / "AGENTS.md").write_bytes(original)
        (self.home / "other.txt").write_text("keep")
        result = txn.install(self.preview(), consent=True)
        self.assertEqual(result["status"], "FILES_VERIFIED")
        self.assertEqual(result["activation"], "NOT_RUN")
        self.assertTrue((self.skills / "chef-orchestrator" / "SKILL.md").exists())
        undo = txn.rollback(result["journal"], consent=True)
        self.assertEqual(undo["status"], "ROLLED_BACK")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), original)
        self.assertEqual((self.home / "other.txt").read_text(), "keep")
        self.assertFalse((self.skills / "chef-orchestrator").exists())

    def test_rollback_refuses_modified_install(self):
        result = txn.install(self.preview(), consent=True)
        path = self.home / "AGENTS.md"
        path.write_text(path.read_text() + "\nnew rule")
        with self.assertRaises(txn.TransactionError):
            txn.rollback(result["journal"], consent=True)
        self.assertIn("new rule", path.read_text())

    def test_cancel_during_install_restores_completed_steps(self):
        cancelled = threading.Event()
        events = []
        def progress(event):
            events.append(event)
            if event == "rules_installed":
                cancelled.set()
        result = txn.install(self.preview(), consent=True, cancel=cancelled, progress=progress)
        self.assertEqual(result["status"], "CANCELLED_ROLLED_BACK")
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertFalse((self.skills / "chef-orchestrator").exists())

    def test_partial_failure_restores_every_changed_file(self):
        with patch("tools.install_transaction.codex_subagents.install", side_effect=OSError("private error")):
            result = txn.install(self.preview(), consent=True)
        self.assertEqual(result["status"], "FAILED_ROLLED_BACK")
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertFalse((self.skills / "chef-orchestrator").exists())
        self.assertNotIn("private error", str(result))

    def test_conflict_does_not_modify_existing_skill(self):
        p = self.skills / "chef-orchestrator"
        p.mkdir(parents=True)
        (p / "SKILL.md").write_text("private skill")
        with self.assertRaises(txn.TransactionError):
            self.preview()
        self.assertEqual((p / "SKILL.md").read_text(), "private skill")

    def test_symlink_parent_refused(self):
        self.home.mkdir()
        link = self.root / "linked"
        try:
            link.symlink_to(self.home, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises((txn.TransactionError, ValueError)):
            txn.preview(REPO, link / "nested", self.skills)

    def test_rollback_preserves_preexisting_empty_managed_directories(self):
        original = self.home / ".aka-chef-backups" / "empty-original"
        original.mkdir(parents=True)
        result = txn.install(self.preview(), consent=True)
        txn.rollback(result["journal"], consent=True)
        self.assertTrue(original.is_dir())

    def test_rollback_refuses_new_empty_directory(self):
        result = txn.install(self.preview(), consent=True)
        (self.skills / "chef-orchestrator" / "user-empty-folder").mkdir()
        with self.assertRaises(txn.TransactionError):
            txn.rollback(result["journal"], consent=True)

    def test_concurrent_edit_during_failed_step_blocks_automatic_rollback(self):
        def failed_step(*args, **kwargs):
            path = self.home / "AGENTS.md"
            path.write_text(path.read_text() + "\nconcurrent private edit")
            raise OSError("private details")
        with patch("tools.install_transaction.skill_installer.install", side_effect=failed_step):
            result = txn.install(self.preview(), consent=True)
        self.assertEqual(result["status"], "BLOCKED_ROLLBACK_REQUIRED")
        self.assertIn("concurrent private edit", (self.home / "AGENTS.md").read_text())
        self.assertNotIn("private details", str(result))

    def test_concurrent_edit_after_successful_step_blocks_automatic_rollback(self):
        real_install = txn.skill_installer.install
        def changed_step(*args, **kwargs):
            result = real_install(*args, **kwargs)
            path = self.home / "AGENTS.md"
            path.write_text(path.read_text() + "\nconcurrent edit")
            return result
        with patch("tools.install_transaction.skill_installer.install", side_effect=changed_step):
            result = txn.install(self.preview(), consent=True)
        self.assertEqual(result["status"], "BLOCKED_ROLLBACK_REQUIRED")
        self.assertIn("concurrent edit", (self.home / "AGENTS.md").read_text())

    def test_second_install_is_idempotent_and_undo_leaves_first_install(self):
        txn.install(self.preview(), consent=True)
        before = (self.home / "AGENTS.md").read_bytes()
        result = txn.install(self.preview(), consent=True)
        self.assertEqual(result["status"], "FILES_VERIFIED")
        txn.rollback(result["journal"], consent=True)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), before)
        self.assertTrue((self.skills / "chef-orchestrator" / "SKILL.md").exists())

    def test_same_or_overlapping_roots_refused(self):
        for skills in (self.home, self.home / "skills"):
            with self.assertRaises(txn.TransactionError):
                txn.preview(REPO, self.home, skills)


if __name__ == "__main__":
    unittest.main()
