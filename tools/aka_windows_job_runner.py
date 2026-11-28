"""Windows-only process-tree lifecycle for Codex acceptance probes.

Job Object kill-on-close is a *lifecycle* control, not a sandbox.

The child is created suspended (``CREATE_SUSPENDED``) and assigned to
the Job Object before its primary thread is resumed, so no child code
runs -- and no grandchild is born -- outside the job. Assignment
failures (including nested-job / breakaway conflicts) fail closed with
``JobError``: the still-suspended child is terminated and the run is
refused rather than executed unconstrained. On timeout the job is
terminated and ``QueryInformationJobObject`` verifies the job emptied;
the result is reported on ``JobTimeout`` (see ``run_in_job``).

The real agent security gate remains BLOCKED until isolation is proved.
"""
import ctypes
import os
import struct
import subprocess
import time
from ctypes import wintypes

if os.name != "nt":
    raise RuntimeError("Windows only")

_kernel = ctypes.WinDLL("kernel32", use_last_error=True)

# Creation flags (winbase.h).
CREATE_SUSPENDED = 0x00000004
# NOTE: CREATE_BREAKAWAY_FROM_JOB (0x01000000) is deliberately NOT passed.
# It only helps when the ambient job (if any) allows breakaway; when it
# does not, CreateProcess fails outright. A runner that itself runs
# inside a job therefore still fails closed at assignment time (see
# run_in_job). Auto-escape needs a real-host decision, not a guess here.

# Job Object limit flags (winnt.h).
JOB_OBJECT_LIMIT_KILL_ON_CLOSE = 0x2000
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200

# JobObjectInformationClass values (winnt.h).
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3

# Thread/toolhelp constants (winnt.h / tlhelp32.h).
THREAD_SUSPEND_RESUME = 0x0002
TH32CS_SNAPTHREAD = 0x00000004
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

ERROR_MORE_DATA = 234

__all__ = [
    "JobError",
    "JobTimeout",
    "query_job_process_ids",
    "wait_for_job_empty",
    "run_in_job",
]


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

class _ThreadEntry32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
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
_kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
_kernel.TerminateJobObject.restype = wintypes.BOOL
_kernel.QueryInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel.QueryInformationJobObject.restype = wintypes.BOOL
_kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry32)]
_kernel.Thread32First.restype = wintypes.BOOL
_kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry32)]
_kernel.Thread32Next.restype = wintypes.BOOL
_kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel.OpenThread.restype = wintypes.HANDLE
_kernel.ResumeThread.argtypes = [wintypes.HANDLE]
_kernel.ResumeThread.restype = wintypes.DWORD

class JobError(RuntimeError):
    """Job setup/assignment failed; never infer containment."""

class JobTimeout(TimeoutError):
    """The probe exceeded its allotted time.

    Attributes set by run_in_job on the timeout path:

    - ``descendants_verified_terminated`` (bool): True only when
      QueryInformationJobObject confirmed the job empty after
      TerminateJobObject. False means "not verified", never "alive".
    - ``alive_pids`` (list[int]): PIDs still reported in the job at the
      end of the verification window (empty when verified).
    """

    def __init__(self, message):
        super().__init__(message)
        self.descendants_verified_terminated = False
        self.alive_pids = []


def query_job_process_ids(job_handle):
    """Return the PIDs currently assigned to *job_handle*.

    Uses QueryInformationJobObject(JobObjectBasicProcessIdList).
    Raises JobError if the query fails.
    """
    capacity = 1024
    while True:
        buf = ctypes.create_string_buffer(
            8 + capacity * ctypes.sizeof(ctypes.c_void_p)
        )
        returned = wintypes.DWORD(0)
        ok = _kernel.QueryInformationJobObject(
            job_handle, JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            buf, len(buf), ctypes.byref(returned),
        )
        if ok:
            _assigned, count = struct.unpack_from("<II", buf.raw, 0)
            count = min(count, capacity)
            if count == 0:
                return []
            # The PID list is an array of ULONG_PTR at offset 8; read it
            # via ctypes (struct 'P' is native-mode only, so it cannot be
            # combined with the '<' prefix used for the DWORD header).
            pid_array = (ctypes.c_void_p * count).from_address(
                ctypes.addressof(buf) + 8
            )
            return [pid_array[i] for i in range(count)]
        err = ctypes.get_last_error()
        if err == ERROR_MORE_DATA and capacity < 65536:
            capacity *= 4
            continue
        raise JobError("QueryInformationJobObject failed (last error %d)" % err)


