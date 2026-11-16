# AKA.CRISTI Skills - safe one-command source updater (Windows PowerShell 7+)
# Run from a reviewed Git checkout: pwsh -File ./update.ps1
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$SkipSetup
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Step([string]$Message) { Write-Host "[CHEF UPDATE] $Message" -ForegroundColor Cyan }
function Git([string[]]$Args) {
    & git @Args
    if ($LASTEXITCODE -ne 0) { throw "git $($Args -join ' ') failed (exit $LASTEXITCODE)" }
}
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required.' }
    $root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
    Set-Location -LiteralPath $root
    if (-not (Test-Path -LiteralPath '.git')) { throw 'Run inside a reviewed aka-cristi-skills Git checkout.' }
    $remote = (& git remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0 -or $remote -notmatch '^(https://github\.com/|git@github\.com:)2ndforcecrew/aka-cristi-skills(\.git)?$') {
        throw 'Unexpected origin. Refusing to fetch.'
    }
    $branch = (& git branch --show-current).Trim()
    if ($branch -ne 'main') { throw "Current branch is '$branch'; switch to main manually before updating." }
    $changes = @(& git status --porcelain --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect working tree.' }
    if ($changes.Count -gt 0 -and ($changes | Where-Object { $_.Trim() })) {
        throw 'Working tree has local changes/untracked files. Commit or back them up first; nothing was changed.'
    }
    Step 'Fetching main metadata (no local changes yet)...'
    Git @('fetch','--no-tags','origin','main')
    $localSha = (& git rev-parse HEAD).Trim()
    $remoteSha = (& git rev-parse refs/remotes/origin/main).Trim()
    Git @('merge-base','--is-ancestor',$localSha,$remoteSha)
    if ($localSha -eq $remoteSha) {
        Step "Source already current: $localSha"
    } else {
        Step "Local:  $localSha"
        Step "Remote: $remoteSha"
        Git @('diff','--stat','HEAD','refs/remotes/origin/main')
        Step 'Review changes above and repository release/security status before applying.'
        if (-not $Apply) {
            $answer = Read-Host 'Type UPDATE to fast-forward local source and open the installer preview'
            if ($answer -cne 'UPDATE') { Step 'Cancelled; no local files updated.'; exit 0 }
        }
        Git @('merge','--ff-only','refs/remotes/origin/main')
        Step "Source fast-forwarded to $remoteSha"
    }
    if ($SkipSetup) { Step 'Source update only. Installed Skills unchanged.'; exit 0 }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { $exe = $py.Source; $prefix = @('-3') }
    else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) { throw 'Python 3.11+ missing; source updated, installed Skills unchanged.' }
        $exe = $python.Source; $prefix = @()
    }
    Step 'Starting existing interactive setup. Preview/conflict checks and user approval are required.'
    & $exe @prefix -m tools.full_setup --interactive
    if ($LASTEXITCODE -ne 0) { throw "Setup failed (exit $LASTEXITCODE). Check backups and logs; no automatic rollback of Git source was attempted." }
    Step 'Setup finished. File verification is not proof of live Agent activation.'
} catch {
    Write-Host "[CHEF UPDATE][BLOCKED] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
