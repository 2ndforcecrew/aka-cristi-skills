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
import unittest
from ctypes import wintypes

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from aka_windows_job_runner import JobTimeout, run_in_job

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.WaitForSingleObject.restype = wintypes.DWORD
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL

SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102


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
                while not marker.is_file() and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(.025)
                self.assertTrue(marker.is_file(), state)
                pids = marker.read_text(encoding="ascii").splitlines()
                self.assertEqual(len(pids), 2)
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
                for handle in handles:
                    kernel.CloseHandle(handle)
                if unrelated.poll() is None:
                    unrelated.terminate()
                try:
                    unrelated.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    unrelated.kill()
                    unrelated.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
