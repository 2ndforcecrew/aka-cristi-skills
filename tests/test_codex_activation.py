"""Offline tests of activation EVIDENCE JUDGING, not real Codex runs."""
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.verify_codex_activation import assess, parse_events, run


NAME = "verified-change-loop"
NONCE = "AKA-PROBE-12345ABC"


def trace(name=NAME, nonce=NONCE):
    return [
        {"type": "thread.started", "thread_id": "fixture-only"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {
            "type": "command_execution",
            "command": "cat .agents/skills/" + name + "/SKILL.md",
            "exit_code": 0}},
        {"type": "item.completed", "item": {
            "type": "command_execution", "command": "cat CASE.md", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "agent_message",
            "text": "Case ID: " + nonce + ". Live defect reproduction NOT_RUN."}},
        {"type": "turn.completed", "usage": {"input_tokens": 42}},
    ]


def _as_group_runner(fake_run):
    """Adapt a (args, **kwargs) fake CLI to run_in_process_group's call shape.

    WP-C: the POSIX exec path runs through tools.chef_dual_engine
    .run_in_process_group (Popen + new process group) instead of
    subprocess.run; the login probe still uses subprocess.run, so both
    entry points share the same fake.
    """
    def group_runner(command, cwd, timeout, env=None, **kwargs):
        return fake_run(command, cwd=cwd, timeout=timeout, env=env, **kwargs)
    return group_runner


# WP-C: real fake Codex CLI for POSIX process-group tests. The exec
# branch records its own pid and its grandchild's pid, spawns a
# grandchild that would write a marker after 2s, then sleeps. A correct
# process-group kill on timeout means the marker never appears and
# both recorded PIDs are gone.
_FAKE_CODEX_SCRIPT = '''#!/usr/bin/env python3
import os
import subprocess
import sys
import time
from pathlib import Path

here = Path(sys.argv[0]).resolve().parent
if sys.argv[1:2] == ["--version"]:
    print("codex-cli 0.0.0-test")
    raise SystemExit(0)
if sys.argv[1:3] == ["login", "status"]:
    raise SystemExit(0)
(here / "child.pid").write_text(str(os.getpid()))
grandchild = subprocess.Popen([sys.executable, "-c",
    "import time; from pathlib import Path; time.sleep(2.0); "
    "Path(" + repr(str(here / "orphan-wrote")) + ").write_text('orphan')"])
(here / "grandchild.pid").write_text(str(grandchild.pid))
time.sleep(60)
'''


