"""Manual workspace pull integration tests: real isolated files, no transport."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.workspace_sync import SyncEngine, WorkspaceSyncError


def snapshot(content=b"# public rules\n", extra=None):
    files = {"rules/AGENTS.md": content, **(extra or {})}
    entries = []
    for path, data in files.items():
        target = "codex/AGENTS.md" if path == "rules/AGENTS.md" else (
            "codex/" + path if path.startswith("agents/") else path)
        entries.append({"path": path, "target": target,
                        "sha256": hashlib.sha256(data).hexdigest()})
    return {"schema_version": 1, "owner": "alice", "repository": "my-agent-workspace",
            "sync_mode": "manual", "files": entries}, files


class WorkspaceSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home, self.skills = self.root / "codex", self.root / "skills"
        self.engine = SyncEngine(self.root / "state", self.home, self.skills)

    def tearDown(self):
        self.temp.cleanup()

    def preview(self, content=b"# public rules\n", extra=None, engine=None):
        manifest, files = snapshot(content, extra)
        return (engine or self.engine).preview(manifest, files, "a" * 40)

    def sync(self, content=b"# public rules\n", extra=None, engine=None):
        target = engine or self.engine
        return target.apply(self.preview(content, extra, target), confirmed=True)

    def test_first_pull_preserves_unrelated_files_and_requires_consent(self):
        self.home.mkdir()
        (self.home / "notes.txt").write_text("mine")
        plan = self.preview(extra={"skills/my-skill/SKILL.md": b"# My skill\n"})
        self.assertIn("+# public rules", plan["changes"][0]["diff"])
        with self.assertRaises(WorkspaceSyncError):
            self.engine.apply(plan)
        result = self.engine.apply(plan, confirmed=True)
        self.assertEqual(result["status"], "SYNCED")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"# public rules\n")
        self.assertEqual((self.home / "notes.txt").read_text(), "mine")
        self.assertEqual(self.engine.installed_skills(), [{"name": "my-skill", "status": "INSTALLED"}])
        self.assertEqual(len(self.engine.backups()), 1)

    def test_two_machines_update_independently(self):
        other = SyncEngine(self.root / "other-state", self.root / "other-home", self.root / "other-skills")
        self.sync()
        self.sync(engine=other)
        self.sync(b"# version two\n")
        self.assertEqual((other.codex_home / "AGENTS.md").read_bytes(), b"# public rules\n")
        self.sync(b"# version two\n", engine=other)
        self.assertEqual((other.codex_home / "AGENTS.md").read_bytes(), b"# version two\n")

    def test_unowned_different_conflicts_equal_adopts_with_backup(self):
        self.home.mkdir()
        target = self.home / "AGENTS.md"
        target.write_bytes(b"personal")
        plan = self.preview()
        self.assertTrue(plan["conflicts"])
        with self.assertRaises(WorkspaceSyncError):
            self.engine.apply(plan, confirmed=True)
        target.write_bytes(b"# public rules\n")
        adopted = self.sync()
        self.assertTrue(adopted["backup_id"])
        self.sync(b"new\n")
        target.write_bytes(b"user edit\n")
        self.assertTrue(self.preview(b"third\n")["conflicts"])

    def test_stale_preview_and_tampered_source_plan_blocked(self):
        plan = self.preview()
        self.home.mkdir()
        (self.home / "AGENTS.md").write_bytes(b"concurrent")
        with self.assertRaises(WorkspaceSyncError):
            self.engine.apply(plan, confirmed=True)
        (self.home / "AGENTS.md").unlink()
        plan = self.preview()
        plan["source_revision"] = "b" * 40
        with self.assertRaises(WorkspaceSyncError):
            self.engine.apply(plan, confirmed=True)

    def test_restore_refuses_user_edit_then_restores_and_preserves_original_mode(self):
        self.home.mkdir()
        target = self.home / "AGENTS.md"
        target.write_bytes(b"# public rules\n")
        os.chmod(target, 0o640)
        self.sync()
        result = self.sync(b"new\n")
        target.write_bytes(b"my edit\n")
        with self.assertRaises(WorkspaceSyncError):
            self.engine.restore(result["backup_id"], confirmed=True)
        target.write_bytes(b"new\n")
        self.assertEqual(self.engine.restore(result["backup_id"], confirmed=True)["status"], "RESTORED")
        self.assertEqual(target.read_bytes(), b"# public rules\n")
        if os.name != "nt":
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_failure_rolls_back_and_retry_works(self):
        real_write = self.engine._write_target
        calls = 0

        def fail_second(path, data, mode):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated private error")
            return real_write(path, data, mode)

        with patch.object(self.engine, "_write_target", side_effect=fail_second):
            result = self.sync(extra={"agents/reviewer.toml": b'name = "Reviewer"\n'})
        self.assertEqual(result["status"], "FAILED_ROLLED_BACK")
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertEqual(self.sync()["status"], "SYNCED")

    def test_concurrent_mutation_is_never_authorized_as_rollback(self):
        real_write = self.engine._write_target
        calls = 0

        def concurrent(path, data, mode):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.home / "AGENTS.md").write_bytes(b"user raced write")
                raise OSError("unrelated private error")
            return real_write(path, data, mode)

        with patch.object(self.engine, "_write_target", side_effect=concurrent):
            result = self.sync(extra={"agents/reviewer.toml": b'name = "Reviewer"\n'})
        self.assertEqual(result["status"], "BLOCKED_ROLLBACK_REQUIRED")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"user raced write")

    def test_edited_backup_refused(self):
        result = self.sync()
        ledger = json.loads((self.root / "state" / "state.json").read_text())
        backup = self.root / "state" / "backups" / ledger["backups"][result["backup_id"]]["receipt"]
        record = json.loads(backup.read_text())
        record["source_revision"] = "b" * 40
        backup.write_text(json.dumps(record))
        with self.assertRaises(WorkspaceSyncError):
            self.engine.restore(result["backup_id"], confirmed=True)

    def test_invalid_manifest_identity_path_hash_revision_and_secrets(self):
        for field, value in [("schema_version", 2), ("sync_mode", "push"), ("owner", "../alice"),
                             ("repository", "../repo")]:
            manifest, files = snapshot()
            manifest[field] = value
            with self.assertRaises(WorkspaceSyncError):
                self.engine.preview(manifest, files, "a" * 40)
        for path in ["skills/demo/../auth.json", "skills/demo/.env", "skills/CON/SKILL.md",
                     "agents/../auth.toml", "skills/demo/chats/history.json"]:
            manifest, files = snapshot(extra={path: b"x"})
            with self.assertRaises(WorkspaceSyncError):
                self.engine.preview(manifest, files, "a" * 40)
        manifest, files = snapshot()
        manifest["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(WorkspaceSyncError):
            self.engine.preview(manifest, files, "a" * 40)
        manifest, files = snapshot()
        with self.assertRaises(WorkspaceSyncError):
            self.engine.preview(manifest, files, "main")
        manifest, files = snapshot(b'github_token = "ghp_1234567890abcdefghijklmnopqrstuv"\n')
        with self.assertRaises(WorkspaceSyncError):
            self.engine.preview(manifest, files, "a" * 40)

    def test_audit_sanitized_permissions_and_symlinks(self):
        self.sync(b"# public special-user-content\n")
        audit = json.dumps(self.engine.audit_log())
        self.assertNotIn("special-user-content", audit)
        self.assertNotIn(str(self.root), audit)
        self.assertNotIn("alice", audit)
        if os.name != "nt":
            self.assertEqual((self.root / "state").stat().st_mode & 0o777, 0o700)
            self.assertEqual((self.root / "state" / "state.json").stat().st_mode & 0o777, 0o600)
            linked = self.root / "linked"
            linked.symlink_to(self.home, target_is_directory=True)
            with self.assertRaises(WorkspaceSyncError):
                SyncEngine(self.root / "state2", linked, self.root / "skills2")
        with self.assertRaises(WorkspaceSyncError):
            SyncEngine(self.home / "state", self.home, self.skills)

    def test_initial_status_reads_do_not_create_directories(self):
        self.assertEqual(self.engine.backups(), [])
        self.assertEqual(self.engine.installed_skills(), [])
        self.assertEqual(self.engine.audit_log(), [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cross_process_lock_is_exclusive(self):
        script = (
            "import sys; from tools.workspace_sync import SyncEngine,WorkspaceSyncError; "
            "e=SyncEngine(*sys.argv[1:]); "
            "\ntry:\n e.backups()\nexcept WorkspaceSyncError as exc:\n print(exc.code)\n")
        with self.engine._lock():
            result = subprocess.run([sys.executable, "-c", script, str(self.root / "state"),
                                     str(self.home), str(self.skills)], capture_output=True,
                                    text=True, timeout=10, check=True)
        self.assertEqual(result.stdout.strip(), "SYNC_BUSY")

    def test_restore_failure_rolls_back_and_can_retry(self):
        first = {"agents/reviewer.toml": b'name = "First"\n'}
        second = {"agents/reviewer.toml": b'name = "Second"\n'}
        self.sync(extra=first)
        result = self.sync(b"# update\n", extra=second)
        real_write = self.engine._write_target
        calls = 0

        def fail_second(path, data, mode):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("private failure")
            return real_write(path, data, mode)

        with patch.object(self.engine, "_write_target", side_effect=fail_second):
            restored = self.engine.restore(result["backup_id"], confirmed=True)
        self.assertEqual(restored["status"], "FAILED_ROLLED_BACK")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"# update\n")
        self.assertEqual(self.engine.restore(result["backup_id"], confirmed=True)["status"], "RESTORED")

    def test_plan_does_not_alias_source_payload_and_remote_omission_never_deletes(self):
        manifest, files = snapshot(extra={"skills/demo/SKILL.md": b"demo"})
        plan = self.engine.preview(manifest, files, "a" * 40)
        files["rules/AGENTS.md"] = b"unverified after preview"
        manifest["owner"] = "mallory"
        self.engine.apply(plan, confirmed=True)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"# public rules\n")
        self.sync(b"next")
        self.assertEqual((self.skills / "demo" / "SKILL.md").read_bytes(), b"demo")

    def test_invalid_payload_duplicates_case_and_limits(self):
        manifest, files = snapshot()
        manifest["files"].append(dict(manifest["files"][0]))
        with self.assertRaises(WorkspaceSyncError):
            self.engine.preview(manifest, files, "a" * 40)
        manifest, files = snapshot(extra={"skills/demo/SKILL.md": b"demo",
                                          "skills/demo/skill.md": b"other"})
        with self.assertRaises(WorkspaceSyncError):
            self.engine.preview(manifest, files, "a" * 40)
        self.sync(extra={"skills/Demo/SKILL.md": b"demo"})
        with self.assertRaises(WorkspaceSyncError):
            self.preview(extra={"skills/demo/SKILL.md": b"demo"})
        manifest, files = snapshot(b"x" * (1024 * 1024 + 1))
        with self.assertRaises(WorkspaceSyncError):
            self.engine.preview(manifest, files, "a" * 40)

    def test_other_profile_cannot_write_same_roots_during_apply(self):
        other = SyncEngine(self.root / "bob-state", self.home, self.skills)
        alice_plan = self.preview(b"alice rules")
        manifest, files = snapshot(b"bob rules")
        manifest["owner"] = "bob"
        bob_plan = other.preview(manifest, files, "b" * 40)
        entered, release = threading.Event(), threading.Event()
        results = []
        real_write = other._write_target

        def blocked_write(path, data, mode):
            entered.set()
            if not release.wait(10):
                raise OSError("test synchronization timeout")
            return real_write(path, data, mode)

        with patch.object(other, "_write_target", side_effect=blocked_write):
            thread = threading.Thread(target=lambda: results.append(other.apply(bob_plan, confirmed=True)))
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises(WorkspaceSyncError) as caught:
                    self.engine.apply(alice_plan, confirmed=True)
                self.assertEqual(caught.exception.code, "SYNC_BUSY")
            finally:
                release.set()
                thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]["status"], "SYNCED")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"bob rules")
        with self.assertRaises(WorkspaceSyncError) as caught:
            self.engine.apply(alice_plan, confirmed=True)
        self.assertEqual(caught.exception.code, "STALE_PREVIEW")

    def test_shared_root_lock_is_cross_process_and_preview_does_not_create_it(self):
        self.preview()
        self.assertFalse(list(self.root.glob(".aka-workspace-lock-*")))
        script = (
            "import sys; from tools.workspace_sync import SyncEngine,WorkspaceSyncError; "
            "e=SyncEngine(*sys.argv[1:]); "
            "\ntry:\n with e._target_lock(): pass\nexcept WorkspaceSyncError as exc:\n print(exc.code)\n")
        with self.engine._target_lock():
            result = subprocess.run([sys.executable, "-c", script, str(self.root / "different-state"),
                                     str(self.home), str(self.root / "different-skills")],
                                    capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(result.stdout.strip(), "SYNC_BUSY")

    def test_final_restore_commit_failure_preserves_receipt_and_retry(self):
        self.sync()
        result = self.sync(b"new rules")
        backup_id = result["backup_id"]
        real_save = self.engine._save_state
        failed = False

        def fail_final(state):
            nonlocal failed
            if not failed and state["backups"][backup_id]["status"] == "RESTORED":
                failed = True
                raise OSError("disk full before ledger commit")
            return real_save(state)

        with patch.object(self.engine, "_save_state", side_effect=fail_final):
            restored = self.engine.restore(backup_id, confirmed=True)
        self.assertEqual(restored["status"], "FAILED_ROLLED_BACK")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"new rules")
        reopened = SyncEngine(self.root / "state", self.home, self.skills)
        self.assertEqual(reopened.restore(backup_id, confirmed=True)["status"], "RESTORED")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"# public rules\n")

    def test_receipt_count_bounded_per_backup_and_other_backups_retained(self):
        extra = {"skills/demo/file" + str(i) + ".md": b"content" * 100 for i in range(40)}
        first = self.sync(extra=extra)
        second = self.sync(b"update", extra={key: value + b" next" for key, value in extra.items()})
        receipts = list((self.root / "state" / "backups").glob("*.json"))
        self.assertEqual(len(receipts), 2)
        self.engine.restore(second["backup_id"], confirmed=True)
        self.assertEqual(len(list((self.root / "state" / "backups").glob("*.json"))), 2)
        self.assertEqual({item["id"] for item in self.engine.backups()}, {first["backup_id"], second["backup_id"]})

    def test_interrupted_restore_recovers_only_persisted_known_progress(self):
        self.sync(extra={"agents/reviewer.toml": b"first"})
        result = self.sync(b"new rules", extra={"agents/reviewer.toml": b"second"})
        real_record = self.engine._record

        def interrupted(record, state):
            real_record(record, state)
            if record["status"] == "RESTORING" and len(record["restore_progress"]) == 1:
                raise KeyboardInterrupt()

        with patch.object(self.engine, "_record", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.engine.restore(result["backup_id"], confirmed=True)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"new rules")
        self.assertEqual((self.home / "agents" / "reviewer.toml").read_bytes(), b"first")
        reopened = SyncEngine(self.root / "state", self.home, self.skills)
        self.assertEqual(reopened.restore(result["backup_id"], confirmed=True)["status"], "RESTORED")
        self.assertEqual((self.home / "agents" / "reviewer.toml").read_bytes(), b"first")

    def test_interrupted_apply_can_restore_known_checkpoint_and_refuses_external_edit(self):
        real_record = self.engine._record

        def interrupted(record, state):
            real_record(record, state)
            if record["status"] == "APPLYING" and record["after"]["rules/AGENTS.md"] is not None:
                raise KeyboardInterrupt()

        with patch.object(self.engine, "_record", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.sync(extra={"agents/reviewer.toml": b"reviewer"})
        backup_id = self.engine.backups()[0]["id"]
        reopened = SyncEngine(self.root / "state", self.home, self.skills)
        (self.home / "AGENTS.md").write_bytes(b"external edit")
        with self.assertRaises(WorkspaceSyncError):
            reopened.restore(backup_id, confirmed=True)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"external edit")
        (self.home / "AGENTS.md").write_bytes(b"# public rules\n")
        self.assertEqual(reopened.restore(backup_id, confirmed=True)["status"], "RESTORED")
        self.assertFalse((self.home / "AGENTS.md").exists())

    def test_cleanup_retains_unreferenced_crash_orphan(self):
        result = self.sync()
        orphan = self.root / "state" / "backups" / (result["backup_id"] + "-" + "0" * 32 + ".json")
        orphan.write_bytes(b"diagnostic crash orphan")
        self.engine.restore(result["backup_id"], confirmed=True)
        self.assertEqual(orphan.read_bytes(), b"diagnostic crash orphan")

    def test_uncheckpointed_restore_write_blocks_recovery(self):
        self.sync(extra={"agents/reviewer.toml": b"first"})
        result = self.sync(b"new rules", extra={"agents/reviewer.toml": b"second"})
        real_record = self.engine._record

        def interrupted_before_checkpoint(record, state):
            if record["status"] == "RESTORING" and record["restore_progress"]:
                raise KeyboardInterrupt()
            real_record(record, state)

        with patch.object(self.engine, "_record", side_effect=interrupted_before_checkpoint):
            with self.assertRaises(KeyboardInterrupt):
                self.engine.restore(result["backup_id"], confirmed=True)
        reopened = SyncEngine(self.root / "state", self.home, self.skills)
        with self.assertRaises(WorkspaceSyncError) as caught:
            reopened.restore(result["backup_id"], confirmed=True)
        self.assertEqual(caught.exception.code, "ROLLBACK_CONFLICT")
        self.assertEqual((self.home / "agents" / "reviewer.toml").read_bytes(), b"first")


if __name__ == "__main__":
    unittest.main()
