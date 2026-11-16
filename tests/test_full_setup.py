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

    @patch("tools.full_setup.dependency_status")
    @patch("tools.full_setup.universal_chef")
    def test_workbuddy_routes_to_native_project_adapter(self, adapter, status):
        status.return_value = self.status
        adapter.inspect.return_value = {"host": "workbuddy", "status": "PREVIEW",
                                         "conflicts": []}
        adapter.install.return_value = {"host": "workbuddy",
                                         "status": "FILES_VERIFIED"}
        replies = iter(["YES", "NO"])
        result = full_setup.run(host="workbuddy", project="/tmp/example",
                                interactive=True, workspace=True,
                                test_agents=True, input_fn=lambda _: next(replies))
        self.assertEqual(result["core_install"], "FILES_VERIFIED")
        self.assertEqual(result["workspace"], "CODEX_ONBOARDING_ONLY")
        self.assertEqual(result["live_agents"], "CANCELLED")
        self.assertEqual(self.pre.call_count, 0)
        adapter.install.assert_called_once()

    @patch("tools.full_setup.chef_runtime_dispatch.run",
           return_value={"status": "REVIEW_REQUIRED",
                         "native_subagent": "NOT_VERIFIED"})
    @patch("tools.full_setup.dependency_status")
    @patch("tools.full_setup.universal_chef")
    def test_workbuddy_real_host_probe_requires_second_consent(
            self, adapter, status, runtime):
        status.return_value = self.status
        adapter.inspect.return_value = {"status": "PREVIEW", "conflicts": []}
        adapter.install.return_value = {"status": "FILES_VERIFIED"}
        replies = iter(["YES", "YES"])
        outcome = full_setup.run(host="workbuddy", project="/tmp/example",
                                 interactive=True, test_agents=True,
                                 input_fn=lambda _: next(replies))
        self.assertEqual(outcome["live_agents"], "REVIEW_REQUIRED")
        self.assertEqual(outcome["native_subagents"], "NOT_VERIFIED")
        runtime.assert_called_once()
        self.assertTrue(runtime.call_args.kwargs["allow_quota"])

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
