"""Windows Job Object regression with retained process handles (no Codex invocation)."""
import ctypes
import os
import unittest
if os.name != 'nt':
    raise unittest.SkipTest('Windows Job Object regression is Windows-only')
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
from ctypes import wintypes

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import aka_windows_job_runner
from aka_windows_job_runner import JobTimeout, run_in_job

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.WaitForSingleObject.restype = wintypes.DWORD
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL
kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel.TerminateProcess.restype = wintypes.BOOL

SYNCHRONIZE = 0x00100000
PROCESS_TERMINATE = 0x00000001
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102

CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def _wait_for_marker_text(path, deadline_s=4.0):
    """Poll *path* until it has text; return the text or None on timeout."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if path.is_file():
            try:
                return path.read_text(encoding="ascii")
            except (OSError, UnicodeError):
                pass
        time.sleep(.025)
    return None


def _open_process_handles(pids):
    """Open SYNCHRONIZE handles for *pids*; raises AssertionError if one cannot be opened."""
    handles = []
    for pid in pids:
        handle = kernel.OpenProcess(SYNCHRONIZE, False, int(pid))
        if not handle:
            for open_handle in handles:
                kernel.CloseHandle(open_handle)
            raise AssertionError("cannot open pid %s" % pid)
        handles.append(handle)
    return handles


def _close_handles(handles):
    for handle in handles:
        kernel.CloseHandle(handle)


def _terminate_pid(pid):
    """Best-effort TerminateProcess of *pid*; never raises (stray-process cleanup)."""
    try:
        handle = kernel.OpenProcess(PROCESS_TERMINATE, False, int(pid))
    except Exception:
        return
    if not handle:
        return
    try:
        kernel.TerminateProcess(handle, 1)
    finally:
        kernel.CloseHandle(handle)


class JobObjectTests(unittest.TestCase):
    def test_normal_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_in_job([sys.executable, "-c", "print('NORMAL')"], tmp, 10)
            self.assertEqual(result.returncode, 0)
            self.assertIn(b"NORMAL", result.stdout)

    def test_timeout_kills_parent_and_child_without_killing_unrelated_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            unrelated = subprocess.Popen(
                [sys.executable, "-c", "import time;time.sleep(45)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            handles = []
            try:
                marker = root / "pids.txt"
                code = (
                    'import os,sys,time,subprocess,pathlib;'
                    'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],'
                    'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);'
                    'pathlib.Path(sys.argv[1]).write_text(str(os.getpid())+"\\n"+str(p.pid),encoding="ascii");'
                    'time.sleep(60)'
                )
                state = {}
                def worker():
                    try:
                        run_in_job([sys.executable, "-c", code, str(marker)], root, 5)
                        state["returned"] = True
                    except JobTimeout:
                        state["timeout"] = True
                    except Exception as exc:
                        state["error"] = repr(exc)
                thread = threading.Thread(target=worker, daemon=True)
                thread.start()
                deadline = time.monotonic() + 4
                pids = []
                while thread.is_alive() and time.monotonic() < deadline:
                    if marker.is_file():
                        try:
                            pids = marker.read_text(encoding="ascii").splitlines()
                        except (OSError, UnicodeError):
                            pass
                        if len(pids) == 2:
                            break
                    time.sleep(.025)
                self.assertEqual(len(pids), 2, state)
                for pid in pids:
                    handle = kernel.OpenProcess(SYNCHRONIZE, False, int(pid))
                    self.assertTrue(handle)
                    handles.append(handle)
                for handle in handles:
                    self.assertEqual(kernel.WaitForSingleObject(handle, 0), WAIT_TIMEOUT)
                thread.join(timeout=12)
                self.assertFalse(thread.is_alive())
                self.assertTrue(state.get("timeout"), state)
                for handle in handles:
                    self.assertEqual(kernel.WaitForSingleObject(handle, 2000), WAIT_OBJECT_0)
                self.assertIsNone(unrelated.poll())
            finally:
                if "thread" in locals() and thread.is_alive():
                    thread.join(timeout=8)
                for handle in handles:
                    kernel.CloseHandle(handle)
                if unrelated.poll() is None:
                    unrelated.terminate()
                try:
                    unrelated.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    unrelated.kill()
                    unrelated.wait(timeout=5)


    def test_race_window_slow_assignment_still_contains_grandchild(self):
        """WP-B race regression. Designed to be RED on the old Popen-then-assign code.

        AssignProcessToJobObject is monkeypatched to sleep 1s, widening
        the old race window deterministically: with the old code the
        child starts at once and its grandchild is born before the
        delayed assignment, so the grandchild escapes the job and
        survives the timeout (the final death assertion fails). With
        suspended creation the child cannot run until after assignment,
        so the grandchild is born inside the job and dies on timeout.

        RED evidence has NOT been obtained: the test is Windows-only
        and can only run on windows-latest CI. The RED claim above is
        a design expectation from code walkthrough (2026-11-24 repair
        round 1), not an observed failure on old code.
        """
        original_assign = aka_windows_job_runner._kernel.AssignProcessToJobObject

        def slow_assign(job, handle):
            time.sleep(1.0)
            return original_assign(job, handle)

        aka_windows_job_runner._kernel.AssignProcessToJobObject = slow_assign
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                unrelated = subprocess.Popen(
                    [sys.executable, "-c", "import time;time.sleep(45)"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                handles = []
                try:
                    marker = root / "pids.txt"
                    code = (
                        'import os,sys,time,subprocess,pathlib;'
                        'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],'
                        'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);'
                        'pathlib.Path(sys.argv[1]).write_text(str(os.getpid())+"\\n"+str(p.pid),encoding="ascii");'
                        'time.sleep(60)'
                    )
                    state = {}
                    def worker():
                        try:
                            run_in_job([sys.executable, "-c", code, str(marker)], root, 5)
                            state["returned"] = True
                        except JobTimeout:
                            state["timeout"] = True
                        except Exception as exc:
                            state["error"] = repr(exc)
                    thread = threading.Thread(target=worker, daemon=True)
                    thread.start()
                    text = _wait_for_marker_text(marker)
                    self.assertIsNotNone(text, state)
                    pids = text.splitlines()
                    self.assertEqual(len(pids), 2, state)
                    handles = _open_process_handles(pids)
                    for handle in handles:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 0), WAIT_TIMEOUT)
                    thread.join(timeout=12)
                    self.assertFalse(thread.is_alive())
                    self.assertTrue(state.get("timeout"), state)
                    self.assertNotIn("error", state)
                    for handle in handles:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 2000), WAIT_OBJECT_0)
                    self.assertIsNone(unrelated.poll())
                finally:
                    if "thread" in locals() and thread.is_alive():
                        thread.join(timeout=8)
                    _close_handles(handles)
                    if unrelated.poll() is None:
                        unrelated.terminate()
                    try:
                        unrelated.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        unrelated.kill()
                        unrelated.wait(timeout=5)
        finally:
            aka_windows_job_runner._kernel.AssignProcessToJobObject = original_assign

    def test_breakaway_attempt_is_denied(self):
        """A child in the job cannot break away: the job does not set
        BREAKAWAY_OK, so spawning with CREATE_BREAKAWAY_FROM_JOB must
        fail inside the child. If it somehow succeeded, the escapee
        must still be dead after the timeout (fail-closed)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            marker = root / "breakaway.txt"
            code = "\n".join([
                "import subprocess,sys,time,pathlib",
                "try:",
                "    g=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
                "creationflags=0x01000000)",
                "    pathlib.Path(sys.argv[1]).write_text('spawned:'+str(g.pid),encoding='ascii')",
                "except Exception as e:",
                "    pathlib.Path(sys.argv[1]).write_text('denied:'+type(e).__name__,encoding='ascii')",
                "time.sleep(60)",
            ])
            state = {}
            def worker():
                try:
                    run_in_job([sys.executable, "-c", code, str(marker)], root, 5)
                    state["returned"] = True
                except JobTimeout:
                    state["timeout"] = True
                except Exception as exc:
                    state["error"] = repr(exc)
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            text = _wait_for_marker_text(marker)
            self.assertIsNotNone(text, state)
            thread.join(timeout=12)
            self.assertFalse(thread.is_alive())
            self.assertTrue(state.get("timeout"), state)
            self.assertNotIn("error", state)
            if text.startswith("spawned:"):
                pid = int(text.split(":", 1)[1])
                handles = _open_process_handles([pid])
                try:
                    self.assertEqual(kernel.WaitForSingleObject(handles[0], 2000), WAIT_OBJECT_0)
                finally:
                    _close_handles(handles)
                    _terminate_pid(pid)
            else:
                self.assertTrue(text.startswith("denied:"), text)

    def test_timeout_reports_descendants_verified_and_pids_dead(self):
        """WP-B/WP-C contract: on timeout the raised JobTimeout reports
        descendants_verified_terminated=True with no live PIDs, and an
        independent OpenProcess/WaitForSingleObject poll of the recorded
        parent+grandchild PIDs confirms both are dead."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            marker = root / "pids.txt"
            code = (
                'import os,sys,time,subprocess,pathlib;'
                'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],'
                'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);'
                'pathlib.Path(sys.argv[1]).write_text(str(os.getpid())+"\\n"+str(p.pid),encoding="ascii");'
                'time.sleep(60)'
            )
            state = {}
            def worker():
                try:
                    run_in_job([sys.executable, "-c", code, str(marker)], root, 5)
                    state["returned"] = True
                except JobTimeout as exc:
                    state["timeout_exc"] = exc
                except Exception as exc:
                    state["error"] = repr(exc)
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            text = _wait_for_marker_text(marker)
            self.assertIsNotNone(text, state)
            pids = text.splitlines()
            self.assertEqual(len(pids), 2, state)
            handles = _open_process_handles(pids)
            try:
                for handle in handles:
                    self.assertEqual(kernel.WaitForSingleObject(handle, 0), WAIT_TIMEOUT)
                thread.join(timeout=12)
                self.assertFalse(thread.is_alive())
                exc = state.get("timeout_exc")
                self.assertIsNotNone(exc, state)
                self.assertTrue(exc.descendants_verified_terminated, state)
                self.assertEqual(exc.alive_pids, [])
                for handle in handles:
                    self.assertEqual(kernel.WaitForSingleObject(handle, 2000), WAIT_OBJECT_0)
            finally:
                if thread.is_alive():
                    thread.join(timeout=8)
                _close_handles(handles)

    def test_reap_quietly_never_raises_on_repeated_timeout(self):
        """The finally-masking fix: even if communicate() keeps raising
        TimeoutExpired after kill(), _reap_quietly must return normally
        so cleanup can never replace the original exception."""
        class StubProc:
            def __init__(self):
                self.kill_calls = 0
            def communicate(self, timeout=None):
                raise subprocess.TimeoutExpired("stub", timeout)
            def poll(self):
                return None
            def kill(self):
                self.kill_calls += 1
            def wait(self, timeout=None):
                return 0
        stub = StubProc()
        aka_windows_job_runner._reap_quietly(stub, timeout=1)
        self.assertEqual(stub.kill_calls, 1)

    def test_active_process_limit_blocks_grandchild(self):
        """Opt-in ActiveProcessLimit: with max_processes=1 the child is
        the only process the job allows, so its grandchild spawn fails
        inside the child and the child exits normally."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            marker = root / "spawn.txt"
            code = "\n".join([
                "import subprocess,sys,pathlib",
                "try:",
                "    g=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)",
                "    pathlib.Path(sys.argv[1]).write_text('spawned:'+str(g.pid),encoding='ascii')",
                "    g.kill()",
                "except Exception as e:",
                "    pathlib.Path(sys.argv[1]).write_text('denied:'+type(e).__name__,encoding='ascii')",
            ])
            result = run_in_job([sys.executable, "-c", code, str(marker)], root, 10,
                                max_processes=1)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(marker.is_file())
            text = marker.read_text(encoding="ascii")
            self.assertTrue(text.startswith("denied:"), text)

    def test_job_memory_limit_blocks_huge_allocation(self):
        """Opt-in JobMemoryLimit: a 512 MiB allocation inside a 64 MiB
        job must fail with MemoryError (child exits 3), not succeed."""
        with tempfile.TemporaryDirectory() as tmp:
            code = "\n".join([
                "import sys",
                "try:",
                "    x=bytearray(512*1024*1024)",
                "    sys.exit(0)",
                "except MemoryError:",
                "    sys.exit(3)",
            ])
            result = run_in_job([sys.executable, "-c", code], tmp, 30,
                                job_memory_limit_bytes=64 * 1024 * 1024)
            self.assertEqual(result.returncode, 3)

    def test_invalid_limits_rejected_before_launch(self):
        """Limit validation happens before any process is spawned."""
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in ({"max_processes": 0}, {"max_processes": -1},
                           {"max_processes": True}, {"max_processes": "4"},
                           {"job_memory_limit_bytes": 0},
                           {"job_memory_limit_bytes": -1}):
                with self.assertRaises(ValueError, msg=kwargs):
                    run_in_job([sys.executable, "-c", "pass"], tmp, 5, **kwargs)


if __name__ == "__main__":
    unittest.main()
