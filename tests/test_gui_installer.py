"""GUI smoke uses real Tk widgets only when a display is available."""
import os
import unittest


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
