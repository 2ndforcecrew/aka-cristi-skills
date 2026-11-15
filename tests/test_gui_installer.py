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