def wait_for_job_empty(job_handle, timeout=5.0, poll_interval=0.05):
    """Poll QueryInformationJobObject until *job_handle* reports no processes.

    Returns ``(empty, last_seen_pids)``: ``(True, [])`` only after two
    consecutive empty polls (a single empty read could straddle a
    process mid-creation); otherwise ``(False, last_seen_pids)`` once
    *timeout* seconds elapse, or ``(False, last_seen_pids)`` if the
    query itself fails. Never raises for a timeout; a JobError from the
    query is reported as not-verified, never as empty.
    """
    deadline = time.monotonic() + timeout
    last_seen = []
    empty_streak = 0
    while True:
        try:
            pids = query_job_process_ids(job_handle)
        except JobError:
            return False, last_seen
        if not pids:
            empty_streak += 1
            if empty_streak >= 2:
                return True, []
        else:
            empty_streak = 0
            last_seen = pids
        if time.monotonic() >= deadline:
            return False, last_seen
        time.sleep(poll_interval)


def _apply_job_limits(job, max_processes, job_memory_limit_bytes):
    """Apply KILL_ON_CLOSE plus the optional caps. Raises JobError on failure."""
    limits = _ExtendedLimit()
    flags = JOB_OBJECT_LIMIT_KILL_ON_CLOSE
    if max_processes is not None:
        flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        limits.BasicLimitInformation.ActiveProcessLimit = max_processes
    if job_memory_limit_bytes is not None:
        flags |= JOB_OBJECT_LIMIT_JOB_MEMORY
        limits.JobMemoryLimit = job_memory_limit_bytes
    limits.BasicLimitInformation.LimitFlags = flags
    if not _kernel.SetInformationJobObject(
        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits), ctypes.sizeof(limits),
    ):
        raise JobError(
            "SetInformationJobObject failed (last error %d)"
            % ctypes.get_last_error()
        )


def _resume_process_threads(pid):
    """Resume every thread of *pid* (created suspended). Raises JobError if none resumes.

    The child is suspended at creation, so only its primary thread can
    exist; enumerating the thread list via Toolhelp is race-free here
    because no child code can run (and therefore no new thread can be
    created) until a resume succeeds.
    """
    snapshot = _kernel.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snapshot in (None, INVALID_HANDLE_VALUE):
        raise JobError(
            "CreateToolhelp32Snapshot failed (last error %d)"
            % ctypes.get_last_error()
        )
    resumed = 0
    try:
        entry = _ThreadEntry32()
        entry.dwSize = ctypes.sizeof(entry)
        ok = _kernel.Thread32First(snapshot, ctypes.byref(entry))
        while ok:
            if entry.th32OwnerProcessID == pid:
                thread = _kernel.OpenThread(
                    THREAD_SUSPEND_RESUME, False, entry.th32ThreadID
                )
                if thread:
                    try:
                        if _kernel.ResumeThread(thread) != 0xFFFFFFFF:
                            resumed += 1
                    finally:
                        _kernel.CloseHandle(thread)
            ok = _kernel.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        _kernel.CloseHandle(snapshot)
    if resumed == 0:
        raise JobError(
            "ResumeThread failed: no thread of the suspended child could "
            "be resumed (last error %d)" % ctypes.get_last_error()
        )


def _terminate_job_and_verify(job, timeout=5.0):
    """Terminate every process in *job* and verify the job empties.

    Returns ``(verified, alive_pids)`` as defined by
    wait_for_job_empty. Never raises: any failure to terminate or query
    is reported as verified=False, so this helper cannot mask the
    JobTimeout it is called to annotate.
    """
    try:
        _kernel.TerminateJobObject(job, 1)
    except Exception:
        pass
    try:
        return wait_for_job_empty(job, timeout=timeout)
    except Exception:
        return False, []


def _terminate_quietly(proc):
    """Best-effort terminate + reap of a never-resumed child. Never raises."""
    try:
        if proc.poll() is None:
            proc.kill()
    except Exception:
        pass
    _reap_quietly(proc)


