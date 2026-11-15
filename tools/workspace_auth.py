"""GitHub public-client device OAuth with native OS credential storage.

Register a GitHub OAuth App and supply its non-secret client ID through
AKA_WORKSPACE_OAUTH_CLIENT_ID. The classic ``repo`` scope includes all repositories
the account authorizes; it is broader than a repository-scoped fine-grained PAT.
No client secret, gh configuration, token files, or plaintext fallback is used.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Callable, Protocol

MAX_JSON_BYTES = 4 * 1024 * 1024
API_ROOT = "https://api.github.com"
DEVICE_URL = "https://github.com/login/device"


class AuthError(ValueError):
    """A fixed, credential-free error suitable for UI display."""

    def __init__(self, code: str):
        self.code = code if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code) else "AUTH_FAILED"
        super().__init__(self.code)


class SecretStore(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise AuthError("REDIRECT_REFUSED")


def _native_store() -> SecretStore:
    try:
        import keyring  # type: ignore[import-not-found,unused-ignore]
        backend = keyring.get_keyring()
        identity = (type(backend).__module__, type(backend).__name__)
        allowed = {
            ("keyring.backends.Windows", "WinVaultKeyring"),
            ("keyring.backends.macOS", "Keyring"),
            ("keyring.backends.SecretService", "Keyring"),
        }
        if identity not in allowed or backend.priority <= 0:
            raise AuthError("SECURE_STORAGE_REQUIRED")
        return backend  # type: ignore[no-any-return,unused-ignore]
    except AuthError:
        raise
    except Exception:
        raise AuthError("SECURE_STORAGE_REQUIRED") from None


class AuthClient:
    def __init__(self, config_dir: Path, client_id: str | None = None,
                 store: SecretStore | None = None,
                 request: Callable[..., Any] | None = None):
        self.client_id = client_id or os.environ.get("AKA_WORKSPACE_OAUTH_CLIENT_ID")
        digest = hashlib.sha256(str(Path(config_dir).resolve()).encode()).hexdigest()
        self.service = "aka-cristi.personal-workspace.oauth." + digest
        self._store = store
        self._request = request
        self._credential = "github-oauth"

    def _storage(self) -> SecretStore:
        if self._store is None:
            self._store = _native_store()
        return self._store

    def _read_token(self) -> str:
        try:
            token = self._storage().get_password(self.service, self._credential)
        except AuthError:
            raise
        except Exception:
            raise AuthError("SECURE_STORAGE_FAILED") from None
        if not token:
            raise AuthError("NOT_CONNECTED")
        return self._validate_token(token)

    @staticmethod
    def _validate_token(token: Any) -> str:
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_\-.]{1,1024}", token):
            raise AuthError("INVALID_CREDENTIAL")
        return token

    def _json(self, method: str, url: str, payload: Any = None,
              token: str | None = None, timeout: float = 30,
              form: bool = False) -> Any:
        headers = {"Accept": "application/json", "User-Agent": "AKA-CRISTI-Workspace"}
        data = None
        if payload is not None:
            try:
                data = (urllib.parse.urlencode(payload).encode() if form else
                        json.dumps(payload, allow_nan=False).encode())
            except Exception:
                raise AuthError("INVALID_PAYLOAD") from None
            if len(data) > MAX_JSON_BYTES:
                raise AuthError("RESPONSE_TOO_LARGE")
            headers["Content-Type"] = ("application/x-www-form-urlencoded" if form
                                       else "application/json")
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            send = self._request or urllib.request.build_opener(_NoRedirect()).open
            with send(req, timeout=max(0.01, min(timeout, 30))) as response:
                if response.geturl() != url:
                    raise AuthError("REDIRECT_REFUSED")
                body = response.read(MAX_JSON_BYTES + 1)
            if len(body) > MAX_JSON_BYTES:
                raise AuthError("RESPONSE_TOO_LARGE")
            result = json.loads(body)
            if not isinstance(result, (dict, list)):
                raise AuthError("INVALID_RESPONSE")
            return result
        except AuthError:
            raise
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400:
                raise AuthError("REDIRECT_REFUSED") from None
            code = error.code if 400 <= error.code < 600 else 500
            raise AuthError(f"HTTP_{code}") from None
        except (TimeoutError, urllib.error.URLError, OSError):
            raise AuthError("NETWORK_ERROR") from None
        except Exception:
            raise AuthError("INVALID_RESPONSE") from None

    def api(self, method: str, path: str, payload: Any = None) -> Any:
        if (method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}
                or not isinstance(path, str) or not path.startswith("/")
                or path.startswith("//") or "\\" in path
                or any(ord(char) < 32 or ord(char) == 127 for char in path)):
            raise AuthError("INVALID_API_PATH")
        parsed = urllib.parse.urlsplit(path)
        decoded = urllib.parse.unquote(parsed.path)
        if (parsed.scheme or parsed.netloc or parsed.fragment
                or any(part in {".", ".."} for part in decoded.split("/"))
                or "\\" in decoded):
            raise AuthError("INVALID_API_PATH")
        return self._json(method, API_ROOT + path, payload, self._read_token())

    def _account(self, token: str, timeout: float = 30) -> dict[str, Any]:
        data = self._json("GET", API_ROOT + "/user", token=token, timeout=timeout)
        login = data.get("login") if isinstance(data, dict) else None
        if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", login):
            raise AuthError("INVALID_ACCOUNT")
        return {"login": login, "secure_storage": True}

    def inspect_account(self) -> dict[str, Any]:
        return self._account(self._read_token())

    def connect(self, cancel_event: threading.Event | None = None, timeout: float = 180,
                on_challenge: Callable[[dict[str, str]], None] | None = None) -> dict[str, Any]:
        if not self.client_id or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", self.client_id):
            raise AuthError("OAUTH_CLIENT_ID_REQUIRED")
        self._storage()  # Refuse insecure environments before requesting authorization.
        if (not isinstance(timeout, (int, float)) or not math.isfinite(timeout)
                or not 0 < timeout <= 1800):
            raise AuthError("INVALID_TIMEOUT")
        deadline = time.monotonic() + timeout
        cancel = cancel_event or threading.Event()

        def remaining() -> float:
            if cancel.is_set():
                raise AuthError("AUTH_CANCELLED")
            left = deadline - time.monotonic()
            if left <= 0:
                raise AuthError("AUTH_TIMEOUT")
            return left

        challenge = self._json("POST", "https://github.com/login/device/code",
                               {"client_id": self.client_id, "scope": "repo"},
                               timeout=remaining(), form=True)
        if not isinstance(challenge, dict):
            raise AuthError("INVALID_RESPONSE")
        device_code, user_code = challenge.get("device_code"), challenge.get("user_code")
        expires, interval = challenge.get("expires_in"), challenge.get("interval", 5)
        if (challenge.get("verification_uri") != DEVICE_URL
                or not isinstance(device_code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", device_code)
                or not isinstance(user_code, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,32}", user_code)
                or type(expires) is not int or not 0 < expires <= 3600
                or type(interval) is not int or not 1 <= interval <= 60):
            raise AuthError("INVALID_RESPONSE")
        deadline = min(deadline, time.monotonic() + expires)
        if on_challenge:
            try:
                on_challenge({"verification_uri": DEVICE_URL, "user_code": user_code})
            except Exception:
                raise AuthError("CHALLENGE_DISPLAY_FAILED") from None
        remaining()
        try:
            webbrowser.open(DEVICE_URL)
        except Exception:
            raise AuthError("BROWSER_OPEN_FAILED") from None
        while True:
            if cancel.wait(min(interval, remaining())):
                raise AuthError("AUTH_CANCELLED")
            result = self._json("POST", "https://github.com/login/oauth/access_token", {
                "client_id": self.client_id, "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }, timeout=remaining(), form=True)
            if not isinstance(result, dict):
                raise AuthError("INVALID_RESPONSE")
            error = result.get("error")
            if error is not None and not isinstance(error, str):
                raise AuthError("INVALID_RESPONSE")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            if error:
                mapping = {"access_denied": "AUTH_DENIED", "expired_token": "AUTH_EXPIRED"}
                raise AuthError(mapping.get(error, "AUTH_FAILED"))
            token = self._validate_token(result.get("access_token"))
            token_type = result.get("token_type", "bearer")
            if not isinstance(token_type, str) or token_type.lower() != "bearer":
                raise AuthError("INVALID_CREDENTIAL")
            account = self._account(token, timeout=remaining())
            remaining()
            try:
                self._storage().set_password(self.service, self._credential, token)
            except Exception:
                raise AuthError("SECURE_STORAGE_FAILED") from None
            return account

    def disconnect(self) -> None:
        try:
            store = self._storage()
            if store.get_password(self.service, self._credential) is not None:
                store.delete_password(self.service, self._credential)
        except AuthError:
            raise
        except Exception:
            raise AuthError("SECURE_STORAGE_FAILED") from None
