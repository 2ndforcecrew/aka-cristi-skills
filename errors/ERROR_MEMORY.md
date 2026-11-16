# Error memory

## 2026-11-16 — One-click recovery stopped at REUSE_REQUIRED

- Baseline: Universal candidate cb2782bbd54d2971d761bf8ddc7f30e2d6215fc5; CI run 43784356310.
- Symptom: repeat setup stopped at repository; the conflict scenario never reached preview.
- Root cause: every run selected with reuse=False, treating the persisted authorized repository as a newly discovered existing repository.
- Fix: opt-in resume for the exact saved owner/repository only, after existing remote identity/private/push/URL validation; manual reuse and confirmation gates remain.
- Verified: original two regressions plus fresh-controller recovery and repository-security checks pass on Windows 10 Pro 19045 / Python 3.13.11. No real GitHub writes were performed.

## 2026-11-16 — Windows test fixture encoding and symlink privileges

- Symptom: UTF-8 public rules were read using the default GBK locale in rollback fixtures; two symlink fixtures raised WinError 1314 before reaching their security assertion.
- Fix: explicit UTF-8 fixture I/O; skip only unavailable symlink creation with winerror=1314, re-raise other errors. Production link rejection remains unchanged.
- Verified: full suite ran 254 tests: 240 passed, 14 skipped. Actual Windows junction rejection tests passed. Ruff, Mypy, compileall and diff checks passed.
- Limits: symlink checks are NOT RUN on this privilege-limited host; two unrelated checks share an existing symlink setup and are also skipped. Existing Tk poll callback messages remain. No release/security gate is cleared.

## 2026-11-16 — Universal safety and live-proof follow-up

- Builder descriptions required quoted serialization and escaping YAML/Python line separators; actual writes now use the same checked, expanded absolute destination as preview. Real Windows junction tests exposed the unchecked tilde-path mismatch before repair.
- Lifecycle now rejects unreadable traversal, stat/read failures and reparse/ancestor redirects without returning a partial digest. Negative OS-error and actual junction regressions pass.
- Shared symlink setup unnecessarily skipped two unrelated checks; prerequisites are now scoped to the three tests needing them. Remote Windows CI ran the original fourteen skipped checks successfully.
- Isolated Skill probes failed before model execution because a non-Git temporary directory lacked --skip-git-repo-check; explicit UTF-8 decoding also avoids the Windows ANSI-code-page assumption. The read-only sandbox remains enforced.
- Live four-role calls in Codex 0.169.0 returned canonical task_name, not UUID. Preserve the initial INCONCLUSIVE result; official app activities map the exact call_id/path to UUID, and existing strict child metadata/completion checks corroborate the actual parent/role/reply. Never treat a task label alone as proof.
- Verification: 265 local tests (253 passed, 12 privilege skips), expanded lint/type/compile checks and independent QA; actual scanned feature-journey-map and native four-role executions passed within synthetic read-only scope. Formal release and external UAT remain separate.
