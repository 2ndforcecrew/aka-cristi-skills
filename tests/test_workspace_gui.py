"""Isolated real Tk adapter tests; no account, network, or user configuration."""
from __future__ import annotations

import gc
import os
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch
from typing import Any


class FakeOneClickSetup:
    """Stand-in for tools.workspace_oneclick.OneClickSetup; mock only."""

    def __init__(self, controller: Any = None, on_step: Any = None, result: dict[str, Any] | None = None):
        self.controller = controller
        self.on_step = on_step
        self.runs: list[dict[str, Any]] = []
        self.result: dict[str, Any] = result if result is not None else {
            "status": "COMPLETED", "completed": ["connect", "repository", "initialize", "preview", "sync", "chatgpt"],
            "step": "chatgpt", "code": None, "repository": "test-account/my-agent-workspace",
            "sync_status": "SYNCED", "chatgpt_status": "PENDING_VERIFICATION"}

    def plan(self) -> dict[str, Any]:
        return {"steps": [
            {"name": "connect", "writes": "GitHub Device Flow 授權（不寫檔案）"},
            {"name": "repository", "writes": "建立私人倉庫 my-agent-workspace"},
            {"name": "initialize", "writes": "寫入 10 個公開檔案到私人倉庫"},
            {"name": "preview", "writes": "無寫入（僅預覽本地差異）"},
            {"name": "sync", "writes": "備份後拉取公開檔案到本機 Codex/Skills 目錄（直接套用預覽差異，不再二次確認）"},
            {"name": "chatgpt", "writes": "僅打開官方指南，不寫憑據"}]}

    def run(self, confirmed: bool = False, cancel_event: Any = None, on_challenge: Any = None) -> dict[str, Any]:
        self.runs.append({"confirmed": confirmed, "cancel_event": cancel_event, "on_challenge": on_challenge})
        if self.on_step is not None:
            for step in ("connect", "repository", "initialize", "preview", "sync", "chatgpt"):
                self.on_step(step, "done")
        return dict(self.result)


class FakeController:
    def __init__(self, directory: Path):
        self.directory = directory
        self.calls: list[Any] = []
        self.account: str | None = None
        self.chatgpt_status = "NOT_CONNECTED"
        self.one_click_setup: Any = None
        self.one_click_result: dict[str, Any] | None = None
        self.one_click_setup_factory: Any = FakeOneClickSetup

    def status(self) -> dict[str, Any]:
        return {"github_account": self.account, "repository": "my-agent-workspace", "sync_status": "NOT_RUN", "chatgpt_status": self.chatgpt_status}

    def configure_oauth_client(self, client_id: str) -> None:
        self.calls.append(("oauth_client", client_id))

    def connect(self, cancel_event: Any = None, on_challenge: Any = None) -> None:
        self.calls.append("connect")
        self.account = "test-account"

    def disconnect(self, confirmed: bool = False) -> None:
        self.calls.append(("disconnect", confirmed))
        self.account = None

    def one_click(self, on_step: Any = None) -> FakeOneClickSetup:
        self.calls.append("one_click")
        setup = self.one_click_setup_factory(self, on_step, result=self.one_click_result)
        self.one_click_setup = setup
        return setup

    def preview_changes(self) -> dict[str, Any]:
        self.calls.append("preview")
        return {"changes": [{"path": "rules/AGENTS.md", "action": "update", "diff": "+public change"}], "conflicts": []}

    def select_repository(self, **kwargs: Any) -> None:
        self.calls.append(("repository", kwargs))

    def initialize(self, **kwargs: Any) -> None:
        self.calls.append(("initialize", kwargs))

    def sync_now(self, **kwargs: Any) -> None:
        self.calls.append(("sync", kwargs))

    def restore_previous(self, backup_id: str, **kwargs: Any) -> None:
        self.calls.append(("restore", backup_id, kwargs))

    def backup_history(self) -> list[dict[str, str]]:
        return [{"id": "backup-1", "created_at": "2026-11-16", "status": "READY"}]

    def __getattr__(self, name: str) -> Any:
        return lambda *args, **kwargs: self.calls.append(name)


@unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "No graphical display")
class WorkspaceGuiTests(unittest.TestCase):
    def setUp(self) -> None:
        import tkinter as tk
        from tools.workspace_gui import WorkspaceWindow
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.controller = FakeController(self.directory)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = WorkspaceWindow(self.root, self.controller, wizard=True)
        self.root.update_idletasks()

    def tearDown(self) -> None:
        self.app.busy = False
        self.app.close()
        self.root.destroy()
        # Drop the app/root references and collect on the main thread:
        # otherwise the cyclic GC may finalize Tk variables of this
        # destroyed window from a later test's worker thread, and
        # Python 3.11 aborts (Tcl_AsyncDelete: async handler deleted by
        # the wrong thread). Main-thread finalization is safe.
        del self.app, self.root
        gc.collect()
        self.assertEqual(list(self.directory.iterdir()), [])
        self.temp.cleanup()

    def finish(self) -> None:
        deadline = time.monotonic() + 3
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy)

    def test_widgets_and_github_never_claim_chatgpt_connected(self) -> None:
        self.assertEqual(len(self.app.tabs.tabs()), 3)
        self.assertEqual(self.app.tabs.select(), str(self.app.setup_page))
        self.app.connect_button.invoke()
        self.finish()
        self.assertIn("test-account", self.app.account.get())
        self.assertEqual(self.app.chatgpt.get(), "ChatGPT：NOT_CONNECTED")

    def test_disconnect_button_requires_confirmation_and_refreshes_account(self) -> None:
        self.controller.account = "test-account"
        with patch.object(self.app, "_confirm", return_value=False):
            self.app.disconnect_button.invoke()
        self.assertNotIn(("disconnect", True), self.controller.calls)
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.disconnect_button.invoke()
            self.finish()
        self.assertIn(("disconnect", True), self.controller.calls)
        self.assertEqual(self.app.account.get(), "GitHub：未连接")
        self.assertEqual(self.app.chatgpt.get(), "ChatGPT：NOT_CONNECTED")

    def test_write_confirmations_and_snapshot(self) -> None:
        with patch.object(self.app, "_confirm", return_value=False):
            self.app.select_repository(False)
            self.app.initialize()
            self.app.sync()
        self.assertEqual(self.controller.calls, [])
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.repository.set("chosen-repo")
            self.app.select_repository(True)
            self.app.repository.set("edited-later")
            self.finish()
            self.assertEqual(self.controller.calls[0], ("repository", {"name": "chosen-repo", "confirmed": True, "reuse": True}))
            self.app.initialize()
            self.finish()
            self.app.sync()
            self.finish()
        self.assertIn(("sync", {"confirmed": True}), self.controller.calls)

    def test_installer_constructor_readonly_and_explicit_first_run(self) -> None:
        from tools.gui_installer import InstallerWindow
        factory = Mock()
        factory.return_value.status.return_value = {"wizard_needed": True}
        module = types.ModuleType("tools.personal_workspace")
        setattr(module, "WorkspaceController", factory)
        with patch.dict("sys.modules", {"tools.personal_workspace": module}):
            installer = InstallerWindow(self.root)
            factory.assert_not_called()
            with patch.object(installer, "open_workspace") as open_workspace:
                installer.first_run_workspace()
                open_workspace.assert_called_once_with(wizard=True)

    def test_installer_close_waits_for_workspace(self) -> None:
        from tools.gui_installer import InstallerWindow
        installer = InstallerWindow(self.root)
        installer.workspace_windows.append(self.app)
        gate = threading.Event()
        self.app.start("check", lambda: gate.wait(2))
        installer.close()
        self.assertFalse(self.app.cancel_event.is_set())
        self.assertIn("无法中途取消", self.app.status.get())
        self.assertTrue(self.root.winfo_exists())
        gate.set()
        self.finish()

    def test_public_oauth_configuration_and_input_snapshot(self) -> None:
        self.assertEqual(self.app.oauth_client_id.get(), "")
        self.app.oauth_client_id.set("maintainer-public-id")
        self.app.configure_oauth_button.invoke()
        self.assertEqual(str(self.app.oauth_entry["state"]), "disabled")
        self.app.oauth_client_id.set("edited-later")
        self.finish()
        self.assertIn(("oauth_client", "maintainer-public-id"), self.controller.calls)

    def test_close_while_busy_requests_cancel(self) -> None:
        gate = threading.Event()
        self.app.start("connect", lambda: gate.wait(2))
        self.app.close()
        self.assertFalse(self.app.closed)
        self.assertTrue(self.app.cancel_event.is_set())
        self.assertTrue(self.app.window.winfo_exists())
        gate.set()
        self.finish()

    def test_repository_collision_requires_explicit_reuse(self) -> None:
        self.app.start("repository", lambda: {"status": "REUSE_REQUIRED"})
        self.finish()
        self.assertIn("REUSE_REQUIRED", self.app.status.get())
        self.assertIn("使用已有 private 仓库", self.app.status.get())
        self.assertIn("修改名称", self.app.status.get())
        self.assertNotIn("操作完成", self.app.status.get())

    def test_failed_sync_reports_recovery_status(self) -> None:
        for status in ("FAILED_ROLLED_BACK", "BLOCKED_ROLLBACK_REQUIRED"):
            with self.subTest(status=status):
                self.app.start("sync", lambda: {"status": status})
                self.finish()
                self.assertIn(status, self.app.status.get())
                self.assertNotIn("操作完成", self.app.status.get())

    def test_cancel_enabled_only_for_authorization(self) -> None:
        for kind in ("sync", "restore", "initialize", "repository", "connect"):
            with self.subTest(kind=kind):
                gate = threading.Event()
                self.app.start(kind, lambda: gate.wait(2))
                expected = "normal" if kind == "connect" else "disabled"
                self.assertEqual(str(self.app.cancel_button["state"]), expected)
                self.app.cancel()
                self.assertEqual(self.app.cancel_event.is_set(), kind == "connect")
                gate.set()
                self.finish()

    def test_preview_and_backup_restore(self) -> None:
        self.app.preview_button.invoke()
        self.finish()
        self.assertIn("+public change", self.app.output.get("1.0", "end"))
        self.app.start("backups", self.controller.backup_history)
        self.finish()
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.restore_button.invoke()
            self.finish()
        self.assertIn(("restore", "backup-1", {"confirmed": True}), self.controller.calls)

    def test_worker_disables_controls_and_redacts_exceptions(self) -> None:
        gate = threading.Event()
        def operation() -> None:
            gate.wait(2)
            raise ValueError("secret-token-must-never-appear")
        self.app.start("connect", operation)
        self.assertEqual(str(self.app.create_button["state"]), "disabled")
        self.assertEqual(str(self.app.backup_combo["state"]), "disabled")
        self.app.timeout = 0
        self.app.poll()
        self.assertTrue(self.app.cancel_event.is_set())
        self.assertTrue(self.app.busy)
        gate.set()
        self.finish()
        self.assertNotIn("secret-token", self.app.status.get())
        self.assertNotIn("secret-token", self.app.output.get("1.0", "end"))

    def test_challenge_stays_busy_and_is_not_logged(self) -> None:
        gate = threading.Event()
        self.app.start("connect", lambda: gate.wait(2))
        self.app.events.put(("challenge", {"user_code": "ABCD-EFGH", "verification_uri": "https://github.com/login/device"}))
        self.app.poll()
        self.assertTrue(self.app.busy)
        self.assertIn("ABCD-EFGH", self.app.status.get())
        self.assertNotIn("ABCD-EFGH", self.app.output.get("1.0", "end"))
        gate.set()
        self.finish()

    def test_one_click_button_runs_setup_and_shows_completion(self) -> None:
        self.assertEqual(str(self.app.oneclick_button["state"]), "normal")
        self.assertEqual(self.app.completion_frame.winfo_manager(), "")
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.oneclick_button.invoke()
            self.finish()
        self.assertIn("one_click", self.controller.calls)
        setup = self.controller.one_click_setup
        self.assertEqual(len(setup.runs), 1)
        self.assertTrue(setup.runs[0]["confirmed"])
        self.root.update_idletasks()
        self.assertEqual(self.app.completion_frame.winfo_manager(), "pack")
        summary = self.app.completion_summary.get()
        self.assertIn("test-account/my-agent-workspace", summary)
        self.assertIn("SYNCED", summary)
        self.assertIn("PENDING_VERIFICATION", summary)
        self.assertNotIn("Connected", summary)
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.completion_sync_button.invoke()
            self.finish()
        self.assertIn(("sync", {"confirmed": True}), self.controller.calls)
        self.app.completion_open_button.invoke()
        self.finish()
        self.assertIn("repository_url", self.controller.calls)

    def test_one_click_challenge_code_shown_in_status_not_output(self) -> None:
        gate = threading.Event()

        class ChallengingSetup(FakeOneClickSetup):
            def run(self, confirmed: bool = False, cancel_event: Any = None, on_challenge: Any = None) -> dict[str, Any]:
                self.runs.append({"confirmed": confirmed, "cancel_event": cancel_event, "on_challenge": on_challenge})
                if on_challenge is not None:
                    on_challenge({"user_code": "ABCD-EFGH", "verification_uri": "https://github.com/login/device"})
                gate.wait(2)
                return dict(self.result)

        self.controller.one_click_setup_factory = ChallengingSetup
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.oneclick_button.invoke()
        deadline = time.monotonic() + 3
        while "ABCD-EFGH" not in self.app.status.get() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertIn("ABCD-EFGH", self.app.status.get())
        self.assertNotIn("ABCD-EFGH", self.app.output.get("1.0", "end"))
        gate.set()
        self.finish()
        self.assertEqual(self.app.completion_frame.winfo_manager(), "pack")

    def test_one_click_failure_shows_step_code_without_completed(self) -> None:
        self.controller.one_click_result = {"status": "STOPPED", "completed": ["connect"],
                                            "step": "repository", "code": "REPO_NOT_PRIVATE",
                                            "repository": None, "sync_status": "NOT_RUN",
                                            "chatgpt_status": "NOT_CONNECTED"}
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.oneclick_button.invoke()
            self.finish()
        self.assertIn("repository", self.app.status.get())
        self.assertIn("REPO_NOT_PRIVATE", self.app.status.get())
        self.assertNotIn("操作完成", self.app.status.get())
        self.assertEqual(self.app.completion_frame.winfo_manager(), "")

    def test_one_click_declined_runs_nothing(self) -> None:
        with patch.object(self.app, "_confirm", return_value=False):
            self.app.oneclick_button.invoke()
        self.assertFalse(self.app.busy)
        self.assertIsNotNone(self.controller.one_click_setup)
        self.assertEqual(self.controller.one_click_setup.runs, [])
        self.assertEqual(self.app.completion_frame.winfo_manager(), "")

    def test_one_click_cancel_enabled_during_run(self) -> None:
        gate = threading.Event()

        class BlockingSetup(FakeOneClickSetup):
            def run(self, confirmed: bool = False, cancel_event: Any = None, on_challenge: Any = None) -> dict[str, Any]:
                self.runs.append({"confirmed": confirmed, "cancel_event": cancel_event, "on_challenge": on_challenge})
                gate.wait(2)
                return dict(self.result)

        self.controller.one_click_setup_factory = BlockingSetup
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.oneclick_button.invoke()
        self.assertEqual(str(self.app.cancel_button["state"]), "normal")
        self.app.cancel()
        self.assertTrue(self.app.cancel_event.is_set())
        gate.set()
        self.finish()

    def test_one_click_uses_lazy_import_without_controller_factory(self) -> None:
        calls: list[Any] = []

        class ImportedSetup(FakeOneClickSetup):
            def __init__(self, controller: Any = None, on_step: Any = None, result: Any = None):
                calls.append(controller)
                super().__init__(controller, on_step, result=result)

        fake_module = types.ModuleType("tools.workspace_oneclick")
        setattr(fake_module, "OneClickSetup", ImportedSetup)

        class NoOneClickController(FakeController):
            one_click = None  # type: ignore[assignment]

        self.app.controller = NoOneClickController(self.directory)
        with patch.dict("sys.modules", {"tools.workspace_oneclick": fake_module}):
            with patch.object(self.app, "_confirm", return_value=True):
                self.app.oneclick_button.invoke()
                self.finish()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.app.completion_frame.winfo_manager(), "pack")

    def test_one_click_cancel_disabled_after_connect_done(self) -> None:
        gate = threading.Event()

        class ConnectDoneSetup(FakeOneClickSetup):
            def run(self, confirmed: bool = False, cancel_event: Any = None, on_challenge: Any = None) -> dict[str, Any]:
                self.runs.append({"confirmed": confirmed, "cancel_event": cancel_event, "on_challenge": on_challenge})
                if self.on_step is not None:
                    self.on_step("connect", "started")
                    self.on_step("connect", "done")
                gate.wait(5)
                if self.on_step is not None:
                    for step in ("repository", "initialize", "preview", "sync", "chatgpt"):
                        self.on_step(step, "done")
                return dict(self.result)

        self.controller.one_click_setup_factory = ConnectDoneSetup
        with patch.object(self.app, "_confirm", return_value=True):
            self.app.oneclick_button.invoke()
        deadline = time.monotonic() + 3
        while str(self.app.cancel_button["state"]) != "disabled" and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(str(self.app.cancel_button["state"]), "disabled")
        self.app.cancel()
        self.assertFalse(self.app.cancel_event.is_set())
        self.assertIn("授權已完成", self.app.status.get())
        gate.set()
        self.finish()
        self.assertEqual(self.app.completion_frame.winfo_manager(), "pack")


if __name__ == "__main__":
    unittest.main()
