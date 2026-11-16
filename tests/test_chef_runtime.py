"""Offline orchestration tests. Fake processes NEVER prove live acceptance."""
import json
from contextlib import closing
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import chef_dual_engine as runtime


class IsolatedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        for args in [('init',), ('config', 'user.email', 'test@example.invalid'),
                     ('config', 'user.name', 'Test')]:
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
        (self.repo / 'input.txt').write_text('original\n')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-m', 'baseline'], check=True, capture_output=True)
        self.db = self.root / 'events.db'

    def tearDown(self):
        self.temp.cleanup()

    def test_isolation_handoff_and_separate_qa(self):
        calls = []
        def agent(role, prompt, workspace, timeout, **kwargs):
            calls.append((role, Path(workspace), prompt, kwargs))
            if role == 'factory':
                (Path(workspace) / 'input.txt').write_text('changed\n')
            else:
                self.assertEqual((Path(workspace) / 'input.txt').read_text(), 'changed\n')
                self.assertIn('deliverables', prompt)
            return {'status': 'COMPLETED', 'thread_ids': [role], 'output': role + ' evidence'}
        with patch.object(runtime, 'run_codex', side_effect=agent):
            result = runtime.orchestrate('hybrid', 'repair', self.repo, self.db)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertEqual((self.repo / 'input.txt').read_text(), 'original\n')
        self.assertEqual(len({c[1] for c in calls}), 3)
        self.assertEqual(calls[0][3]['sandbox'], 'workspace-write')
        self.assertEqual(calls[-1][3]['sandbox'], 'read-only')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('select status from tasks').fetchone()[0], 'REVIEW_REQUIRED')
        self.assertEqual(result['release'], 'BLOCKED')

    def test_resume_reuses_completed_roles_not_failed_work(self):
        calls = []
        def agent(role, prompt, workspace, timeout, **kwargs):
            calls.append(role)
            return {'status': 'FAILED' if calls == ['factory', 'studio'] else 'COMPLETED',
                    'thread_ids': [role + str(len(calls))], 'output': 'evidence'}
        with patch.object(runtime, 'run_codex', side_effect=agent):
            first = runtime.orchestrate('hybrid', 'repair', self.repo, self.db)
            self.assertEqual(first['status'], 'BLOCKED')
            second = runtime.orchestrate('hybrid', 'repair', self.repo, self.db, task_id=first['task_id'])
        self.assertEqual(calls, ['factory', 'studio', 'studio', 'qa'])
        self.assertEqual(second['status'], 'REVIEW_REQUIRED')
        with self.assertRaises(ValueError):
            runtime.orchestrate('factory', 'different', self.repo, self.db, task_id=first['task_id'])

    def test_same_thread_cannot_be_independent_qa(self):
        with patch.object(runtime, 'run_codex', return_value={
                'status': 'COMPLETED', 'thread_ids': ['same'], 'output': 'ok'}):
            result = runtime.orchestrate('factory', 'inspect', self.repo, self.db)
        self.assertEqual(result['status'], 'BLOCKED')

    def test_invalid_timeout_rejected_before_launch(self):
        with self.assertRaises(ValueError):
            runtime.orchestrate('factory', 'x', self.repo, self.db, timeout=0)

    def test_interruption_counts_attempt_and_is_resumable(self):
        with patch.object(runtime, 'run_codex', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                runtime.orchestrate('factory', 'inspect', self.repo, self.db)
        with closing(sqlite3.connect(self.db)) as db:
            task_id = db.execute('select task_id from tasks').fetchone()[0]
            self.assertEqual(db.execute('select count(*) from attempts').fetchone()[0], 1)
        with patch.object(runtime, 'run_codex', return_value={
                'status': 'FAILED', 'reason': 'offline fixture'}):
            result = runtime.orchestrate('factory', 'inspect', self.repo, self.db, task_id=task_id)
        self.assertEqual(result['status'], 'BLOCKED')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('select count(*) from attempts').fetchone()[0], 2)

    def test_retry_budget_is_bounded(self):
        with patch.object(runtime, 'run_codex', return_value={'status': 'FAILED'}) as agent:
            result = runtime.orchestrate('factory', 'inspect', self.repo, self.db)
            for _ in range(4):
                result = runtime.orchestrate('factory', 'inspect', self.repo, self.db, task_id=result['task_id'])
        self.assertEqual(agent.call_count, 3)
        self.assertEqual(result['status'], 'BLOCKED')

    def test_read_only_role_mutation_blocks_review(self):
        def agent(role, prompt, workspace, timeout, **kwargs):
            (Path(workspace) / 'input.txt').write_text('tampered')
            return {'status': 'COMPLETED', 'thread_ids': [role], 'output': 'report'}
        with patch.object(runtime, 'run_codex', side_effect=agent):
            result = runtime.orchestrate('studio', 'inspect', self.repo, self.db)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['qa'], 'NOT_RUN')

    def test_completed_snapshot_mutation_prevents_resume(self):
        with patch.object(runtime, 'run_codex', side_effect=[
                {'status': 'COMPLETED', 'thread_ids': ['factory'], 'output': 'report'},
                {'status': 'FAILED'}]):
            result = runtime.orchestrate('hybrid', 'inspect', self.repo, self.db)
        (Path(result['results']['factory']['workspace']) / 'input.txt').write_text('tampered')
        with self.assertRaises(ValueError):
            runtime.orchestrate('hybrid', 'inspect', self.repo, self.db, task_id=result['task_id'])

    @unittest.skipUnless(__import__('os').name == 'posix', 'POSIX process group regression')
    def test_actual_subprocess_timeout_kills_descendant(self):
        import os
        import time
        executable = self.root / 'codex'
        marker = self.root / 'orphan-wrote'
        executable.write_text('#!/usr/bin/env python3\nimport subprocess, sys, time\n'
                              'subprocess.Popen([sys.executable, "-c", '
                              + repr('import time; from pathlib import Path; time.sleep(0.8); Path(' + repr(str(marker)) + ').write_text("orphan")')
                              + '])\ntime.sleep(20)\n')
        executable.chmod(0o700)
        with patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}):
            result = runtime.run_codex('qa', 'fixture', self.repo, timeout=0.2)
        self.assertEqual(result['reason'], 'timeout')
        time.sleep(1)
        self.assertFalse(marker.exists(), 'timed-out descendant survived and wrote output')

    @unittest.skipUnless(__import__('os').name == 'posix', 'POSIX scripted CLI fixture')
    def test_cli_e2e_scripted_host_failure_resume_and_qa(self):
        """Real local CLI/Git/SQLite pipeline, SCRIPTED host, not live AI acceptance."""
        import os
        import sys
        executable = self.root / 'codex'
        executable.write_text('''#!/usr/bin/env python3
import json, os, sys, uuid
prompt = sys.argv[-1].split("Task: ", 1)[1]
role = json.loads(prompt.split("\\nInspect prior deliverables.")[0])["role"]
if os.environ.get("CHEF_FIXTURE_FAIL") == role:
    print(json.dumps({"type": "turn.failed"}))
    raise SystemExit(1)
if role == "factory":
    from pathlib import Path
    Path("input.txt").write_text("proposal\\n")
print(json.dumps({"type": "thread.started", "thread_id": role + str(uuid.uuid4())}))
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "SCRIPTED FIXTURE: " + role}}))
print(json.dumps({"type": "turn.completed"}))
''')
        executable.chmod(0o700)
        env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ['PATH'],
                   CHEF_FIXTURE_FAIL='studio')
        command = [sys.executable, '-m', 'tools.chef_dual_engine', '--kind', 'hybrid',
                   '--prompt', 'scripted offline journey', '--workspace', str(self.repo),
                   '--db', str(self.db), '--timeout', '5']
        failed = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(failed.returncode, 2, failed.stderr)
        first = json.loads(failed.stdout)
        self.assertEqual(first['qa'], 'NOT_RUN')
        env.pop('CHEF_FIXTURE_FAIL')
        resumed = subprocess.run(command + ['--resume', first['task_id']], env=env,
                                 capture_output=True, text=True, check=False)
        self.assertEqual(resumed.returncode, 0, resumed.stderr + resumed.stdout)
        result = json.loads(resumed.stdout)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertEqual(result['release'], 'BLOCKED')
        self.assertEqual(result['results']['factory']['snapshot'], first['results']['factory']['snapshot'])
        self.assertEqual((Path(result['qa']['workspace']) / 'input.txt').read_text(), 'proposal\n')
        self.assertEqual((self.repo / 'input.txt').read_text(), 'original\n')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('select count(*) from attempts').fetchone()[0], 4)

    @unittest.skipUnless(__import__('os').name == 'posix', 'POSIX private log permissions')
    def test_private_database_and_lock(self):
        import stat
        import os
        previous = os.umask(0o022)
        try:
            with patch.object(runtime, 'run_codex', return_value={'status': 'NOT_RUN'}):
                runtime.orchestrate('factory', 'private objective', self.repo, self.db)
        finally:
            os.umask(previous)
        for path in (self.db, Path(str(self.db) + '.lock')):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    @unittest.skipUnless(__import__('os').name == 'posix', 'POSIX symlink regression')
    def test_database_symlink_is_rejected_before_resolving(self):
        target = self.root / 'private.db'
        runtime.init_db(target).close()
        self.db.symlink_to(target)
        with self.assertRaises(ValueError):
            runtime.orchestrate('factory', 'inspect', self.repo, self.db)