def _reap_quietly(proc, timeout=10):
    """Reap *proc* without ever raising, so cleanup cannot mask the original error.

    A second communicate() timeout after kill() is swallowed here instead
    of escaping from a finally block and replacing the original
    exception (previously: a TimeoutExpired from the reaping
    communicate() could hide the JobTimeout / JobError that caused
    cleanup in the first place).
    """
    try:
        proc.communicate(timeout=timeout)
    except Exception:
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass
        try:
            proc.communicate(timeout=timeout)
        except Exception:
            pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def _close_job_quietly(job):
    """Close the job handle (kill-on-close backstop). Never raises."""
    try:
        _kernel.CloseHandle(job)
    except Exception:
        pass


def run_in_job(command, cwd, timeout, env=None, max_processes=None,
               job_memory_limit_bytes=None):
    """Run *command* in a Job Object and return its CompletedProcess.

    Race fix (WP-B): the child is created suspended
    (``CREATE_SUSPENDED``), assigned to the job, and only then resumed,
    so no child code can run -- and no grandchild can be born -- outside
    the job. The ``PROC_THREAD_ATTRIBUTE_JOB_LIST`` alternative was
    considered and rejected: it requires bypassing ``subprocess.Popen``
    and reimplementing CreateProcessW with STARTUPINFOEX (pipes, env
    block, handle inheritance), a much larger blast radius for the same
    guarantee. Assignment failure -- including nested-job / breakaway
    conflicts, e.g. when the runner itself runs inside a job -- kills
    the still-suspended child and raises JobError (fail-closed); nested
    jobs are not silently supported.

    On timeout a JobTimeout is raised; its
    ``descendants_verified_terminated`` attribute is True only when
    QueryInformationJobObject confirmed the job empty after
    TerminateJobObject, and ``alive_pids`` lists any PIDs still
    reported at the end of the verification window. Cleanup never
    raises, so a failure while reaping the child cannot replace the
    original error.

    Optional caps, off by default: ``max_processes`` caps
    ActiveProcessLimit, ``job_memory_limit_bytes`` caps JobMemoryLimit.
    No default cap is imposed because no safe values have been measured
    against a real Codex run; callers must opt in once measured.

    Does not guarantee MCP/network/credential isolation.
    """
    if max_processes is not None and (
        not isinstance(max_processes, int)
        or isinstance(max_processes, bool)
        or max_processes < 1
    ):
        raise ValueError("max_processes must be a positive int")
    if job_memory_limit_bytes is not None and (
        not isinstance(job_memory_limit_bytes, int)
        or isinstance(job_memory_limit_bytes, bool)
        or job_memory_limit_bytes < 1
    ):
        raise ValueError("job_memory_limit_bytes must be a positive int")
    job = _kernel.CreateJobObjectW(None, None)
    if not job:
        raise JobError("CreateJobObjectW failed")
    proc = None
    try:
        _apply_job_limits(job, max_processes, job_memory_limit_bytes)
        proc = subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=CREATE_SUSPENDED,
        )
        try:
            if not _kernel.AssignProcessToJobObject(
                job, wintypes.HANDLE(int(proc._handle))
            ):
                raise JobError(
                    "AssignProcessToJobObject failed (last error %d). "
                    "The child may already be in a job (nested job) or "
                    "the ambient job forbids breakaway; containment is "
                    "refused rather than run unconstrained."
                    % ctypes.get_last_error()
                )
        except BaseException:
            _terminate_quietly(proc)
            raise
        try:
            _resume_process_threads(proc.pid)
        except BaseException:
            _terminate_quietly(proc)
            raise
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            timeout_exc = JobTimeout("Job-controlled process timed out")
            timeout_exc.__cause__ = exc
            verified, alive = _terminate_job_and_verify(job)
            timeout_exc.descendants_verified_terminated = verified
            timeout_exc.alive_pids = alive
            raise timeout_exc
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    finally:
        # CloseHandle first: kill-on-close is the backstop that kills any
        # job member still alive; _reap_quietly then reaps the direct
        # child. Neither step may raise (see _reap_quietly), so the
        # original exception always propagates unchanged.
        _close_job_quietly(job)
        if proc is not None:
            _reap_quietly(proc)
