# AKA.CRISTI Skills - Windows friend-friendly, non-destructive bootstrap.
# Explicit -Apply authorizes installing user-scoped CHEF rules and Skills.
# -InstallDependencies additionally authorizes official prerequisite installers.
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$InstallDependencies,
    [switch]$SkipCodexCheck,
    [string]$SourceDirectory = "",
    [string]$CodexHome = "",
    [string]$SkillsRoot = "",
    [string]$ArchivePath = "",
    [string]$ExpectedCommit = "",
    [string]$ExpectedSha256 = "",
    [string]$ExpectedSourceRef = "refs/heads/main",
    [string]$ProvenanceBundle = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Repo = "2ndforcecrew/aka-cristi-skills"
$RequiredFiles = @(
    "README.md", "tools/__init__.py", "tools/chef_global_rules.py",
    "tools/codex_subagents.py", "tools/skill_installer.py", "tools/fs_safety.py",
    "templates/AGENTS.global.md", "agents/research.toml",
    "agents/coding.toml", "agents/qa.toml", "agents/automation.toml",
    "skills/chef-orchestrator/SKILL.md",
    "skills/verified-change-loop/SKILL.md",
    "skills/feature-journey-map/SKILL.md",
    "skills/skill-evaluation-gate/SKILL.md"
)
function Show-Step([string]$Message) { Write-Host ("[CHEF] " + $Message) -ForegroundColor Cyan }
function Assert-NoReparseAncestors([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Refusing symlink/reparse-point path or ancestor.'
            }
        }
        $parent = [IO.Path]::GetDirectoryName($current)
        if ($parent -eq $current) { break }
        $current = $parent
    }
}
function Assert-FileTree([string]$Root) {
    Assert-NoReparseAncestors $Root
    foreach ($entry in $RequiredFiles) {
        $path = Join-Path $Root ($entry -replace '/', '\')
        Assert-NoReparseAncestors $path
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Missing required file: $entry"
        }
        if ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing symlink/reparse point: $entry"
        }
    }
}
function Get-PythonExecutable {
    $candidates = @()
    foreach ($name in @('py','python')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            if ($name -eq 'py') {
                $candidates += @{Exe=$command.Source; Prefix=@('-3')}
            } else {
                $candidates += @{Exe=$command.Source; Prefix=@()}
            }
        }
    }
    $localPython = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path -LiteralPath $localPython) {
        Get-ChildItem -LiteralPath $localPython -Filter 'Python3*' -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                $exe = Join-Path $_.FullName 'python.exe'
                if (Test-Path -LiteralPath $exe) { $candidates += @{Exe=$exe; Prefix=@()} }
            }
    }
    foreach ($candidate in $candidates) {
        try {
            $versionArgs = @($candidate.Prefix) + @("--version")
            $versionText = (& $candidate.Exe @versionArgs 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and $versionText -match 'Python (\d+)\.(\d+)') {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                    return $candidate
                }
            }
        } catch {}
    }
    return $null
}
function Invoke-OfficialDependency([string]$Label, [string]$PackageId) {
    if (-not $InstallDependencies) {
        throw "$Label is missing. Rerun with -InstallDependencies to authorize an official installation."
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "$Label is missing and winget is unavailable. Install it from the official provider and rerun."
    }
    Show-Step "Installing $Label via winget ($PackageId). Windows may request permission."
    & winget install --id $PackageId --exact --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "$Label installation failed (winget exit $LASTEXITCODE)." }
}
function Obtain-Source([hashtable]$Python) {
    if ($SourceDirectory) {
        $root = (Resolve-Path -LiteralPath $SourceDirectory).Path
        Assert-FileTree $root
        Show-Step "Reviewed local source selected by user (not a signed release): $root"
        return $root
    }
    # Verification code must be the reviewed copy alongside this script, never
    # Python imported from the downloaded ZIP. No archive code executes first.
    $verifier = Join-Path $PSScriptRoot 'tools\verify_release.py'
    if (-not (Test-Path -LiteralPath $verifier -PathType Leaf)) {
        throw 'Trusted local tools/verify_release.py is required beside install.ps1. Use a reviewed checkout.'
    }
    Assert-NoReparseAncestors $verifier
    Assert-NoReparseAncestors (Join-Path $PSScriptRoot 'tools\__init__.py')
    Assert-NoReparseAncestors (Join-Path $PSScriptRoot 'tools\fs_safety.py')
    if (-not $ArchivePath -or $ExpectedCommit -notmatch '^[a-f0-9]{40}$' -or $ExpectedSha256 -notmatch '^[a-f0-9]{64}$') {
        throw 'Verified archive requires -ArchivePath, -ExpectedCommit and -ExpectedSha256 from a trusted review.'
    }
    $archive = (Resolve-Path -LiteralPath $ArchivePath).Path
    Assert-NoReparseAncestors $archive
    $work = Join-Path ([IO.Path]::GetTempPath()) ("aka-chef-verified-" + [guid]::NewGuid().ToString("N"))
    Assert-NoReparseAncestors ([IO.Path]::GetTempPath())
    $isolatedLauncher = "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('tools.verify_release',run_name='__main__')"
    $verifyArgs = @('-I', '-c', $isolatedLauncher, $PSScriptRoot, $archive, '--expected-commit', $ExpectedCommit,
        '--expected-sha256', $ExpectedSha256, '--source-ref', $ExpectedSourceRef, '--extract-to', $work)
    if ($ProvenanceBundle) { $verifyArgs += @('--bundle', $ProvenanceBundle) }
    Invoke-Python $Python $verifyArgs | ForEach-Object { Write-Host $_ }
    Assert-FileTree $work
    Show-Step 'Archive integrity and pinned GitHub publisher provenance verified before extraction.'
    return $work
}
function Invoke-Python([hashtable]$Python, [string[]]$Arguments) {
    $callArgs = @($Python.Prefix) + @($Arguments)
    & $Python.Exe @callArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Python setup step failed: $($Arguments -join ' ') (exit $LASTEXITCODE)"
    }
}
function Assert-SafePlan([hashtable]$Python, [string[]]$Arguments, [string[]]$Disallowed) {
    $callArgs = @($Python.Prefix) + @($Arguments)
    $result = & $Python.Exe @callArgs 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Preview failed ($($Arguments -join ' ')): $result" }
    Write-Host $result.Trim()
    $parsed = $result | ConvertFrom-Json
    foreach ($item in @($parsed)) {
        $state = if ($item.PSObject.Properties['action']) { [string]$item.action } elseif ($item.PSObject.Properties['state']) { [string]$item.state } else { '' }
        if ($Disallowed -contains $state -or $state -match '^CONFLICT') {
            throw "Existing custom configuration conflict detected. No changes applied ($state)."
        }
    }
}
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'This bootstrap is Windows-only.' }
    Show-Step "Mode: $(if ($Apply) { 'INSTALL (current user)' } else { 'PREVIEW ONLY' })"
    if ($SourceDirectory -and $ArchivePath) { throw 'Choose reviewed local source OR a verified archive.' }
    if (-not $SourceDirectory -and -not $ArchivePath) {
        throw 'Remote source bootstrap is BLOCKED until a signed candidate is available. Use -SourceDirectory for reviewed local source, or -ArchivePath with pinned digest/provenance. No download or dependency installer was run.'
    }
    if ($SourceDirectory) { Assert-FileTree (Resolve-Path -LiteralPath $SourceDirectory).Path }
    $python = Get-PythonExecutable
    if (-not $python) {
        if (-not $Apply) {
            Show-Step "Python 3.11+ not found. Re-run with -Apply -InstallDependencies to authorize installation."
            exit 2
        }
        if ($ArchivePath) { throw 'Python 3.11+ must be installed separately before archive provenance verification. No dependency installer was run.' }
        Invoke-OfficialDependency "Python 3.13" "Python.Python.3.13"
        $python = Get-PythonExecutable
        if (-not $python) { throw "Python installed but not on PATH yet; open a fresh PowerShell and rerun." }
    }
    if (-not $SkipCodexCheck -and -not (Get-Command codex -ErrorAction SilentlyContinue)) {
        if (-not $Apply -or -not $InstallDependencies) {
            Show-Step "Codex CLI not found. You can install it using the official instructions at https://github.com/openai/codex"
            if ($Apply) { throw "Codex CLI required. Install it, then rerun." }
        } else {
            throw 'Codex CLI missing. Automatic download/execution is BLOCKED until verified prerequisite provenance is implemented. Install Codex separately using reviewed official instructions, then retry.'
        }
    }
    $source = Obtain-Source $python
    Show-Step "Performing conflict checks before touching user configuration..."
    Push-Location $source
    try {
        $global = @('-m','tools.chef_global_rules','preview')
        $agents = @('-m','tools.codex_subagents','preview')
        if ($CodexHome) {
            $global += @('--codex-home',$CodexHome)
            $agents += @('--codex-home',$CodexHome)
        }
        Assert-SafePlan $python $global @('conflict_modified','FAIL')
        Assert-SafePlan $python $agents @('CONFLICT_UNMANAGED','CONFLICT_MODIFIED','CONFLICT_MISSING')
        $skills = @('chef-orchestrator','verified-change-loop','feature-journey-map','skill-evaluation-gate')
        $skillTarget = @('--target','codex')
        if ($SkillsRoot) { $skillTarget = @('--target','directory','--root',$SkillsRoot) }
        foreach ($name in $skills) {
            # Codex skills target uses the current user's own standard directory.
            Assert-SafePlan $python (@('-m','tools.skill_installer','preview',"skills/$name") + $skillTarget) @('conflict_unmanaged','conflict_modified','conflict_missing')
        }
        if (-not $Apply) {
            Show-Step "Preview complete. Run with -Apply to install. Nothing changed."
            exit 0
        }
        Show-Step "Applying global rules, 4 Skill packages and 4 Codex agent profiles..."
        $applyGlobal = @('-m','tools.chef_global_rules','install','--apply')
        $applyAgents = @('-m','tools.codex_subagents','install','--apply')
        if ($CodexHome) {
            $applyGlobal += @('--codex-home',$CodexHome)
            $applyAgents += @('--codex-home',$CodexHome)
        }
        Invoke-Python $python $applyGlobal
        foreach ($name in $skills) {
            Invoke-Python $python (@('-m','tools.skill_installer','install',"skills/$name",'--apply') + $skillTarget)
        }
        Invoke-Python $python $applyAgents
        Show-Step "Verifying installed files..."
        $verifyGlobal = @('-m','tools.chef_global_rules','verify')
        $verifyAgents = @('-m','tools.codex_subagents','verify')
        if ($CodexHome) {
            $verifyGlobal += @('--codex-home',$CodexHome)
            $verifyAgents += @('--codex-home',$CodexHome)
        }
        Invoke-Python $python $verifyGlobal
        foreach ($name in $skills) {
            Invoke-Python $python (@('-m','tools.skill_installer','verify',$name) + $skillTarget)
        }
        Invoke-Python $python $verifyAgents
        Show-Step "FILE INSTALLATION COMPLETE. Agent runtime activation: NOT_RUN."
        Show-Step "Next: sign in to Codex and test actual agent delegation separately."
    } finally {
        Pop-Location
    }
} catch {
    Write-Host ("[CHEF][BLOCKED] " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
