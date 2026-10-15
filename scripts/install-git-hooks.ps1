#requires -Version 7.0
<#
.SYNOPSIS
    Windows counterpart of scripts/install-git-hooks.sh.

.DESCRIPTION
    Installs an optional pre-commit hook that runs the local pre-flight, so a
    broken import or lint is caught before the commit (and before a CI
    round-trip). Bypass a single commit with: git commit --no-verify

    The hook itself is a POSIX sh script: git for Windows executes hooks
    through its bundled shell regardless of the shell you installed from, which
    keeps the hook working from both PowerShell and Git Bash. It prefers
    preflight.ps1 when pwsh is on PATH and falls back to preflight.sh, so the
    same checkout behaves correctly on Linux and macOS too.

    Re-run this after pulling, and re-run it from the repository root. To
    remove the hook use -Remove.

.EXAMPLE
    ./scripts/install-git-hooks.ps1
    ./scripts/install-git-hooks.ps1 -Remove
#>
[CmdletBinding()]
param(
    [string]$HookName = 'pre-commit',
    # Delete the hook instead of installing it.
    [switch]$Remove
)

. (Join-Path $PSScriptRoot '_devlib.ps1')

$root = Get-RepoRoot
Set-Location $root

# git ignores .git/hooks entirely once core.hooksPath is set, so a hook written
# there would never run while this script still reported success.
$hooksPath = (& git config --get core.hooksPath)
if ($LASTEXITCODE -ne 0 -or -not $hooksPath) { $hooksPath = '.git/hooks' }

if (-not [System.IO.Path]::IsPathRooted($hooksPath)) {
    $hooksPath = Join-Path $root $hooksPath
}
$hook = Join-Path $hooksPath $HookName

if ($Remove) {
    if (Test-Path -LiteralPath $hook) {
        Remove-Item -LiteralPath $hook -Force
        Write-Step "install-git-hooks: removed $hook"
    }
    else {
        Write-Note "install-git-hooks: nothing to remove at $hook"
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $hooksPath -PathType Container)) {
    Write-Fail "hooks directory not found: $hooksPath (not a git repo?)"
    exit 2
}

$hookBody = @'
#!/usr/bin/env sh
# Installed by scripts/install-git-hooks.ps1 -- runs the local pre-flight.
# Skip with: git commit --no-verify
#
# The guards below matter on older revisions: this hook is a local, untracked
# artifact, so it survives a checkout of a commit that predates the pre-flight
# scripts. Without them the hook fails with a bare "not found" and blocks the
# commit with nothing to act on.
ROOT="$(git rev-parse --show-toplevel)"

if [ -f "$ROOT/scripts/preflight.ps1" ] && command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoProfile -ExecutionPolicy Bypass -File "$ROOT/scripts/preflight.ps1"
fi

if [ -x "$ROOT/scripts/preflight.sh" ]; then
  exec "$ROOT/scripts/preflight.sh"
fi

exit 0
'@

# sh needs LF endings regardless of how this file was checked out.
$hookBody = $hookBody -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($hook, $hookBody, [System.Text.UTF8Encoding]::new($false))

Write-Step "install-git-hooks: installed $hook"
if ($hooksPath -ne (Join-Path $root '.git/hooks')) {
    Write-Note "core.hooksPath is '$hooksPath'"
}
Write-Note 'hook runs scripts/preflight.ps1 (or preflight.sh when pwsh is absent)'
Write-Note 're-run this script after pulling; remove with -Remove'
exit 0
