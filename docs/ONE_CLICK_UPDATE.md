# Universal one-click update (candidate, PR #49)

This updater is for an **existing reviewed Git checkout**, not an unverified remote bootstrap. Git and Python 3.11+ are required. No sudo or automatic dependency installation. Verify releases and source provenance separately.

## Windows 10/11 (PowerShell 7)

```powershell
pwsh -File ./update.ps1
```

## macOS (Apple Silicon / Intel), Ubuntu, Debian, Linux

```sh
sh ./update.sh
```

Both entry points refuse unexpected Git origin, non-main branches, dirty working trees, and divergent Git history. They fetch main and show a diff summary; typing `UPDATE` permits a fast-forward. The existing interactive installer then previews managed rules, Skills and role changes, requiring separate approval.

`sh ./update.sh --source-only` updates repository source but not installed Skills. For a preview without installation, use `python3 -m tools.update`.

**Scope:** These commands do not auto-push private workspace data, edit secrets, activate agents, or prove real multi-agent runtime behavior. The GUI button and signed-release update channel are not yet implemented. Installation is per the existing setup's default host (Codex); a different host requires its own explicit setup options.

**Validation pending:** macOS, Ubuntu and Windows real-host smoke tests, CI and review. Do not publish this as a verified release until those checks pass.
