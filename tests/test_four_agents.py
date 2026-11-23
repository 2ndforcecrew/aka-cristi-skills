"""Contract tests: synthetic traces are NOT counted as real Codex invocations."""
import json
import os
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.verify_four_agents import (
    ROLES, decode_output, evaluate, find_role_tomls, json_lines, parse_spawn_calls, run,
)


def _mock_job_runner(fake_cli):
    """Synthetic mock for the Windows branch; NEVER runs a real Codex agent."""
    return patch.dict("sys.modules", {
        "tools.aka_windows_job_runner": SimpleNamespace(
            JobError=RuntimeError, JobTimeout=TimeoutError,
            run_in_job=lambda command, cwd, timeout, env=None: fake_cli(command, cwd=cwd, env=env))
    })


# E-247-2: env allowlist the fake CLI must receive (mirrors
# tools/codex_probe_isolation.py). Four-agents exec must carry
# --sandbox read-only and must NOT carry --ephemeral: its acceptance
# reads persisted rollout sessions (see rooted_sessions).
_ALLOWED_PROBE_ENV_KEYS = frozenset({
    "CODEX_HOME", "PATH", "Path", "SystemRoot", "SYSTEMROOT", "WINDIR",
    "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA",
    "LOCALAPPDATA", "COMSPEC", "PATHEXT",
})


def _assert_probe_env(testcase, env, home):
    testcase.assertIsNotNone(env, "CLI was invoked without an env")
    testcase.assertTrue(set(env) <= _ALLOWED_PROBE_ENV_KEYS,
                        "CLI env leaked non-allowlist keys: %s"
                        % sorted(set(env) - _ALLOWED_PROBE_ENV_KEYS))
    testcase.assertEqual(env.get("CODEX_HOME"), str(Path(home).resolve()))
    for secret in ("SECRET_TOKEN", "GH_TOKEN", "OPENAI_API_KEY"):
        testcase.assertNotIn(secret, env)


def _assert_exec_argv(testcase, cmd):
    testcase.assertIn("--sandbox", cmd)
    testcase.assertEqual(cmd[cmd.index("--sandbox") + 1], "read-only")
    testcase.assertNotIn("--ephemeral", cmd)


def _as_group_runner(fake_cli):
    """Adapt a (cmd, **kwargs) fake CLI to run_in_process_group's call shape.

    WP-C: the POSIX exec path runs through tools.chef_dual_engine
    .run_in_process_group (Popen + new process group) instead of
    subprocess.run; the --version / login probes still use
    subprocess.run, so both entry points share the same fake.
    """
    def group_runner(command, cwd, timeout, env=None, **kwargs):
        return fake_cli(command, cwd=cwd, timeout=timeout, env=env, **kwargs)
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


