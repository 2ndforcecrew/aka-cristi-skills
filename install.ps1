# AKA.CRISTI Skills - Windows friend-friendly, non-destructive bootstrap.
# Explicit -Apply authorizes installing user-scoped CHEF rules and Skills.
# -InstallDependencies additionally authorizes official prerequisite installers.
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$InstallDependencies,
    [switch]$SkipCodexCheck,
    [string]$SourceDirectory = "",
    [string]$CodexHome = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Repo = "2ndforcecrew/aka-cristi-skills"
$RequiredFiles = @(
    "README.md", "tools/__init__.py", "tools/chef_global_rules.py",
    "tools/codex_subagents.py", "tools/skill_installer.py",
    "templates/AGENTS.global.md", "agents/research.toml",
    "agents/coding.toml", "agents/qa.toml", "agents/automation.toml",
    "skills/chef-orchestrator/SKILL.md",
    "skills/verified-change-loop/SKILL.md",
    "skills/feature-journey-map/SKILL.md",
    "skills/skill-evaluation-gate/SKILL.md"
)
function Show-Step([string]$Message) { Write-Host ("[CHEF] " + $Message) -ForegroundColor Cyan }
function Assert-FileTree([string]$Root) {
    foreach ($entry in $RequiredFiles) {
        $path = Join-Path $Root ($entry -replace '/', '\')
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
            $versionText = (& $candidate.Exe @($candidate.Prefix) --version 2>&1 | Out-String).Trim()
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
function Obtain-Source {
    if ($SourceDirectory) {
        $root = (Resolve-Path -LiteralPath $SourceDirectory).Path
        Assert-FileTree $root
        Show-Step "Validated supplied local source: $root"
        return $root
    }
    # Always obtain a fresh, complete, commit-pinned GitHub archive.
    # A damaged or incomplete existing checkout is never overwritten.
    $api = "https://api.github.com/repos/$Repo/commits/main"
    Show-Step "Discovering current public release..."
    $metadata = Invoke-RestMethod -Uri $api -Headers @{ 'User-Agent' = 'aka-cristi-safe-bootstrap'; 'Accept' = 'application/vnd.github+json' } -TimeoutSec 45
    $sha = [string]$metadata.sha
    if ($sha -notmatch '^[a-f0-9]{40}$') { throw "GitHub returned an invalid commit SHA" }
    $rootCache = Join-Path $env:LOCALAPPDATA 'AKA.CRISTI\installer'
    New-Item -ItemType Directory -Force -Path $rootCache | Out-Null
    $work = Join-Path $rootCache ("download-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $work | Out-Null
    $zip = Join-Path $work 'source.zip'
    $extract = Join-Path $work 'extracted'
    $uri = "https://github.com/$Repo/archive/$sha.zip"
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Show-Step "Fetching full source archive from GitHub (attempt $attempt/2)..."
        try {
            Invoke-WebRequest -Uri $uri -OutFile $zip -UseBasicParsing -TimeoutSec 120
            if (Test-Path -LiteralPath $extract) {
                # This path belongs to this run; preserve any other user files.
                Remove-Item -LiteralPath $extract -Recurse -Force
            }
            Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
            $folders = @(Get-ChildItem -LiteralPath $extract -Directory)
            if ($folders.Count -ne 1) { throw "Unexpected GitHub archive structure" }
            $root = $folders[0].FullName
            Assert-FileTree $root
            Show-Step "Verified all $($RequiredFiles.Count) required project files."
            return $root
        } catch {
            if ($attempt -eq 2) { throw "Source repair failed after two attempts: $($_.Exception.Message)" }
            Show-Step "Incomplete source detected; downloading the archive again."
        }
    }
    throw "Could not obtain verified source"
}
function Invoke-Python([hashtable]$Python, [string[]]$Arguments) {
    & $Python.Exe @($Python.Prefix) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python setup step failed: $($Arguments -join ' ') (exit $LASTEXITCODE)"
    }
}
function Assert-SafePlan([hashtable]$Python, [string[]]$Arguments, [string[]]$Disallowed) {
    $result = & $Python.Exe @($Python.Prefix) @Arguments 2>&1 | Out-String
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
    $python = Get-PythonExecutable
    if (-not $python) {
        if (-not $Apply) {
            Show-Step "Python 3.11+ not found. Re-run with -Apply -InstallDependencies to authorize installation."
            exit 2
        }
        Invoke-OfficialDependency "Python 3.13" "Python.Python.3.13"
        $python = Get-PythonExecutable
        if (-not $python) { throw "Python installed but not on PATH yet; open a fresh PowerShell and rerun." }
    }
    if (-not $SkipCodexCheck -and -not (Get-Command codex -ErrorAction SilentlyContinue)) {
        if (-not $Apply -or -not $InstallDependencies) {
            Show-Step "Codex CLI not found. You can install it using the official instructions at https://github.com/openai/codex"
            if ($Apply) { throw "Codex CLI required. Install it, then rerun." }
        } else {
            # The official install script is downloaded for inspection/execution rather
            # than piping an unreviewed remote script directly to iex.
            $installer = Join-Path $env:TEMP ("codex-official-" + [guid]::NewGuid().ToString("N") + ".ps1")
            Show-Step "Downloading official Codex CLI installer from chatgpt.com..."
            Invoke-WebRequest -Uri 'https://chatgpt.com/codex/install.ps1' -OutFile $installer -UseBasicParsing -TimeoutSec 60
            Show-Step "Running official Codex CLI installer (authorized by -InstallDependencies)."
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
            if ($LASTEXITCODE -ne 0) { throw "Official Codex CLI installer did not succeed" }
            Show-Step "If codex is not recognized yet, open a new terminal after installation."
        }
    }
    $source = Obtain-Source
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
        foreach ($name in $skills) {
            # Codex skills target uses the current user's own standard directory.
            Assert-SafePlan $python @('-m','tools.skill_installer','preview',"skills/$name",'--target','codex') @('conflict_unmanaged','conflict_modified','conflict_missing')
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
            Invoke-Python $python @('-m','tools.skill_installer','install',"skills/$name",'--target','codex','--apply')
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
            Invoke-Python $python @('-m','tools.skill_installer','verify',$name,'--target','codex')
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
