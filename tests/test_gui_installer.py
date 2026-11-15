"""GUI smoke uses real Tk widgets only when a display is available."""
import os
import time
import types
import unittest
from unittest.mock import Mock, patch


class FakeWorkspaceController:
    """Stand-in for tools.personal_workspace.WorkspaceController; mock only."""

    def __init__(self, repository=None):
        self.repository = repository
        self.calls = []

    def status(self):
        return {"github_account": "test-account" if self.repository else None,
                "repository": self.repository, "sync_status": "NOT_RUN",
                "chatgpt_status": "NOT_CONNECTED"}

    def preview_changes(self):
        self.calls.append("preview")
        return {"changes": [], "conflicts": [], "source_revision": "abc"}

    def sync_now(self, confirmed=False):
        self.calls.append("sync")
        return {"status": "SYNCED", "backup_id": "backup-1", "source_revision": "abc"}

    def repository_url(self):
        self.calls.append("repository_url")
        return "https://github.com/test-account/my-agent-workspace" if self.repository else ""


@unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "No graphical display")
class InstallerWorkspaceTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from tools.gui_installer import InstallerWindow
        self.fake_controller = FakeWorkspaceController()
        factory = Mock(return_value=self.fake_controller)
        module = types.ModuleType("tools.personal_workspace")
        setattr(module, "WorkspaceController", factory)
        self._modules_patch = patch.dict("sys.modules", {"tools.personal_workspace": module})
        self._modules_patch.start()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = InstallerWindow(self.root)
        self.root.update_idletasks()

    def tearDown(self):
        self.app.busy = False
        self.root.destroy()
        self._modules_patch.stop()

    def finish(self):
        deadline = time.monotonic() + 3
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy)

    def test_offer_workspace_three_choices(self):
        with patch.object(self.app, "open_workspace", return_value=Mock()) as open_workspace:
            workspace = open_workspace.return_value
            with patch("tkinter.messagebox.askyesnocancel", return_value=True):
                self.app.offer_workspace()
            open_workspace.assert_called_once_with(wizard=True)
            workspace.start_one_click.assert_called_once_with()
        with patch.object(self.app, "open_workspace", return_value=Mock()) as open_workspace:
            workspace = open_workspace.return_value
            with patch("tkinter.messagebox.askyesnocancel", return_value=False):
                self.app.offer_workspace()
            open_workspace.assert_called_once_with(wizard=True)
            workspace.start_one_click.assert_not_called()
        with patch.object(self.app, "open_workspace", return_value=Mock()) as open_workspace:
            workspace = open_workspace.return_value
            with patch("tkinter.messagebox.askyesnocancel", return_value=None):
                self.app.offer_workspace()
            open_workspace.assert_not_called()
            workspace.start_one_click.assert_not_called()

    def test_completion_buttons_disabled_without_repository(self):
        self.assertEqual(str(self.app.workspace_sync_button["state"]), "disabled")
        self.assertEqual(str(self.app.workspace_open_button["state"]), "disabled")

    def test_completion_buttons_enabled_with_repository(self):
        self.fake_controller.repository = "test-account/my-agent-workspace"
        self.app.events.put(("install", {"status": "FILES_VERIFIED", "journal": {"id": "journal-1"}}))
        with patch("tkinter.messagebox.askyesnocancel", return_value=None):
            self.app.poll()
            self.root.update_idletasks()
        self.assertEqual(str(self.app.workspace_sync_button["state"]), "normal")
        self.assertEqual(str(self.app.workspace_open_button["state"]), "normal")

    def test_workspace_sync_calls_preview_then_sync(self):
        self.fake_controller.repository = "test-account/my-agent-workspace"
        self.app._refresh_workspace_buttons()
        with patch("tkinter.messagebox.askyesno", return_value=True) as confirm:
            self.app.workspace_sync_button.invoke()
            self.finish()
        confirm.assert_called_once()
        self.assertEqual(self.fake_controller.calls, ["preview", "sync"])

    def test_workspace_open_repository_calls_repository_url(self):
        self.fake_controller.repository = "test-account/my-agent-workspace"
        self.app._refresh_workspace_buttons()
        with patch("webbrowser.open") as open_url:
            self.app.workspace_open_button.invoke()
            self.finish()
        self.assertEqual(self.fake_controller.calls, ["repository_url"])
        open_url.assert_called_once_with("https://github.com/test-account/my-agent-workspace")

    def test_workspace_buttons_refresh_when_window_closes(self):
        fake_window = types.SimpleNamespace(closed=False, controller=self.fake_controller)
        self.app.workspace_windows.append(fake_window)
        self.fake_controller.repository = "test-account/my-agent-workspace"
        self.app.poll()
        self.root.update_idletasks()
        self.assertEqual(str(self.app.workspace_sync_button["state"]), "disabled")
        fake_window.closed = True
        self.app.poll()
        self.root.update_idletasks()
        self.assertEqual(str(self.app.workspace_sync_button["state"]), "normal")
        self.assertEqual(str(self.app.workspace_open_button["state"]), "normal")


class GuiTests(unittest.TestCase):
    def test_dependency_inspection_does_not_claim_activation(self):
        from tools.gui_installer import prerequisites
        report = prerequisites()
        self.assertEqual(report["activation"], "NOT_RUN")
        self.assertIn(report["codex"], ("AVAILABLE", "MISSING"))

    @unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "No graphical display")
    def test_real_window_preview_and_consent_controls(self):
        import tkinter as tk
        from tools.gui_installer import InstallerWindow
        window = tk.Tk()
        try:
            app = InstallerWindow(window)
            window.update_idletasks()
            self.assertEqual(str(app.install_button["state"]), "disabled")
            self.assertFalse(app.consent.get())
            self.assertFalse(app.trusted.get())
            self.assertIn("NOT_RUN", app.status.get())
            self.assertTrue(app.diff.winfo_exists())
        finally:
            window.destroy()


class FrozenDataTests(unittest.TestCase):
    def test_unfrozen_default_is_repository(self):
        from tools.gui_installer import default_source
        from pathlib import Path
        self.assertEqual(default_source(), Path(__file__).resolve().parents[1])

    def test_frozen_manifest_requires_exact_public_files_and_hashes(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools import gui_installer as gui
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            files = {}
            for name in gui.BUNDLED_PUBLIC_FILES:
                path = root / "public-source" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic public data")
                files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = root / "bundled-public-data.json"
            manifest.write_text(json.dumps({"source_commit": "a" * 40, "files": files}))
            with patch.object(gui.sys, "frozen", True, create=True), patch.object(gui.sys, "_MEIPASS", str(root), create=True):
                self.assertEqual(gui.default_source(), root / "public-source")
                (root / "public-source" / gui.BUNDLED_PUBLIC_FILES[0]).write_text("tampered")
                with self.assertRaises(ValueError):
                    gui.default_source()

    def test_frozen_manifest_rejects_unexpected_paths(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools import gui_installer as gui
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "bundled-public-data.json").write_text(json.dumps({"source_commit": "a" * 40, "files": {"../auth.json": "b" * 64}}))
            with patch.object(gui.sys, "frozen", True, create=True), patch.object(gui.sys, "_MEIPASS", str(root), create=True):
                with self.assertRaises(ValueError):
                    gui.default_source()