class FourAgentEvidenceTests(unittest.TestCase):
    def test_no_codex_returns_not_run(self):
        with patch("tools.verify_four_agents.shutil.which", return_value=None):
            result = run(codex_home=Path("/nonexistent-aka-codex"))
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertFalse(result["invoked"])

    def test_plain_text_claim_does_not_prove_spawn(self):
        text = json.dumps({"type": "item.completed", "item": {
            "type": "agent_message",
            "text": "I spawned aka_research, aka_coding, aka_qa, aka_automation"}})
        self.assertEqual(parse_spawn_calls(json_lines(text)), {})

    def test_task_name_label_not_custom_agent_role(self):
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "call_id": "call1", "arguments": json.dumps({
                "task_name": "aka_research", "prompt": "Hello"})}}
        output = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": json.dumps({"agent_id": str(uuid.uuid4())})}}
        self.assertEqual(parse_spawn_calls([call, output]), {})

    def test_generic_agent_type_not_custom_role(self):
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "call_id": "call1", "arguments": json.dumps({"agent_type": "worker"})}}
        output = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": json.dumps({"agent_id": str(uuid.uuid4())})}}
        self.assertEqual(parse_spawn_calls([call, output]), {})

    def test_exact_role_and_correlated_output_can_prove_spawn_stage(self):
        thread = str(uuid.uuid4())
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "functions.spawn_agent",
            "call_id": "call1", "arguments": json.dumps({
                "agent_type": "aka_research", "message": "Read fixture"})}}
        output = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": json.dumps({"agent_id": thread})}}
        result = parse_spawn_calls([call, output])
        self.assertEqual(result["aka_research"]["child_thread_id"], thread)

    def test_unpaired_call_or_failed_output_cannot_prove_spawn(self):
        call = {"type": "response_item", "payload": {
            "type": "function_call", "name": "spawn_agent",
            "call_id": "call1", "arguments": '{"agent_type":"aka_research"}'}}
        self.assertEqual(parse_spawn_calls([call]), {})
        out = {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call1",
            "output": "Failed to spawn " + str(uuid.uuid4())}}
        self.assertEqual(parse_spawn_calls([call, out]), {})

    def test_empty_real_rollout_is_inconclusive_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            result = evaluate([], Path(d), 0, str(uuid.uuid4()), 0, True)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertTrue(all(v == "NOT_VERIFIED" for v in result["roles"].values()))

    def test_no_child_rollout_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            tid = str(uuid.uuid4())
            session = home / "sessions" / ("rollout-" + tid + ".jsonl")
            session.parent.mkdir()
            session.write_text(json.dumps({"type": "session_meta",
                                          "payload": {"id": tid}}))
            result = evaluate([], home, 0, tid, 0, True)
        self.assertEqual(result["status"], "INCONCLUSIVE")

    def test_source_of_truth_contains_four_roles(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            folder = home / "agents"
            folder.mkdir()
            for name in ("research", "coding", "qa", "automation"):
                (folder / (name + ".toml")).write_bytes(
                    (root / "agents" / (name + ".toml")).read_bytes())
            checked = find_role_tomls(home)
        self.assertEqual(set(checked), set(ROLES))
        self.assertTrue(all(v == "PASS" for v in checked.values()))


    def test_utf8_jsonl_bytes_and_invalid_ansi_data_do_not_crash(self):
        event = {"type": "thread.started", "thread_id": str(uuid.uuid4()),
                 "note": "中文UTF-8"}
        payload = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
        records = json_lines(payload + b"invalid:\xff\n")
        self.assertEqual(records, [event])
        self.assertIn("中文UTF-8", decode_output(payload))
        self.assertEqual(json_lines(None), [])
        self.assertEqual(json_lines(b""), [])

    def test_windows_subprocess_output_in_bytes_is_handled(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "codex"
            agents = home / "agents"
            agents.mkdir(parents=True)
            for role in ("research", "coding", "qa", "automation"):
                (agents / (role + ".toml")).write_bytes(
                    (root / "agents" / (role + ".toml")).read_bytes())
            events = (json.dumps({"type": "thread.started",
                                  "thread_id": str(uuid.uuid4())}) + "\n" +
                      json.dumps({"type": "turn.completed"}) + "\n").encode("utf-8")
            def fake_cli(cmd, **kwargs):
                _assert_probe_env(self, kwargs.get("env"), home)
                if "--version" in cmd:
                    return SimpleNamespace(returncode=0,
                        stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
                if "login" in cmd:
                    return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
                _assert_exec_argv(self, cmd)
                print("[E-247-2] fake CLI env keys (PATH omitted):",
                      sorted(k for k in kwargs.get("env", {}) if k != "PATH"))
                return SimpleNamespace(returncode=0, stdout=events + b"\\xff",
                                       stderr=b"\\xff")
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home),
                                           "SECRET_TOKEN": "sentinel-2472",
                                           "GH_TOKEN": "sentinel-2472",
                                           "OPENAI_API_KEY": "sentinel-2472"}), \
                 patch("tools.verify_four_agents.shutil.which", return_value="codex.exe"), \
                 patch("tools.verify_four_agents.subprocess.run", side_effect=fake_cli), \
                 patch("tools.chef_dual_engine.run_in_process_group",
                       side_effect=_as_group_runner(fake_cli)), \
                 _mock_job_runner(fake_cli):
                result = run(codex_home=home)
            self.assertEqual(result["status"], "INCONCLUSIVE")
            self.assertTrue(result["invoked"])
            self.assertTrue(result["agent_completion_observed"])



