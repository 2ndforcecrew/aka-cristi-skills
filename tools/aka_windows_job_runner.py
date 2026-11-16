"""Windows-only process-tree lifecycle for Codex acceptance probes.

Job Object kill-on-close is a *lifecycle* control, not a sandbox.
A short process-start-to-job-assignment race still exists; the real
agent security gate remains BLOCKED until isolation is proved.
"""
import ctypes
import os
import subprocess
from ctypes import wintypes

if os.name != "nt":
    raise RuntimeError("Windows only")

_kernel = ctypes.WinDLL("kernel32", use_last_error=True)

class _BasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]

class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]

class _ExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimit),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

_kernel.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
_kernel.CreateJobObjectW.restype = wintypes.HANDLE
_kernel.SetInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD
]
_kernel.SetInformationJobObject.restype = wintypes.BOOL
_kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
_kernel.AssignProcessToJobObject.restype = wintypes.BOOL
_kernel.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel.CloseHandle.restype = wintypes.BOOL

class JobError(RuntimeError):
    """Job setup/assignment failed; never infer containment."""

class JobTimeout(TimeoutError):
    """The probe exceeded its allotted time."""


def run_in_job(command, cwd, timeout, env=None):
    """Run the child under kill-on-close, rejecting assignment failures.

    Does not guarantee race-free containment or MCP/network/credential isolation.
    """
    job = _kernel.CreateJobObjectW(None, None)
    if not job:
        raise JobError("CreateJobObjectW failed")
    proc = None
    assigned = False
    try:
        limits = _ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = 0x2000
        if not _kernel.SetInformationJobObject(
            job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise JobError("SetInformationJobObject failed")
        proc = subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if not _kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(proc._handle))):
            raise JobError("AssignProcessToJobObject failed")
        assigned = True
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise JobTimeout("Job-controlled process timed out") from exc
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    finally:
        _kernel.CloseHandle(job)
        if proc is not None:
            if not assigned and proc.poll() is None:
                proc.kill()
            try:
                proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate(timeout=10)
