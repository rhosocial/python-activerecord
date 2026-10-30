#requires -Version 7.0
<#
.SYNOPSIS
    Local mirror of .github/workflows/changelog-check.yml.

.DESCRIPTION
    Runs the same fragment rules CI enforces, so a misnumbered or missing
    changelog.d fragment is caught before pushing instead of after a CI
    round-trip.

      feature/* fix/* bugfix/* test/* docs/* chore/*  ->  release/* | maint/*
        - must not target main directly
        - the change must add at least one changelog.d/<number>.<type>.md
        - every added fragment's <number> must equal the PR number

      release/*  ->  main
        - CHANGELOG.md must have changed
        - changelog.d/ must contain no fragments at the merge commit

    Escape hatches (presence requirement only -- the number-must-match rule is
    always enforced): [trivial] in the PR title, the skip-changelog label, or a
    "docs: update CHANGELOG" title.

    PR number, title and base ref are auto-detected through `gh` when the branch
    already has an open PR; pass them explicitly to check a branch that has none
    yet.

.EXAMPLE
    ./scripts/changelog-check.ps1
    ./scripts/changelog-check.ps1 -PrNumber 124 -BaseRef release/v1.0.0.dev30
    ./scripts/changelog-check.ps1 -PrNumber 124 -PrTitle 'feat(query): add lateral join [trivial]'

.NOTES
    Exit codes: 0 ok, 1 a rule was violated, 2 the base ref could not be resolved.
#>
[CmdletBinding()]
param(
    # PR number the fragment numbers must match. 0 disables the check.
    [int]$PrNumber = 0,
    # Base branch of the PR, with or without the origin/ prefix.
    [string]$BaseRef = '',
    # Head branch; defaults to the current branch.
    [string]$HeadRef = '',
    # PR title, used only for the escape hatches.
    [string]$PrTitle = '',
    # Stand in for the skip-changelog label.
    [switch]$SkipChangelog,
    # Skip `git fetch origin <base>` before diffing.
    [switch]$NoFetch,
    # Skip the `gh pr view` lookup entirely.
    [switch]$NoRemoteLookup
)

. (Join-Path $PSScriptRoot '_devlib.ps1')

Set-Location (Get-RepoRoot)

$failed = $false
$knownTypes = Get-TowncrierTypes
$branchKinds = @('feature/*', 'fix/*', 'bugfix/*', 'test/*', 'docs/*', 'chore/*')

function Get-GitLines {
    param([string[]]$Arguments)
    $out = & git @Arguments
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($out | Where-Object { $_ })
}

# ---------------------------------------------------------------------------
# Resolve head / base / PR metadata
# ---------------------------------------------------------------------------
if (-not $HeadRef) {
    $HeadRef = (& git rev-parse --abbrev-ref HEAD)
    if ($LASTEXITCODE -ne 0 -or -not $HeadRef -or $HeadRef -eq 'HEAD') {
        Write-Fail 'cannot determine the current branch (detached HEAD?). Pass -HeadRef.'
        exit 2
    }
}

if (-not $NoRemoteLookup) {
    $gh = Resolve-RepoTool -Name 'gh'
    if ($gh) {
        try {
            $json = & $gh pr view --json number,title,baseRefName 2>$null
            if ($LASTEXITCODE -eq 0 -and $json) {
                $pr = $json | ConvertFrom-Json
                if (-not $PrNumber -and $pr.number) { $PrNumber = [int]$pr.number }
                if (-not $PrTitle) { $PrTitle = [string]$pr.title }
                if (-not $BaseRef) { $BaseRef = [string]$pr.baseRefName }
            }
        }
        catch {
            Write-Note 'gh pr view failed; continuing with the values passed in'
        }
    }
    else {
        Write-Note 'gh not installed -- pass -PrNumber/-BaseRef explicitly for a full check'
    }
}

if (-not $BaseRef) {
    # No PR yet: a release branch is destined for main, everything else for the
    # active release branch (see .claude/version_control.md).
    if ($HeadRef -like 'release/*') { $BaseRef = 'main' }
    else {
        Write-Fail 'cannot infer the base branch. Pass -BaseRef release/vX.Y.Z (or maint/X).'
        exit 2
    }
}

$remoteRef = if ($BaseRef -like 'origin/*') { $BaseRef } else { "origin/$BaseRef" }

Write-Step "changelog-check: $HeadRef -> $remoteRef"
if ($PrNumber) {
    $suffix = if ($PrTitle) { " ($PrTitle)" } else { '' }
    Write-Note "PR #$PrNumber$suffix"
}
else { Write-Note 'PR number unknown -- fragment numbering not verified' }

# ---------------------------------------------------------------------------
# Resolve the comparison base
# ---------------------------------------------------------------------------
if (-not $NoFetch) {
    $fetchTarget = $remoteRef -replace '^origin/', ''
    & git fetch origin $fetchTarget --quiet 2>&1 | Out-Null
}

& git rev-parse --verify --quiet $remoteRef | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "base ref '$remoteRef' not found locally -- run: git fetch origin"
    exit 2
}

$diffArgs = @('diff', '--name-only', "$remoteRef...HEAD")

function Test-BaseIsMain {
    return ($remoteRef -eq 'origin/main' -or $remoteRef -eq 'refs/remotes/origin/main')
}

# ---------------------------------------------------------------------------
# Branch policy: feature-ish branches must not target main
# ---------------------------------------------------------------------------
$isBranchKind = $false
foreach ($kind in $branchKinds) {
    if ($HeadRef -like $kind) { $isBranchKind = $true; break }
}

if ($isBranchKind -and (Test-BaseIsMain)) {
    Write-Fail "'$HeadRef' must not target main directly."
    Write-Note 'Per the rhosocial merge rules:'
    Write-Item 'feature/* fix/* bugfix/* test/* docs/* chore/*  ->  release/* | maint/*'
    Write-Item 'release/*                                            ->  main'
    Write-Note 'Active release branches:'
    foreach ($line in (Get-GitLines @('branch', '-r', '--list', 'origin/release/*'))) {
        Write-Item ($line -replace '^\s*origin/', '')
    }
    exit 1
}

# ---------------------------------------------------------------------------
# release/* -> main : CHANGELOG.md must change, changelog.d/ must be clear
# ---------------------------------------------------------------------------
if ($HeadRef -like 'release/*' -and (Test-BaseIsMain)) {
    Write-Step 'release merge into main'

    $changed = Get-GitLines @('diff', '--name-only', "$remoteRef...HEAD", '--', 'CHANGELOG.md')
    if ($changed) {
        Write-Pass 'CHANGELOG.md updated'
    }
    else {
        Write-Fail 'CHANGELOG.md was not updated by this release merge.'
        Write-Note 'Regenerate it with: towncrier build --yes --keep'
        $failed = $true
    }

    # Checked against the merge result, not the diff: leftover fragments from
    # earlier in the release cycle must be gone by this point.
    $leftovers = Get-GitLines @('ls-tree', '--name-only', 'HEAD', 'changelog.d/') |
        Where-Object { $_ -match '^[0-9]+\.[A-Za-z]+\.md$' }
    if ($leftovers) {
        Write-Fail 'changelog.d/ still contains fragments after the release merge:'
        foreach ($item in $leftovers) { Write-Item $item }
        Write-Note 'Delete them; their content is already folded into CHANGELOG.md.'
        $failed = $true
    }
    else {
        Write-Pass 'changelog.d/ is clear of fragments'
    }

    if ($failed) { exit 1 }
    exit 0
}

# ---------------------------------------------------------------------------
# Fragments added by this branch
# ---------------------------------------------------------------------------
Write-Step 'fragment numbering'

# Three sources, because this runs before the commit exists: `git diff` alone
# only sees what is already committed, so a freshly created (untracked or
# staged) fragment -- exactly the case worth catching -- would be invisible.
# Fragments already present in changelog.d/ (carried in by previously merged
# branches) are excluded by --diff-filter=A, so only this branch's additions are
# judged, matching what CI will see once the work is pushed.
$added = @()
$added += Get-GitLines @('diff', '--name-only', '--diff-filter=A', "$remoteRef...HEAD", '--', 'changelog.d')
$added += Get-GitLines @('diff', '--name-only', '--diff-filter=A', '--cached', '--', 'changelog.d')
$added += Get-GitLines @('ls-files', '--others', '--exclude-standard', '--', 'changelog.d')
$added = @($added |
        Sort-Object -Unique |
        Where-Object { ($_ -split '/')[-1] -notin @('README.md', 'template.md', '.gitkeep') })

if ($added) {
    foreach ($path in $added) {
        $base = ($path -split '/')[-1]
        if ($base -notmatch '^(\d+)\.([A-Za-z]+)\.md$') {
            Write-Fail "$path : fragment must be named <number>.<type>.md, got '$base'"
            Write-Note 'Multiple issues in one file (123+456.fixed.md, see changelog.d/README.md)'
            Write-Note 'are rejected by the CI check -- use one fragment per issue.'
            $failed = $true
            continue
        }

        $num = $Matches[1]
        $type = $Matches[2]

        if ($PrNumber -and $num -ne "$PrNumber") {
            Write-Fail "$path : fragment number '$num' does not match PR #$PrNumber"
            Write-Note "Rename it to changelog.d/$PrNumber.$type.md, or open a PR for #$num."
            $failed = $true
            continue
        }

        if ($type -notin $knownTypes) {
            Write-Note "$path : '$type' is not a configured towncrier type (warning only)"
            Write-Note "types: $($knownTypes -join ', ')"
        }
    }

    if ($failed) {
        Write-Host ''
        Write-Fail "Fragment numbering does not match PR #$PrNumber"
        exit 1
    }

    $summary = ($added | ForEach-Object { ($_ -split '/')[-1] }) -join ', '
    $subject = if ($PrNumber) { "PR #$PrNumber" } else { 'this branch' }
    Write-Pass "fragment(s) added for $subject -> $summary"
    exit 0
}

# ---------------------------------------------------------------------------
# No fragment added: apply the escape hatches, then the internal-only waiver
# ---------------------------------------------------------------------------
if ($PrTitle -like '*[[]trivial[]]*' -or $SkipChangelog -or $PrTitle -like 'docs: update CHANGELOG*') {
    Write-Pass 'no fragment required (exempt)'
    exit 0
}

# Working-tree state counts too, for the same reason as the fragment list above.
$changedFiles = @()
$changedFiles += Get-GitLines $diffArgs
$changedFiles += Get-GitLines @('diff', '--name-only', '--cached')
$changedFiles += Get-GitLines @('diff', '--name-only')
$changedFiles = @($changedFiles | Sort-Object -Unique)
$internalOnly = ($changedFiles | Where-Object { $_ -match '^(tests/|docs/|\.github/)' }) -and
                -not ($changedFiles | Where-Object { $_ -match '^src/' })
if ($internalOnly) {
    Write-Pass 'internal-only change, no fragment required'
    exit 0
}

Write-Fail 'No changelog fragment added by this branch.'
if ($PrNumber) {
    Write-Note "Add at least one changelog.d/$PrNumber.<type>.md"
}
else {
    Write-Note 'Add at least one changelog.d/<pr-number>.<type>.md'
}
Write-Note "Types: $($knownTypes -join ' | ')"
Write-Note 'Or waive it: add [trivial] to the PR title, apply the skip-changelog'
Write-Note "label, or title the PR 'docs: update CHANGELOG'."
Write-Note 'Create one with: ./scripts/dev.ps1 fragment <pr-number> <type> "<text>"'
exit 1
