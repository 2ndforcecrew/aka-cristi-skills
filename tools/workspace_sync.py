"""Consent-first, offline, manifest-verified personal workspace manual pull.

All source content is inert data. A preview is a capability local to one engine;
apply checks its exact plan and local preconditions under a process lock. Portable
filesystem checks cannot defend against a hostile process replacing parent
directories between syscalls; close other configuration editors during apply.
"""
import base64
import copy
import difflib
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import NoReturn

MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_FILES = 500
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_REVISION = re.compile(r"[a-f0-9]{40}\Z")
_ID = re.compile(r"[a-f0-9]{32}\Z")
_RESERVED = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)),
             *("lpt" + str(i) for i in range(1, 10))}
_FORBIDDEN = {"auth", "credentials", "credential", "secrets", "secret", "chats", "chat",
              "history", "sessions", "session", "tokens", "token", "env", "id_rsa", "id_ed25519"}
_SECRET = re.compile(
    rb"-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|"
    rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})|"
    rb"(?i:(?:oauth_token|access_token|refresh_token|api_key|api_secret|password|github_token)"
    rb"\s*[=:]\s*[\"']?[^\s\"'<>\{\}]{8,})")


class WorkspaceSyncError(ValueError):
    """Safe, fixed error identifiers; never include raw content or OS errors."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


SyncError = WorkspaceSyncError


def _fail(code) -> NoReturn:
    raise WorkspaceSyncError(code)


def _safe_errors(method):
    @wraps(method)
    def run(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except WorkspaceSyncError:
            raise
        except OSError:
            _fail("FILESYSTEM_ERROR")
        except (ValueError, TypeError, KeyError, UnicodeError):
            _fail("INVALID_DATA")
    return run


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _private_permissions(path, directory=False):
    """POSIX modes, or a protected current-user DACL on Windows (no fallback)."""
    os.chmod(path, 0o700 if directory else 0o600)
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
    security.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
                                                  ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
    security.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
                                             ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    security.SetNamedSecurityInfoW.restype = wintypes.DWORD
    token, descriptor = wintypes.HANDLE(), ctypes.c_void_p()
    sid_text = wintypes.LPWSTR()
    try:
        if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        size = wintypes.DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not size.value:
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        buffer = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not security.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        sid_value = sid_text.value
        if sid_value is None:
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        inheritance = "OICI" if directory else ""
        sddl = "D:P(A;" + inheritance + ";FA;;;" + sid_value + ")"
        if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), ctypes.c_void_p()
        if not security.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(dacl),
                                                  ctypes.byref(defaulted)) or not present.value or not dacl.value:
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
        if security.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None):
            _fail("PRIVATE_STORAGE_UNAVAILABLE")
    finally:
        if token:
            kernel.CloseHandle(token)
        if sid_text:
            kernel.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
        if descriptor:
            kernel.LocalFree(descriptor)


def _safe(path):
    path = Path(os.path.abspath(os.path.expanduser(str(path))))
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            _fail("UNSAFE_PATH")
        if part != path and not stat.S_ISDIR(info.st_mode):
            _fail("UNSAFE_PATH")
    return path


def _component(value, simple=False):
    if not isinstance(value, str) or not (_NAME if simple else _COMPONENT).fullmatch(value):
        _fail("INVALID_PATH")
    stem = value.split(".")[0].lower()
    if value.endswith(".") or stem in _RESERVED or stem in _FORBIDDEN:
        _fail("INVALID_PATH")


def _mapping(source):
    if not isinstance(source, str) or len(source) > 512:
        _fail("INVALID_PATH")
    parts = source.split("/")
    if source == "rules/AGENTS.md":
        return "codex/AGENTS.md"
    if len(parts) == 2 and parts[0] == "agents" and parts[1].endswith(".toml"):
        _component(parts[1][:-5], simple=True)
        return "codex/" + source
    if len(parts) >= 3 and parts[0] == "skills":
        _component(parts[1], simple=True)
        for part in parts[2:]:
            _component(part)
        return source
    _fail("INVALID_PATH")


def _entry(data, mode=0o600):
    # Windows chmod exposes the read-only bit, not POSIX owner/group bits.
    # Derive its expected stat mode rather than accepting an observed snapshot.
    if os.name == "nt":
        mode = 0o666 if mode & 0o200 else 0o444
    return {"data": base64.b64encode(data).decode("ascii"), "sha256": _hash(data), "mode": mode}


def _decode(entry):
    if not isinstance(entry, dict) or set(entry) != {"data", "sha256", "mode"}:
        _fail("INVALID_BACKUP")
    if type(entry["mode"]) is not int or entry["mode"] < 0 or entry["mode"] > 0o777:
        _fail("INVALID_BACKUP")
    try:
        data = base64.b64decode(entry["data"], validate=True)
    except (ValueError, TypeError):
        _fail("INVALID_BACKUP")
    if len(data) > MAX_FILE_BYTES or _hash(data) != entry["sha256"]:
        _fail("INVALID_BACKUP")
    return data


def _read(path):
    path = _safe(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_FILE_BYTES:
        _fail("UNSAFE_LOCAL_FILE")
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        _fail("SIZE_LIMIT")
    return _entry(data, stat.S_IMODE(info.st_mode) & 0o777)


def _private_read(path):
    path = _safe(path)
    if not path.exists():
        return None
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 48 * 1024 * 1024:
        _fail("INVALID_STATE")
    if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o077:
        _fail("INSECURE_STATE")
    if os.name == "nt":
        _private_permissions(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        _fail("INVALID_STATE")


def _atomic(path, data, mode=0o600, private=False):
    path = _safe(path)
    temp = path.with_name(".workspace-" + uuid.uuid4().hex + ".tmp")
    try:
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "wb") as handle:
            if private:
                _private_permissions(temp)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        _safe(path)
        os.replace(temp, path)
        if os.name != "nt":
            parent_descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(parent_descriptor)
            finally:
                os.close(parent_descriptor)
    finally:
        if temp.exists():
            temp.unlink()


class SyncEngine:
    @_safe_errors
    def __init__(self, state_dir, codex_home, skills_root):
        self.state_dir = _safe(state_dir)
        self.codex_home = _safe(codex_home)
        self.skills_root = _safe(skills_root)
        roots = [self.state_dir, self.codex_home, self.skills_root]
        for i, left in enumerate(roots):
            if left.exists() and not left.is_dir():
                _fail("UNSAFE_ROOT")
            for right in roots[i + 1:]:
                if left == right or left in right.parents or right in left.parents:
                    _fail("OVERLAPPING_ROOTS")
        self._binding = _hash(_json([str(self.codex_home), str(self.skills_root)]))
        self._plans = {}

    def _target(self, source):
        target = _mapping(source)
        label, relative = target.split("/", 1)
        root = self.codex_home if label == "codex" else self.skills_root
        return _safe(root / relative)

    def _prepare_state(self):
        _safe(self.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        _private_permissions(self.state_dir, directory=True)
        backups = _safe(self.state_dir / "backups")
        backups.mkdir(exist_ok=True, mode=0o700)
        _private_permissions(backups, directory=True)

    @contextmanager
    def _lock(self):
        self._prepare_state()
        with self._file_lock(self.state_dir / "sync.lock"):
            yield

    @contextmanager
    def _target_lock(self):
        # Locks follow destination roots, not account/repository state profiles.
        # A separate lock per root also coordinates engines sharing only one root.
        # Preview/status never create these files or configuration destinations.
        with ExitStack() as stack:
            for root in sorted((self.codex_home, self.skills_root), key=str):
                _safe(root)
                parent = _safe(root.parent)
                parent.mkdir(parents=True, exist_ok=True)
                _safe(parent)
                key = _hash(os.path.normcase(str(root)).encode("utf-8"))
                path = parent / (".aka-workspace-lock-" + key)
                stack.enter_context(self._file_lock(path))
            yield

    @contextmanager
    def _file_lock(self, path):
        lock_path = _safe(path)
        if lock_path.exists() and (not lock_path.is_file() or lock_path.stat().st_nlink != 1):
            _fail("UNSAFE_PATH")
        handle = open(lock_path, "a+b")
        locked = False
        try:
            _private_permissions(lock_path)
            if sys.platform == "win32":
                import msvcrt
                # Do not read another process's locked byte: Windows byte-range
                # locks can reject the read before LK_NBLCK reports SYNC_BUSY.
                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    _fail("SYNC_BUSY")
            else:
                import fcntl
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    _fail("SYNC_BUSY")
            locked = True
            yield
        finally:
            if locked:
                if sys.platform == "win32":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def _state(self):
        state = _private_read(self.state_dir / "state.json")
        if state is None:
            return {"version": 1, "binding": self._binding, "owner": None, "repository": None,
                    "owned": {}, "backups": {}, "generation": 0}
        if not isinstance(state, dict) or set(state) != {
                "version", "binding", "owner", "repository", "owned", "backups", "generation"}:
            _fail("INVALID_STATE")
        if state["version"] != 1 or state["binding"] != self._binding:
            _fail("STATE_ROOT_MISMATCH")
        if not isinstance(state["owned"], dict) or not isinstance(state["backups"], dict):
            _fail("INVALID_STATE")
        if type(state["generation"]) is not int or state["generation"] < 0:
            _fail("INVALID_STATE")
        if (state["owner"] is None) != (state["repository"] is None):
            _fail("INVALID_STATE")
        if state["owner"] is not None and (not isinstance(state["owner"], str) or
                not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", state["owner"]) or
                not isinstance(state["repository"], str) or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", state["repository"])):
            _fail("INVALID_STATE")
        for source, digest in state["owned"].items():
            _mapping(source)
            if not isinstance(digest, str) or not _HEX.fullmatch(digest):
                _fail("INVALID_STATE")
        for backup_id, metadata in state["backups"].items():
            if not isinstance(backup_id, str) or not _ID.fullmatch(backup_id) or not isinstance(metadata, dict) or set(metadata) != {
                    "sha256", "created_at", "status", "receipt"}:
                _fail("INVALID_STATE")
            if not isinstance(metadata["receipt"], str) or not re.fullmatch(
                    re.escape(backup_id) + r"-[a-f0-9]{32}\.json", metadata["receipt"]):
                _fail("INVALID_STATE")
            if not isinstance(metadata["sha256"], str) or not _HEX.fullmatch(metadata["sha256"]) or metadata["status"] not in {
                    "APPLYING", "SYNCED", "RESTORING", "RESTORED", "FAILED_ROLLED_BACK", "BLOCKED_ROLLBACK_REQUIRED"}:
                _fail("INVALID_STATE")
            timestamp = metadata["created_at"]
            if not isinstance(timestamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00", timestamp):
                _fail("INVALID_STATE")
            datetime.fromisoformat(timestamp)
        return state

    def _save_state(self, state):
        _atomic(self.state_dir / "state.json", _json(state), private=True)

    def _audit(self, event, status):
        # These are closed enums; no source identifier, path, exception or data.
        if event not in {"APPLY", "RESTORE"} or status not in {
                "SYNCED", "RESTORED", "FAILED_ROLLED_BACK", "BLOCKED_ROLLBACK_REQUIRED"}:
            _fail("INVALID_AUDIT")
        path = self.state_dir / "audit.json"
        existing = self.audit_log()
        existing.append({"event": event, "status": status})
        _atomic(path, _json(existing[-1000:]), private=True)

    def _validate(self, manifest, files, revision):
        if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
            _fail("INVALID_SOURCE_REVISION")
        if not isinstance(manifest, dict) or set(manifest) != {
                "schema_version", "owner", "repository", "sync_mode", "files"}:
            _fail("INVALID_MANIFEST")
        if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or manifest["sync_mode"] != "manual":
            _fail("INVALID_MANIFEST")
        owner, repository = manifest["owner"], manifest["repository"]
        if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner):
            _fail("INVALID_OWNER")
        if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", repository):
            _fail("INVALID_REPOSITORY")
        if repository.endswith(".") or repository.lower().endswith(".git"):
            _fail("INVALID_REPOSITORY")
        entries = manifest["files"]
        if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES or not isinstance(files, dict):
            _fail("INVALID_MANIFEST")
        payload = {}
        total = 0
        targets: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"path", "target", "sha256"}:
                _fail("INVALID_MANIFEST")
            source = entry["path"]
            target = _mapping(source)
            if target != entry["target"] or target.casefold() in targets:
                _fail("INVALID_MANIFEST")
            for existing in targets:
                if existing.startswith(target.casefold() + "/") or target.casefold().startswith(existing + "/"):
                    _fail("INVALID_MANIFEST")
            targets.add(target.casefold())
            digest, data = entry["sha256"], files.get(source)
            if not isinstance(digest, str) or not _HEX.fullmatch(digest) or not isinstance(data, bytes):
                _fail("INVALID_PAYLOAD")
            total += len(data)
            if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                _fail("SIZE_LIMIT")
            if _hash(data) != digest:
                _fail("HASH_MISMATCH")
            if _SECRET.search(data):
                _fail("SECRET_CONTENT")
            payload[source] = data
        if set(payload) != set(files):
            _fail("UNEXPECTED_PAYLOAD")
        return payload

    def _snapshot(self, sources):
        snapshot = {source: _read(self._target(source)) for source in sources}
        if sum(len(_decode(entry)) for entry in snapshot.values() if entry is not None) > MAX_TOTAL_BYTES:
            _fail("SIZE_LIMIT")
        return snapshot

    @_safe_errors
    def preview(self, manifest, files, source_revision):
        payload = self._validate(manifest, files, source_revision)
        with self._lock():
            state = self._state()
            if state["owner"] is not None and (state["owner"].lower(), state["repository"].lower()) != (
                    manifest["owner"].lower(), manifest["repository"].lower()):
                _fail("WORKSPACE_IDENTITY_MISMATCH")
            old_paths = {_mapping(source).casefold(): source for source in state["owned"]}
            if any(_mapping(source).casefold() in old_paths and
                   old_paths[_mapping(source).casefold()] != source for source in payload):
                _fail("PATH_CASE_CONFLICT")
            before = self._snapshot(payload)
            changes, conflicts = [], []
            for source, data in payload.items():
                entry = before[source]
                old = _decode(entry) if entry else b""
                owned = state["owned"].get(source)
                conflict = (entry is not None and owned is None and old != data) or (
                    owned is not None and (entry is None or entry["sha256"] != owned))
                action = "CONFLICT" if conflict else (
                    "CREATE" if entry is None else "ADOPT" if owned is None else "UNCHANGED" if old == data else "UPDATE")
                try:
                    old_lines, new_lines = old.decode("utf-8").splitlines(True), data.decode("utf-8").splitlines(True)
                except UnicodeError:
                    old_lines = [base64.b64encode(old).decode("ascii") + "\n"] if old else []
                    new_lines = [base64.b64encode(data).decode("ascii") + "\n"]
                diff = "".join(difflib.unified_diff(old_lines, new_lines, fromfile=source + " before",
                                                    tofile=source + " after", n=max(len(old_lines), len(new_lines))))
                change = {"path": source, "action": action, "diff": diff}
                changes.append(change)
                if conflict:
                    conflicts.append({"path": source, "action": "CONFLICT"})
            plan_id = uuid.uuid4().hex
            public = {"changes": changes, "conflicts": conflicts,
                      "source_revision": source_revision, "_plan_id": plan_id}
            self._plans[plan_id] = {"public": copy.deepcopy(public), "before": before, "state": state,
                                    "payload": payload, "manifest": copy.deepcopy(manifest)}
            return public

    def _write_target(self, path, data, mode):
        _safe(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _safe(path)
        _atomic(path, data, mode)

    def _restore_files(self, before, after):
        # Check the entire known footprint before any change; never bless a
        # fresh post-failure snapshot as our own write set.
        if self._snapshot(after) != after:
            _fail("ROLLBACK_CONFLICT")
        for source, desired in before.items():
            current = _read(self._target(source))
            if current != after[source]:
                _fail("ROLLBACK_CONFLICT")
            if current == desired:
                continue
            path = self._target(source)
            if desired is None:
                path.unlink()
            else:
                self._write_target(path, _decode(desired), desired["mode"])
        if self._snapshot(before) != before:
            _fail("ROLLBACK_CONFLICT")

    def _record(self, record, state):
        data = _json(record)
        backup_id = record["id"]
        previous = state["backups"].get(backup_id, {}).get("receipt")
        receipt = backup_id + "-" + uuid.uuid4().hex + ".json"
        # Never overwrite the journal referenced by a committed ledger. If the
        # atomic pointer update fails, that old receipt remains readable/retryable.
        _atomic(self.state_dir / "backups" / receipt, data, private=True)
        updated = copy.deepcopy(state)
        updated["backups"][backup_id] = {"sha256": _hash(data), "created_at": record["created_at"],
                                        "status": record["status"], "receipt": receipt}
        self._save_state(updated)
        state.clear()
        state.update(updated)
        # The atomic pointer now names the new complete revision. Reclaim only
        # this same backup's previously committed revision, never crash orphans
        # or the receipt of any other backup transaction.
        if isinstance(previous, str) and re.fullmatch(re.escape(backup_id) + r"-[a-f0-9]{32}\.json", previous):
            try:
                _safe(self.state_dir / "backups" / previous).unlink()
            except (OSError, ValueError):
                pass  # Cleanup failure retains a private diagnostic revision.

    @_safe_errors
    def apply(self, plan, confirmed=False):
        if confirmed is not True:
            _fail("CONFIRMATION_REQUIRED")
        if not isinstance(plan, dict) or not isinstance(plan.get("_plan_id"), str):
            _fail("INVALID_PREVIEW")
        saved = self._plans.get(plan["_plan_id"])
        if saved is None or plan != saved["public"]:
            _fail("INVALID_PREVIEW")
        if plan["conflicts"]:
            _fail("LOCAL_CONFLICT")
        with self._target_lock(), self._lock():
            state = self._state()
            if state != saved["state"] or self._snapshot(saved["before"]) != saved["before"]:
                _fail("STALE_PREVIEW")
            before = saved["before"]
            after = copy.deepcopy(before)
            backup_id = uuid.uuid4().hex
            next_owned = dict(state["owned"])
            for source, data in saved["payload"].items():
                next_owned[source] = _hash(data)
            record = {"version": 1, "id": backup_id, "binding": self._binding,
                      "created_at": datetime.now(timezone.utc).isoformat(), "status": "APPLYING",
                      "source_revision": plan["source_revision"], "before": before, "after": after,
                      "owned_before": dict(state["owned"]), "owned_after": next_owned,
                      "owner_before": state["owner"], "repository_before": state["repository"],
                      "owner": saved["manifest"]["owner"], "repository": saved["manifest"]["repository"]}
            self._record(record, state)  # Durable full backup before first target write.
            try:
                for source, data in saved["payload"].items():
                    if self._snapshot(after) != after:
                        _fail("CONCURRENT_CHANGE")
                    old = before[source]
                    if old is not None and _decode(old) == data:
                        continue
                    mode = old["mode"] if old is not None else 0o600
                    self._write_target(self._target(source), data, mode)
                    after[source] = _entry(data, mode)
                    if self._snapshot(after) != after:
                        _fail("CONCURRENT_CHANGE")
                    record["after"] = copy.deepcopy(after)
                    self._record(record, state)
                if self._snapshot(after) != after:
                    _fail("CONCURRENT_CHANGE")
                state["owned"] = next_owned
                state["owner"], state["repository"] = record["owner"], record["repository"]
                state["generation"] += 1
                record["status"] = "SYNCED"
                record["after"] = copy.deepcopy(after)
                self._record(record, state)
                self._audit("APPLY", "SYNCED")
                return {"status": "SYNCED", "backup_id": backup_id, "source_revision": plan["source_revision"]}
            except (OSError, ValueError):
                # Only the deterministic expected successful writes are eligible
                # for undo. Unrecognized bytes block all automatic rollback.
                try:
                    self._restore_files(before, after)
                    state["owned"] = record["owned_before"]
                    state["owner"], state["repository"] = record["owner_before"], record["repository_before"]
                    record["status"] = "FAILED_ROLLED_BACK"
                except (OSError, ValueError):
                    record["status"] = "BLOCKED_ROLLBACK_REQUIRED"
                record["after"] = copy.deepcopy(after)
                self._record(record, state)
                self._audit("APPLY", record["status"])
                return {"status": record["status"], "backup_id": backup_id, "source_revision": plan["source_revision"]}

    @_safe_errors
    def backups(self):
        if not _safe(self.state_dir).exists():
            return []
        with self._lock():
            state = self._state()
            return [{"id": backup_id, "created_at": item["created_at"], "status": item["status"]}
                    for backup_id, item in sorted(state["backups"].items(),
                                                  key=lambda pair: pair[1]["created_at"], reverse=True)]

    def _load_backup(self, backup_id, state):
        if not isinstance(backup_id, str) or not _ID.fullmatch(backup_id):
            _fail("INVALID_BACKUP")
        item = state["backups"].get(backup_id)
        if not isinstance(item, dict):
            _fail("BACKUP_NOT_FOUND")
        path = _safe(self.state_dir / "backups" / item["receipt"])
        record = _private_read(path)
        if record is None or _hash(_json(record)) != item["sha256"]:
            _fail("BACKUP_INTEGRITY")
        if record.get("id") != backup_id or record.get("binding") != self._binding or record.get("version") != 1:
            _fail("INVALID_BACKUP")
        before, after = record.get("before"), record.get("after")
        if not isinstance(before, dict) or not isinstance(after, dict) or set(before) != set(after) or len(before) > MAX_FILES:
            _fail("INVALID_BACKUP")
        total = 0
        for entries in (before, after):
            for source, entry in entries.items():
                self._target(source)
                if entry is not None:
                    total += len(_decode(entry))
        if total > MAX_TOTAL_BYTES * 2:
            _fail("INVALID_BACKUP")
        return record

    @_safe_errors
    def restore(self, backup_id, confirmed=False):
        if confirmed is not True:
            _fail("CONFIRMATION_REQUIRED")
        with self._target_lock(), self._lock():
            state = self._state()
            record = self._load_backup(backup_id, state)
            original_record = copy.deepcopy(record)
            current_status = record["status"]
            if current_status not in {"SYNCED", "APPLYING", "RESTORING"}:
                _fail("RESTORE_NOT_CURRENT")
            origin = record.get("restore_origin") if current_status == "RESTORING" else current_status
            if origin not in {"SYNCED", "APPLYING"}:
                _fail("INVALID_BACKUP")
            owned = record["owned_before"] if origin == "APPLYING" else record["owned_after"]
            identity = (record["owner_before"], record["repository_before"]) if origin == "APPLYING" else (
                record["owner"], record["repository"])
            if state["owned"] != owned or (state["owner"], state["repository"]) != identity:
                _fail("RESTORE_NOT_CURRENT")
            expected = copy.deepcopy(record["after"])
            progress = record.get("restore_progress", []) if current_status == "RESTORING" else []
            if not isinstance(progress, list) or any(not isinstance(source, str) for source in progress) or (
                    len(set(progress)) != len(progress)) or any(source not in record["before"] for source in progress):
                _fail("INVALID_BACKUP")
            for source in progress:
                expected[source] = record["before"][source]
            # Recovery authority comes solely from the persisted footprint and
            # progress, never from taking a fresh snapshot of arbitrary edits.
            if self._snapshot(expected) != expected:
                _fail("ROLLBACK_CONFLICT")
            original_state = copy.deepcopy(state)
            start_expected = copy.deepcopy(expected)
            record["status"] = "RESTORING"
            record["restore_origin"] = origin
            record["restore_progress"] = list(progress)
            self._record(record, state)
            try:
                for source, desired in record["before"].items():
                    if self._snapshot(expected) != expected:
                        _fail("ROLLBACK_CONFLICT")
                    if desired != expected[source]:
                        path = self._target(source)
                        if desired is None:
                            path.unlink()
                        else:
                            self._write_target(path, _decode(desired), desired["mode"])
                        expected[source] = desired
                        if self._snapshot(expected) != expected:
                            _fail("ROLLBACK_CONFLICT")
                        record["restore_progress"].append(source)
                        self._record(record, state)
                if self._snapshot(expected) != expected:
                    _fail("ROLLBACK_CONFLICT")
                state["owned"] = record["owned_before"]
                state["owner"], state["repository"] = record["owner_before"], record["repository_before"]
                state["generation"] += 1
                record["status"] = "RESTORED"
                self._record(record, state)
                self._audit("RESTORE", "RESTORED")
            except (OSError, ValueError):
                try:
                    self._restore_files(start_expected, expected)
                    state["owned"] = original_state["owned"]
                    state["owner"], state["repository"] = original_state["owner"], original_state["repository"]
                    state["generation"] = original_state["generation"]
                    record = copy.deepcopy(original_record)
                    status = "FAILED_ROLLED_BACK"
                except (OSError, ValueError):
                    record["status"] = "BLOCKED_ROLLBACK_REQUIRED"
                    status = "BLOCKED_ROLLBACK_REQUIRED"
                self._record(record, state)
                self._audit("RESTORE", status)
                return {"status": status, "backup_id": backup_id, "source_revision": record["source_revision"]}
            return {"status": "RESTORED", "backup_id": backup_id, "source_revision": record["source_revision"]}

    @_safe_errors
    def installed_skills(self):
        if not _safe(self.state_dir).exists():
            return []
        with self._lock():
            owned = self._state()["owned"]
            names = sorted({source.split("/")[1] for source in owned if source.startswith("skills/")})
            return [{"name": name, "status": "INSTALLED" if all(
                (entry := _read(self._target(source))) is not None and entry["sha256"] == digest
                for source, digest in owned.items() if source.startswith("skills/" + name + "/")) else "MODIFIED"}
                for name in names]

    @_safe_errors
    def audit_log(self):
        data = _private_read(self.state_dir / "audit.json")
        if data is None:
            return []
        if not isinstance(data, list) or len(data) > 1000:
            _fail("INVALID_AUDIT")
        for item in data:
            if not isinstance(item, dict) or set(item) != {"event", "status"} or item["event"] not in {
                    "APPLY", "RESTORE"} or item["status"] not in {
                    "SYNCED", "RESTORED", "FAILED_ROLLED_BACK", "BLOCKED_ROLLBACK_REQUIRED"}:
                _fail("INVALID_AUDIT")
        return copy.deepcopy(data)