def _pid_gone(pid, timeout=2.0):
    """True when *pid* is gone (a Linux zombie awaiting reaping counts as gone)."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        if os.name == "posix":
            try:
                state = Path("/proc", str(pid), "stat").read_text(
                    encoding="utf-8", errors="replace").rsplit(")", 1)[-1].split()[0]
                if state == "Z":
                    return True
            except (OSError, IndexError):
                return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


class CodexAgentEvidenceTests(unittest.TestCase):
    def test_synthetic_positive_evidence(self):
        self.assertEqual(assess(trace(), NAME, NONCE, 0)["status"], "PASS")

    def test_no_skill_file_read_fails(self):
        x = trace()
        x[2]["item"]["command"] = "echo loaded"
        self.assertEqual(assess(x, NAME, NONCE, 0)["status"], "FAIL")

    def test_no_case_read_fails(self):
        x = trace()
        x[3]["item"]["command"] = "echo CASE.md"
        self.assertEqual(assess(x, NAME, NONCE, 0)["status"], "FAIL")

    def test_wrong_case_id_fails(self):
        self.assertEqual(assess(trace(), NAME, "DIFFERENT", 0)["status"], "FAIL")

    def test_no_completed_agent_turn_fails(self):
        self.assertEqual(assess(trace()[:-1], NAME, NONCE, 0)["status"], "FAIL")

    def test_failed_exit_fails(self):
        self.assertEqual(assess(trace(), NAME, NONCE, 1)["status"], "FAIL")

    def test_no_events_fails(self):
        self.assertEqual(assess([], NAME, NONCE, 0)["status"], "FAIL")

    def test_parse_jsonl_ignores_noise(self):
        line = "not-json\n" + "\n".join(json.dumps(x) for x in trace())
        self.assertEqual(len(parse_events(line)), len(trace()))

    def test_temporary_workspace_probe_has_required_cli_options_and_utf8(self):
        calls = []
        # E-247-2: every fake CLI invocation must receive only allowlist
        # env keys, with CODEX_HOME equal to the dedicated probe home.
        allowed = {"CODEX_HOME", "PATH", "Path", "SystemRoot", "SYSTEMROOT",
                   "WINDIR", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE",
                   "APPDATA", "LOCALAPPDATA", "COMSPEC", "PATHEXT"}
        def fake_run(args, **kwargs):
            env = kwargs.get("env") or {}
            self.assertTrue(set(env) <= allowed,
                            "fake CLI env leaked non-allowlist keys: %s"
                            % sorted(set(env) - allowed))
            self.assertEqual(env.get("CODEX_HOME"),
                             str(Path(os.environ["AKA_CODEX_PROBE_HOME"]).resolve()))
            for secret in ("SECRET_TOKEN", "GH_TOKEN", "OPENAI_API_KEY"):
                self.assertNotIn(secret, env)
            print("[E-247-2] fake CLI env keys (PATH omitted):",
                  sorted(k for k in env if k != "PATH"))
            if args[1:3] == ["login", "status"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            calls.append((args, kwargs))
            case = (Path(kwargs["cwd"]) / "CASE.md").read_text(encoding="utf-8")
            nonce = next(line.split(": ", 1)[1] for line in case.splitlines()
                         if line.startswith("Case ID: "))
            events = trace("feature-journey-map", nonce)
            return subprocess.CompletedProcess(
                args, 0, "\n".join(json.dumps(x, ensure_ascii=False) for x in events), "")
        with tempfile.TemporaryDirectory() as dedicated:
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": dedicated,
                                           "SECRET_TOKEN": "sentinel-2472",
                                           "GH_TOKEN": "sentinel-2472",
                                           "OPENAI_API_KEY": "sentinel-2472"}), \
                 patch("tools.verify_codex_activation.shutil.which", return_value="codex"), \
                 patch("tools.verify_codex_activation.subprocess.run", side_effect=fake_run), \
                 patch("tools.chef_dual_engine.run_in_process_group",
                       side_effect=_as_group_runner(fake_run)), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=TimeoutError,
                     run_in_job=lambda args, cwd, timeout, env=None: fake_run(args, cwd=cwd, env=env))}):
                result = run("feature-journey-map")
        self.assertEqual(result["status"], "PASS")
        args, options = calls[0]
        self.assertIn("--skip-git-repo-check", args)
        if os.name != "nt":
            self.assertEqual(options.get("encoding"), "utf-8")
            self.assertEqual(options.get("errors"), "replace")
        self.assertEqual(args[args.index("--sandbox") + 1], "read-only")
        self.assertIn("--ephemeral", args)
        self.assertEqual(options["env"]["CODEX_HOME"],
                         str(Path(dedicated).resolve()))
        self.assertTrue(set(options["env"]) <= allowed)

    def test_job_timeout_reports_descendants_unverified_and_fail(self):
        # E-247-3: mock run_in_job raising JobTimeout (Windows branch).
        # The nt branch is forced by patching this module's os.name only;
        # probe_environment and tempfile keep their own os references.
        class _JobTimeout(Exception):
            pass

        def raising_job(args, cwd, timeout, env=None):
            raise _JobTimeout()

        def fake_login(args, **kwargs):
            if args[1:3] == ["login", "status"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            raise AssertionError("unexpected subprocess.run call: %r" % (args,))

        with tempfile.TemporaryDirectory() as dedicated:
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": dedicated}), \
                 patch("tools.verify_codex_activation.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_codex_activation.subprocess.run",
                       side_effect=fake_login), \
                 patch("tools.verify_codex_activation.os",
                       SimpleNamespace(name="nt")), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=_JobTimeout,
                     run_in_job=raising_job)}):
                result = run("feature-journey-map")
        self.assertEqual(result["status"], "FAIL")
        self.assertNotEqual(result["status"], "PASS")
        self.assertNotEqual(result["status"], "INCONCLUSIVE")
        self.assertIs(result["descendants_verified_terminated"], False)
        self.assertTrue(result["invoked"])

    def test_job_timeout_verified_true_propagates(self):
        # WP-C: WP-B's run_in_job reports True only when the job was
        # confirmed empty; verify_* must pass that through, not hardcode False.
        class _JobTimeout(Exception):
            def __init__(self):
                super().__init__("simulated job timeout")
                self.descendants_verified_terminated = True
                self.alive_pids = []

        def raising_job(args, cwd, timeout, env=None):
            raise _JobTimeout()

        def fake_login(args, **kwargs):
            if args[1:3] == ["login", "status"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            raise AssertionError("unexpected subprocess.run call: %r" % (args,))

        with tempfile.TemporaryDirectory() as dedicated:
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": dedicated}), \
                 patch("tools.verify_codex_activation.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_codex_activation.subprocess.run",
                       side_effect=fake_login), \
                 patch("tools.verify_codex_activation.os",
                       SimpleNamespace(name="nt")), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=_JobTimeout,
                     run_in_job=raising_job)}):
                result = run("feature-journey-map")
        self.assertEqual(result["status"], "FAIL")
        self.assertIs(result["descendants_verified_terminated"], True)
        self.assertEqual(result.get("alive_pids"), [])
        self.assertTrue(result["invoked"])

    def test_job_timeout_verification_failure_reports_alive_pids(self):
        # WP-C: a failed verification must stay False and echo alive_pids.
        class _JobTimeout(Exception):
            def __init__(self):
                super().__init__("simulated job timeout")
                self.descendants_verified_terminated = False
                self.alive_pids = [424242]

        def raising_job(args, cwd, timeout, env=None):
            raise _JobTimeout()

        def fake_login(args, **kwargs):
            if args[1:3] == ["login", "status"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            raise AssertionError("unexpected subprocess.run call: %r" % (args,))

        with tempfile.TemporaryDirectory() as dedicated:
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": dedicated}), \
                 patch("tools.verify_codex_activation.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_codex_activation.subprocess.run",
                       side_effect=fake_login), \
                 patch("tools.verify_codex_activation.os",
                       SimpleNamespace(name="nt")), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=_JobTimeout,
                     run_in_job=raising_job)}):
                result = run("feature-journey-map")
        self.assertEqual(result["status"], "FAIL")
        self.assertIs(result["descendants_verified_terminated"], False)
        self.assertEqual(result.get("alive_pids"), [424242])
        self.assertTrue(result["invoked"])

    def test_posix_timeout_verification_failure_reports_tree_unverified_and_fail(self):
        # WP-C update of the WP-D mock test: the POSIX exec path now
        # runs through run_in_process_group, so the failure is mocked
        # there instead of on subprocess.run. Intent unchanged: FAIL,
        # tree unverified, field not True.
        from tools.chef_dual_engine import ProcessGroupTimeout

        def raising_group(command, cwd, timeout, env=None, **kwargs):
            raise ProcessGroupTimeout(command, timeout,
                                      descendants_verified_terminated=False,
                                      alive_pids=[424242])

        def fake_login(args, **kwargs):
            if args[1:3] == ["login", "status"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            raise AssertionError("unexpected subprocess.run call: %r" % (args,))

        with tempfile.TemporaryDirectory() as dedicated:
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": dedicated}), \
                 patch("tools.verify_codex_activation.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_codex_activation.subprocess.run",
                       side_effect=fake_login), \
                 patch("tools.chef_dual_engine.run_in_process_group",
                       side_effect=raising_group):
                result = run("feature-journey-map")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("POSIX tree unverified", result["reason"])
        self.assertIs(result["descendants_verified_terminated"], False)
        self.assertEqual(result.get("alive_pids"), [424242])

    @unittest.skipUnless(os.name == "posix", "POSIX process group regression")
    def test_posix_timeout_kills_process_group_and_verifies(self):
        # WP-C: real fake CLI (not a subprocess.run mock). The exec
        # spawns a grandchild that would write a marker after 2s; the
        # run times out after 1s, so a correct process-group kill means
        # the marker never appears, both recorded PIDs are gone, and
        # the report carries descendants_verified_terminated True.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "codex"
            fake.write_text(_FAKE_CODEX_SCRIPT, encoding="utf-8")
            fake.chmod(0o700)
            skill_dir = root / "skills" / "verified-change-loop"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: verified-change-loop\ndescription: test\n---\n",
                encoding="utf-8")
            dedicated = root / "home"
            dedicated.mkdir()
            with patch.dict("os.environ", {
                    "AKA_CODEX_PROBE_HOME": str(dedicated),
                    "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}):
                result = run("verified-change-loop", codex="codex",
                             timeout=1, root=root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIs(result["descendants_verified_terminated"], True)
            self.assertEqual(result.get("alive_pids"), [])
            self.assertTrue(result["invoked"])
            time.sleep(2.5)  # Past the grandchild's 2s marker delay.
            self.assertFalse((bin_dir / "orphan-wrote").exists(),
                             "timed-out grandchild survived and wrote output")
            for name in ("child.pid", "grandchild.pid"):
                pid = int((bin_dir / name).read_text(encoding="utf-8"))
                self.assertTrue(_pid_gone(pid), "%s %d still alive" % (name, pid))

    def test_missing_codex_reports_not_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "skills" / NAME
            src.mkdir(parents=True)
            (src / "SKILL.md").write_text(
                "---\nname: verified-change-loop\ndescription: test\n---\n",
                encoding="utf-8")
            with patch("tools.verify_codex_activation.shutil.which",
                       return_value=None):
                result = run(NAME, root=root)
            self.assertEqual(result["status"], "NOT_RUN")
            self.assertFalse(result["invoked"])


if __name__ == "__main__":
    unittest.main()
