# Windows graphical installer — candidate, not yet externally accepted

Status: real Tk graphical flow and local transaction backend implemented. **Not a standalone signed Windows EXE.** Windows 11 standard-user acceptance, prerequisite auto-install and a verified remote GUI download flow remain **BLOCKED / NOT_RUN**. No live Agent activation is implied.

## Run from a trusted complete checkout

Prerequisites: Python 3.11+ including Tk (included in official Python Windows installers); Codex CLI installed separately. No elevation is required. Review the checkout or verify a candidate archive's provenance using [release verification](RELEASE_VERIFICATION.md) before running code.

Double-click `start-gui.cmd`, or run:

```powershell
python -m tools.gui_installer
```

The launcher only starts the Python application. It does not download Python or Codex, change execution policy, or bypass a signature check. Without Python it shows an actionable terminal message. Without Codex, the GUI permits preview and blocks installation. Without Tk or a graphical display it reports `BLOCKED`.

1. Select the trusted local source folder and check the two target directories. Codex defaults to `CODEX_HOME` or `~/.codex`; Skills default to `~/.agents/skills`.
2. Confirm that you reviewed or verified the source, then choose **检查与预览**. This reads configuration without writing user files.
3. Inspect the full local before/after `AGENTS.md` diff and the expected four Skills/four roles. Private pre-existing rules are visible only in this local window, never in the progress log.
4. Explicitly consent to backing up and applying those changes. Installation stays disabled until this consent and a successful preview exist.
5. **安装并校验文件** appends managed global rules, installs the four Skills and four TOML roles, then verifies integrity. The success state is `FILES_VERIFIED`, with actual Agent activation **NOT_RUN**.
6. **取消并恢复** requests cancellation at the next safe checkpoint, restores completed changes and preserves the local journal. A 60-second UI watchdog requests the same safe cancellation; it never kills a file write halfway through. Disk operations themselves cannot be safely force-terminated.
7. **撤销本次安装** restores the before-install bytes after an additional confirmation. Any subsequent managed file or directory changes block rollback to preserve edits. This button operates on this GUI session's completed transaction only.

## Safety, logs and recovery

- All changes use the existing Python installers. Before every install, the source/configuration fingerprints must still match the preview. A stale preview, unmanaged files or edited managed files stop the operation.
- Symlink/junction/reparse paths, overlapping target roots, oversized backups and unexpected filesystem entries are rejected.
- Completed steps are journaled and checked against known target bytes/state after each step. Ordinary errors or cancellation roll back only when the current tree still matches the last verified step. Unexpected partial mutations or concurrent edits yield `BLOCKED_ROLLBACK_REQUIRED` and preserve the local backup for manual inspection. Unrelated files and pre-existing empty managed directories are preserved.
- A private local journal lives at `CODEX_HOME/.aka-chef-gui/<transaction-id>/journal.json`. It contains the original configuration, encoded for exact restoration; this encoding is **not encryption**. POSIX files use owner-only permissions; Windows follows the user profile's inherited ACL. **Never attach this journal to GitHub or upload it.**
- The GUI progress log contains constant event names, result statuses and exception class names. It does not contain the rules diff, prompts, credentials or exception text.
- Do not edit configuration from another installer while this one runs. This transaction does not provide a cross-process lock or protection against hostile same-user races. Subsequent edits are checked before rollback.
- A forced process kill, power loss or abrupt filesystem failure can leave an incomplete transaction. Do not blindly restore a journal or delete configuration: inspect local backups and current files before recovery. Crash-proof recovery is not yet verified.
- Incomplete or untrusted source: obtain a complete verified candidate through the documented release process. Network/proxy failures occur outside this offline GUI; it never silently falls back to an unverified archive.
- No standalone packaging, Authenticode signature, dependency installation, uninstaller EXE or claim of first-time friend acceptance is provided by this candidate.

## Cloud verification vs real Windows UAT

```sh
python -m unittest discover -s tests -p 'test_install_transaction.py' -v
python -m unittest discover -s tests -p 'test_gui_installer.py' -v
python -m tools.gui_installer --smoke-test
```

The smoke option opens real Tk widgets, checks safe defaults and closes without changing user configuration. It needs a graphical display and is not an interactive user journey test. Filesystem tests use isolated temporary directories and cover explicit consent, real install/verify/undo, exact original bytes, stale preview, edited configs, cancellation, injected step failure, concurrent edits during/after failed and successful steps, idempotent reinstall, symlinks, overlapping roots and empty directory preservation. Synthetic injected failures are not reports of observed production failures.

Remaining Windows 11 standard-user checklist: first run with missing Python/Codex, deny permissions, corrupted source, proxy interruption during acquisition, reinstall, cancellation, rollback, configuration edits and independent nontechnical user approval. Each requires environment/version, duration, observed result and sanitized evidence; unsupported or unavailable cases stay `BLOCKED`.
