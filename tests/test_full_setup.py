"""Tests for one-command setup: previews, opt-in boundaries, and capability status."""
import unittest
from unittest.mock import patch

from tools import full_setup


class FullSetupTests(unittest.TestCase):
    def setUp(self):
        self.status = {
            "python": "3.11", "git": "AVAILABLE", "codex_cli": "MISSING",
            "workspace_keyring": "MISSING", "workspace_oauth_client_id": "NOT_CONFIGURED",
        }
        self.previewer = patch("tools.full_setup.quick_install.execute")
        self.pre = self.previewer.start()
        self.addCleanup(self.previewer.stop)
        self.pre.side_effect = lambda **kw: (
            {"status": "FILES_VERIFIED", "rules": "PASS",
             "roles": {"research": "PASS", "coding": "PASS",
                       "qa": "PASS", "automation": "PASS"},
             "skills": {"chef-orchestrator": "PASS"}} if kw.get("apply")
            else {"status": "PREVIEW", "applied": False}
        )

    @patch("tools.full_setup.dependency_status")
    def test_preview_has_no_install_or_auth(self, status):
        status.return_value = self.status
        result = full_setup.run(workspace=True, test_agents=True)
        self.assertEqual(result["core_install"], "PREVIEW_ONLY")
        self.assertEqual(result["workspace"], "NOT_RUN")
        self.assertEqual(result["live_agents"], "NOT_RUN")
        self.assertEqual(self.pre.call_count, 1)

    @patch("tools.full_setup.dependency_status")
    def test_consent_declined_no_writes(self, status):
        status.return_value = self.status
        result = full_setup.run(interactive=True, workspace=True, input_fn=lambda _: "NO")
        self.assertEqual(result["core_install"], "CANCELLED")
        self.assertEqual(self.pre.call_count, 1)

    @patch("tools.full_setup._call", return_value=False)
    @patch("tools.full_setup.dependency_status")
    def test_install_and_report_missing_optional_capabilities(self, status, call):
        status.return_value = self.status
        result = full_setup.run(interactive=True, workspace=True,
                                test_agents=True, input_fn=lambda _: "YES")
        self.assertEqual(result["core_install"], "FILES_VERIFIED")
        self.assertIn(result["workspace"], ("OAUTH_CLIENT_ID_REQUIRED",
                                            "DEPENDENCY_INSTALL_FAILED"))
        self.assertEqual(result["live_agents"], "CODEX_CLI_MISSING")
        self.assertEqual(call.call_count, 1)

    @patch("tools.full_setup._call", return_value=True)
    @patch("tools.full_setup.dependency_status")
    def test_optional_agent_probe_separate_confirmation(self, status, call):
        status.return_value = {**self.status, "codex_cli": "AVAILABLE",
                               "workspace_keyring": "AVAILABLE"}
        responses = iter(["YES", "NO"])
        result = full_setup.run(interactive=True, test_agents=True,
                                input_fn=lambda _: next(responses))
        self.assertEqual(result["core_install"], "FILES_VERIFIED")
        self.assertEqual(result["live_agents"], "SEPARATE_CONSENT_REQUIRED")
        self.assertEqual(call.call_count, 1)  # codex login status only


if __name__ == "__main__":
    unittest.main()
