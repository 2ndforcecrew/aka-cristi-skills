"""Isolated OAuth tests: never access browser, network or real credential stores."""
from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from tools.workspace_auth import AuthClient, AuthError, DEVICE_URL, _native_store


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[service, username] = password

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


class Response(io.BytesIO):
    def __init__(self, url: str, result: object):
        super().__init__(json.dumps(result).encode())
        self.url = url

    def geturl(self) -> str:
        return self.url


class FastCancel(threading.Event):
    def __init__(self) -> None:
        super().__init__()
        self.waits: list[float | None] = []

    def wait(self, timeout: float | None = None) -> bool:
        self.waits.append(timeout)
        return self.is_set()


class AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "settings"
        self.store = MemoryStore()
        self.calls: list[object] = []
        self.results: list[object] = []
        self.browser = patch("tools.workspace_auth.webbrowser.open", return_value=True).start()
        self.addCleanup(patch.stopall)
        self.client = AuthClient(self.directory, "registered-public-id", self.store, self.request)
        self.challenge = {"device_code": "private-device-code", "user_code": "ABCD-EFGH",
                          "verification_uri": DEVICE_URL, "interval": 1, "expires_in": 600}
        self.access = {"access_token": "secret_token_123", "token_type": "bearer", "scope": "repo"}

    def request(self, req: object, **kwargs: object) -> Response:
        self.calls.append(req)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return Response(getattr(req, "full_url"), result)

    def fail(self, code: str, action: object) -> None:
        with self.assertRaises(AuthError) as caught:
            action()  # type: ignore[operator]
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)
        self.assertNotIn("secret", str(caught.exception))

    def test_success_verifies_identity_before_secure_persistence(self) -> None:
        self.results = [self.challenge, self.access, {"login": "aka-cristi"}]
        callback = Mock()
        result = self.client.connect(FastCancel(), on_challenge=callback)
        self.assertEqual(result, {"login": "aka-cristi", "secure_storage": True})
        callback.assert_called_once_with({"verification_uri": DEVICE_URL, "user_code": "ABCD-EFGH"})
        self.browser.assert_called_once_with(DEVICE_URL)
        self.assertEqual(self.store.get_password(self.client.service, "github-oauth"), "secret_token_123")
        self.assertFalse(self.directory.exists())
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])
        user_request = self.calls[-1]
        self.assertEqual(getattr(user_request, "headers")["Authorization"], "Bearer secret_token_123")

    def test_inspect_always_checks_remote_identity(self) -> None:
        self.store.set_password(self.client.service, "github-oauth", "secret_token_123")
        self.results = [{"login": "new-user"}, {"login": "another-user"}]
        self.assertEqual(self.client.inspect_account()["login"], "new-user")
        self.assertEqual(self.client.inspect_account()["login"], "another-user")
        self.assertEqual(len(self.calls), 2)

    def test_pending_and_slowdown(self) -> None:
        self.results = [self.challenge, {"error": "authorization_pending"},
                        {"error": "slow_down"}, self.access, {"login": "user"}]
        cancel = FastCancel()
        self.client.connect(cancel)
        self.assertEqual(cancel.waits, [1, 1, 6])

    def test_denied_and_expired(self) -> None:
        for error, code in [("access_denied", "AUTH_DENIED"), ("expired_token", "AUTH_EXPIRED")]:
            self.results = [self.challenge, {"error": error, "error_description": "secret"}]
            self.fail(code, lambda: self.client.connect(FastCancel()))
            self.assertFalse(self.store.values)

    def test_cancel_before_request(self) -> None:
        cancel = FastCancel()
        cancel.set()
        self.fail("AUTH_CANCELLED", lambda: self.client.connect(cancel))
        self.assertFalse(self.calls)

    def test_cancel_after_challenge(self) -> None:
        self.results = [self.challenge]
        cancel = FastCancel()
        self.fail("AUTH_CANCELLED", lambda: self.client.connect(cancel, on_challenge=lambda _: cancel.set()))
        self.assertFalse(self.store.values)
        self.browser.assert_not_called()

    def test_timeout(self) -> None:
        with patch("tools.workspace_auth.time.monotonic", side_effect=[0, 0, 181, 181]):
            self.results = [self.challenge]
            self.fail("AUTH_TIMEOUT", lambda: self.client.connect(FastCancel()))
        self.assertFalse(self.store.values)

    def test_network_failure_is_sanitized(self) -> None:
        for error in [urllib.error.URLError("secret-token"), TimeoutError("secret-token")]:
            self.results = [error]
            self.fail("NETWORK_ERROR", lambda: self.client.connect(FastCancel()))

    def test_missing_id_does_not_touch_store_or_network(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            client = AuthClient(self.directory, store=Mock(), request=Mock())
        self.fail("OAUTH_CLIENT_ID_REQUIRED", client.connect)
        self.assertFalse(self.calls)

    def test_plaintext_chainer_and_unavailable_backends_refused(self) -> None:
        import sys
        for module, name in [("keyrings.alt.file", "PlaintextKeyring"),
                             ("keyring.backends.chainer", "ChainerBackend"),
                             ("keyring.backends.fail", "Keyring")]:
            backend = type(name, (), {"__module__": module, "priority": 1})()
            with patch.dict(sys.modules, {"keyring": Mock(get_keyring=lambda: backend)}):
                self.fail("SECURE_STORAGE_REQUIRED", _native_store)

    def test_native_backend_whitelist(self) -> None:
        import sys
        for module, name in [("keyring.backends.Windows", "WinVaultKeyring"),
                             ("keyring.backends.macOS", "Keyring"),
                             ("keyring.backends.SecretService", "Keyring")]:
            backend = type(name, (), {"__module__": module, "priority": 1})()
            with patch.dict(sys.modules, {"keyring": Mock(get_keyring=lambda: backend)}):
                self.assertIs(_native_store(), backend)

    def test_redirect_refused(self) -> None:
        self.results = [urllib.error.HTTPError("https://github.com", 302, "secret", {}, None)]
        self.fail("REDIRECT_REFUSED", lambda: self.client.connect(FastCancel()))
        redirected = Response("https://evil.example", {"login": "user"})
        self.client._request = Mock(return_value=redirected)
        self.fail("REDIRECT_REFUSED", lambda: self.client.connect(FastCancel()))

    def test_malicious_challenge_url_refused(self) -> None:
        self.results = [{**self.challenge, "verification_uri": "https://evil.example"}]
        self.fail("INVALID_RESPONSE", lambda: self.client.connect(FastCancel()))
        self.browser.assert_not_called()

    def test_api_paths_refused_before_token_read(self) -> None:
        for path in ["https://evil.example", "//evil.example", "/../user", "/%2e%2e/user", "/user#fragment", "/\\evil"]:
            self.fail("INVALID_API_PATH", lambda: self.client.api("GET", path))
        self.assertFalse(self.calls)

    def test_api_list_and_404(self) -> None:
        self.store.set_password(self.client.service, "github-oauth", "secret_token_123")
        self.results = [[], urllib.error.HTTPError("https://api.github.com", 404, "secret", {}, None)]
        self.assertEqual(self.client.api("GET", "/repos/user/repo/git/matching-refs/heads/"), [])
        self.fail("HTTP_404", lambda: self.client.api("GET", "/repos/user/repo"))

    def test_bad_identity_never_stores_token(self) -> None:
        self.results = [self.challenge, self.access, {"login": "invalid/name"}]
        self.fail("INVALID_ACCOUNT", lambda: self.client.connect(FastCancel()))
        self.assertFalse(self.store.values)

    def test_malformed_token_response_uses_fixed_error(self) -> None:
        for result in [{"error": {"raw": "secret"}}, {**self.access, "token_type": []}]:
            self.results = [self.challenge, result]
            expected = "INVALID_RESPONSE" if "error" in result else "INVALID_CREDENTIAL"
            self.fail(expected, lambda: self.client.connect(FastCancel()))
            self.assertFalse(self.store.values)

    def test_response_size_bound_and_no_logs(self) -> None:
        self.client._request = Mock(return_value=Response(
            "https://github.com/login/device/code", {"secret": "x" * (4 * 1024 * 1024)}))
        with patch("sys.stdout", new_callable=io.StringIO) as stdout, patch(
            "sys.stderr", new_callable=io.StringIO
        ) as stderr:
            self.fail("RESPONSE_TOO_LARGE", lambda: self.client.connect(FastCancel()))
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(self.directory.exists())

    def test_credential_namespace_and_disconnect(self) -> None:
        other = AuthClient(self.directory / "other", store=self.store)
        self.assertNotEqual(self.client.service, other.service)
        self.store.set_password(self.client.service, "github-oauth", "first")
        self.store.set_password(other.service, "github-oauth", "other")
        self.client.disconnect()
        self.assertIsNone(self.store.get_password(self.client.service, "github-oauth"))
        self.assertEqual(self.store.get_password(other.service, "github-oauth"), "other")


if __name__ == "__main__":
    unittest.main()