class StrictCorrelationTests(unittest.TestCase):
    """All sessions in this class are SYNTHETIC protocol fixtures."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / 'sessions').mkdir()
        self.root = str(uuid.uuid4())
        self.children = {role: str(uuid.uuid4()) for role in ROLES}

    def write(self, tid, records):
        p = self.home / 'sessions' / ('rollout-' + tid + '.jsonl')
        p.write_text('\n'.join(json.dumps(x) for x in records), encoding='utf-8')
        return p

    def root_records(self):
        result = [{'type': 'session_meta', 'payload': {'id': self.root}}]
        for i, role in enumerate(ROLES):
            result += [
                {'type': 'response_item', 'payload': {'type': 'function_call',
                 'name': 'spawn_agent', 'call_id': str(i),
                 'arguments': json.dumps({'agent_type': role})}},
                {'type': 'response_item', 'payload': {'type': 'function_call_output',
                 'call_id': str(i), 'output': json.dumps({'agent_id': self.children[role]})}}]
        return result

    def child_records(self, role):
        return [
            {'type': 'session_meta', 'payload': {'id': self.children[role],
             'timestamp': '2026-11-15T12:00:00Z',
             'source': {'subagent': {'thread_spawn': {
                 'parent_thread_id': self.root, 'agent_role': role, 'depth': 1}}}}},
            {'type': 'response_item', 'payload': {'type': 'message',
             'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'Synthetic reply'}]}},
            {'type': 'event_msg', 'payload': {'type': 'task_complete',
             'turn_id': 'synthetic-turn', 'last_agent_message': 'Synthetic reply'}}]

    def assess(self, mutate=None, root_mutate=None):
        roots = self.root_records()
        if root_mutate:
            root_mutate(roots)
        self.write(self.root, roots)
        for role in ROLES:
            records = self.child_records(role)
            if mutate and role == ROLES[0]:
                mutate(records)
            self.write(self.children[role], records)
        return evaluate([], self.home, 0, self.root, 0, True)

    def test_complete_structured_correlation_passes_synthetic_contract(self):
        result = self.assess()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['role_stages'][ROLES[0]]['ROLE_PASS'], True)

    def test_unrelated_parent_never_passes(self):
        result = self.assess(lambda r: r[0]['payload']['source']['subagent']['thread_spawn'].update(parent_thread_id=str(uuid.uuid4())))
        self.assertEqual(result['roles'][ROLES[0]], 'NOT_VERIFIED')

    def test_wrong_child_metadata_id_never_passes(self):
        result = self.assess(lambda r: r[0]['payload'].update(id=str(uuid.uuid4())))
        self.assertNotEqual(result['status'], 'PASS')

    def test_substring_role_never_passes(self):
        result = self.assess(lambda r: r[0]['payload']['source']['subagent']['thread_spawn'].update(agent_role='prefix_aka_research'))
        self.assertNotEqual(result['status'], 'PASS')

    def test_intermediate_reply_without_completion_never_passes(self):
        result = self.assess(lambda r: r.pop())
        self.assertNotEqual(result['status'], 'PASS')

    def test_failed_completion_never_passes(self):
        result = self.assess(lambda r: r[-1]['payload'].update(error={'message': 'synthetic failure'}))
        self.assertNotEqual(result['status'], 'PASS')

    def test_conflicting_metadata_roles_never_pass(self):
        result = self.assess(lambda r: r[0]['payload'].update(agent_role='aka_coding'))
        self.assertNotEqual(result['status'], 'PASS')

    def test_duplicate_child_for_multiple_roles_never_passes(self):
        self.children[ROLES[1]] = self.children[ROLES[0]]
        self.assertNotEqual(self.assess()['status'], 'PASS')

    def test_wrong_root_metadata_id_never_passes(self):
        result = self.assess(root_mutate=lambda r: r[0]['payload'].update(id=str(uuid.uuid4())))
        self.assertNotEqual(result['status'], 'PASS')

    def test_prose_uuid_output_is_not_spawn_success(self):
        records = self.root_records()
        records[2]['payload']['output'] = 'reference ' + self.children[ROLES[0]]
        self.assertNotIn(ROLES[0], parse_spawn_calls(records))

    def test_structured_error_with_uuid_is_not_spawn_success(self):
        records = self.root_records()
        records[2]['payload']['output'] = json.dumps({'error': 'denied', 'agent_id': self.children[ROLES[0]]})
        self.assertNotIn(ROLES[0], parse_spawn_calls(records))

    def test_unknown_output_schema_is_not_spawn_success(self):
        records = self.root_records()
        records[2]['payload']['output'] = json.dumps({'message': self.children[ROLES[0]]})
        self.assertNotIn(ROLES[0], parse_spawn_calls(records))

    def test_old_child_session_touched_recently_never_passes(self):
        self.assess()
        # mtime is fresh, but the recorded child creation predates this run.
        result = evaluate([], self.home, time.time(), self.root, 0, True)
        self.assertNotEqual(result['status'], 'PASS')


class IsolatedRoleSourceTests(unittest.TestCase):
    def test_public_roles_can_be_staged_without_global_host_install(self):
        public = Path(__file__).resolve().parents[1] / "agents"
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "codex"
            home.mkdir()
            calls = []
            def cli(command, **kwargs):
                _assert_probe_env(self, kwargs.get("env"), home)
                calls.append(command)
                if "--version" in command:
                    return SimpleNamespace(returncode=0,
                        stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
                if "login" in command:
                    return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
                _assert_exec_argv(self, command)
                for role in ROLES:
                    override = next(x for x in command if x.startswith(
                        "agents." + role + ".config_file="))
                    path = Path(json.loads(override.split("=", 1)[1]))
                    self.assertTrue(path.is_file())
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home)}), \
                 patch("tools.verify_four_agents.shutil.which", return_value="codex"), \
                 patch("tools.verify_four_agents.subprocess.run", side_effect=cli), \
                 patch("tools.chef_dual_engine.run_in_process_group",
                       side_effect=_as_group_runner(cli)), \
                 _mock_job_runner(cli):
                result = run(codex_home=home, role_source=public)
            self.assertTrue(result["invoked"])
            self.assertTrue(home.exists())
            self.assertEqual(result["role_configuration"],
                             "TEMPORARY_PER_PROCESS_OVERRIDES")



class CliFailureTests(unittest.TestCase):
    def test_nonzero_cli_returns_sanitized_failure_without_raw_stderr(self):
        public = Path(__file__).resolve().parents[1] / "agents"
        def cli(command, **kwargs):
            _assert_probe_env(self, kwargs.get("env"), home)
            if "--version" in command:
                return SimpleNamespace(returncode=0,
                    stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
            if "login" in command:
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            _assert_exec_argv(self, command)
            return SimpleNamespace(returncode=1, stdout=b"",
                stderr=b"error: unexpected argument --json SECRET_SENTINEL")
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "codex"
            home.mkdir()
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home)}), \
                 patch("tools.verify_four_agents.shutil.which", return_value="codex"), \
                 patch("tools.verify_four_agents.subprocess.run", side_effect=cli), \
                 patch("tools.chef_dual_engine.run_in_process_group",
                       side_effect=_as_group_runner(cli)), \
                 _mock_job_runner(cli):
                result = run(codex_home=home, role_source=public)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failure_category"], "CLI_OPTION_REJECTED")
        self.assertNotIn("SECRET_SENTINEL", json.dumps(result))


class TimeoutReportingTests(unittest.TestCase):
    """E-247-3: a timeout must report descendants as unverified, FAIL."""

    def _stage_home(self, temp):
        root = Path(__file__).resolve().parents[1]
        home = Path(temp) / "codex"
        agents = home / "agents"
        agents.mkdir(parents=True)
        for role in ("research", "coding", "qa", "automation"):
            (agents / (role + ".toml")).write_bytes(
                (root / "agents" / (role + ".toml")).read_bytes())
        return home

    def test_job_timeout_reports_descendants_unverified_and_fail(self):
        class _JobTimeout(Exception):
            pass

        def raising_job(command, cwd, timeout, env=None):
            raise _JobTimeout("simulated job timeout")

        def fake_subprocess(cmd, **kwargs):
            if "--version" in cmd:
                return SimpleNamespace(returncode=0,
                    stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
            if "login" in cmd:
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            raise AssertionError("unexpected subprocess.run call: %r" % (cmd,))

        with tempfile.TemporaryDirectory() as temp:
            home = self._stage_home(temp)
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home)}), \
                 patch("tools.verify_four_agents.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_four_agents.subprocess.run",
                       side_effect=fake_subprocess), \
                 patch("tools.verify_four_agents.os",
                       SimpleNamespace(name="nt")), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=_JobTimeout,
                     run_in_job=raising_job)}):
                result = run(codex_home=home)
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

        def raising_job(command, cwd, timeout, env=None):
            raise _JobTimeout()

        def fake_subprocess(cmd, **kwargs):
            if "--version" in cmd:
                return SimpleNamespace(returncode=0,
                    stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
            if "login" in cmd:
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            raise AssertionError("unexpected subprocess.run call: %r" % (cmd,))

        with tempfile.TemporaryDirectory() as temp:
            home = self._stage_home(temp)
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home)}), \
                 patch("tools.verify_four_agents.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_four_agents.subprocess.run",
                       side_effect=fake_subprocess), \
                 patch("tools.verify_four_agents.os",
                       SimpleNamespace(name="nt")), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=_JobTimeout,
                     run_in_job=raising_job)}):
                result = run(codex_home=home)
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

        def raising_job(command, cwd, timeout, env=None):
            raise _JobTimeout()

        def fake_subprocess(cmd, **kwargs):
            if "--version" in cmd:
                return SimpleNamespace(returncode=0,
                    stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
            if "login" in cmd:
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            raise AssertionError("unexpected subprocess.run call: %r" % (cmd,))

        with tempfile.TemporaryDirectory() as temp:
            home = self._stage_home(temp)
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home)}), \
                 patch("tools.verify_four_agents.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_four_agents.subprocess.run",
                       side_effect=fake_subprocess), \
                 patch("tools.verify_four_agents.os",
                       SimpleNamespace(name="nt")), \
                 patch.dict("sys.modules", {"tools.aka_windows_job_runner": SimpleNamespace(
                     JobError=RuntimeError, JobTimeout=_JobTimeout,
                     run_in_job=raising_job)}):
                result = run(codex_home=home)
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

        def fake_subprocess(cmd, **kwargs):
            if "--version" in cmd:
                return SimpleNamespace(returncode=0,
                    stdout=b"codex-cli 0.167.0-alpha.4", stderr=b"")
            if "login" in cmd:
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            raise AssertionError("unexpected subprocess.run call: %r" % (cmd,))

        with tempfile.TemporaryDirectory() as temp:
            home = self._stage_home(temp)
            with patch.dict("os.environ", {"AKA_CODEX_PROBE_HOME": str(home)}), \
                 patch("tools.verify_four_agents.shutil.which",
                       return_value="codex"), \
                 patch("tools.verify_four_agents.subprocess.run",
                       side_effect=fake_subprocess), \
                 patch("tools.chef_dual_engine.run_in_process_group",
                       side_effect=raising_group):
                result = run(codex_home=home)
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
            home = self._stage_home(temp)
            bin_dir = Path(temp) / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "codex"
            fake.write_text(_FAKE_CODEX_SCRIPT, encoding="utf-8")
            fake.chmod(0o700)
            with patch.dict("os.environ", {
                    "AKA_CODEX_PROBE_HOME": str(home),
                    "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}):
                result = run(timeout=1, codex_home=home)
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


if __name__ == "__main__":
    unittest.main()
