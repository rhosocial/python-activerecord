#requires -Version 7.0
<#
.SYNOPSIS
    Single entry point for local development on Windows / PowerShell 7.

.DESCRIPTION
    Wraps the commands the project actually needs -- the ones currently spread
    across .claude/commands/*.md, .claude/testing.md and .github/workflows/*.yml
    -- so they can be run from PowerShell without re-typing PYTHONPATH or
    remembering flags.

    Every subcommand resolves the repository virtualenv, puts <root>/src and
    <root>/tests on PYTHONPATH, and streams native output verbatim (test output
    is never filtered or truncated -- see AGENTS.md, "Test Execution").

    Tests run SERIALLY by default; -Parallel opts into the CI configuration
    instead: -n auto --dist=loadgroup with the testsuite plugin loaded, which is
    the only parallel mode the suite supports (.claude/testing.md section 5).
    Parallel is a supported and encouraged mode -- iron rule 1 asks for the
    plugin and the serial marker, it does not require a serial run.

.EXAMPLE
    ./scripts/dev.ps1 doctor
    ./scripts/dev.ps1 test
    ./scripts/dev.ps1 test tests/rhosocial/activerecord_test/feature/query -k cte
    ./scripts/dev.ps1 test -Parallel
    ./scripts/dev.ps1 cov -Parallel
    ./scripts/dev.ps1 lint src tests
    ./scripts/dev.ps1 verify
    ./scripts/dev.ps1 fragment 124 added 'Added lateral join support.'
    ./scripts/dev.ps1 changelog-check
    ./scripts/dev.ps1 redis up

.NOTES
    Exit code is the subcommand's exit code: 0 ok, 1 failure, 2 setup problem.
#>
[CmdletBinding()]
param(
    # Subcommand; defaults to help.
    [Parameter(Position = 0)][string]$Command = 'help',
    # Everything after the subcommand is forwarded verbatim.
    [Parameter(ValueFromRemainingArguments = $true)][object[]]$Rest = @()
)

. (Join-Path $PSScriptRoot '_devlib.ps1')

$Rest = [string[]]$Rest

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Splits the forwarded arguments into pytest passthrough arguments and the two
# control switches this script claims for itself. `-Parallel` is not a pytest
# flag, so there is no collision risk.
function Split-Rest {
    param([string[]]$Arguments)
    $parallel = $false
    $passthrough = [System.Collections.Generic.List[string]]::new()
    foreach ($arg in $Arguments) {
        if ($arg -eq '-Parallel') { $parallel = $true; continue }
        if ($arg -eq '-Serial') { $parallel = $false; continue }
        $passthrough.Add($arg)
    }
    return [pscustomobject]@{ Parallel = $parallel; Args = $passthrough.ToArray() }
}

function Get-Context {
    $ctx = Get-PythonContext
    if (-not $ctx.Python) {
        Write-Fail 'no Python interpreter found. Create .venv3.14 in the repository root or set AR_VENV.'
        return $null
    }
    return $ctx
}

function Invoke-Pytest {
    <#
    .SYNOPSIS
        Run pytest with the repository PYTHONPATH and the project default target.
    #>
    param(
        [string[]]$PytestArgs = @(),
        [switch]$Parallel,
        [string]$Target = 'tests',
        [switch]$NoDefaultTarget
    )

    $ctx = Get-Context
    if (-not $ctx) { return 2 }
    Set-Location $ctx.Root
    Initialize-RepoEnv -Root $ctx.Root | Out-Null

    # The default target is only prepended when the caller supplied no path of
    # their own. Prepending unconditionally would turn `dev.ps1 test
    # tests/providers` into `pytest tests tests/providers`, silently running the
    # whole suite instead of the requested subset.
    $hasExplicitPath = @($PytestArgs | Where-Object {
            -not $_.StartsWith('-') -and (Test-Path -LiteralPath $_)
        }).Count -gt 0

    $arguments = @('-m', 'pytest')
    if (-not $NoDefaultTarget -and -not $hasExplicitPath -and $Target) { $arguments += $Target }
    if ($Parallel) {
        # The testsuite plugin is mandatory here: it owns the per-database
        # scenario pools and the `serial` marker grouping that keep parallel
        # workers from colliding on shared SQLite connections.
        $arguments += @('-n', 'auto', '--dist=loadgroup', '-p', 'rhosocial.activerecord.testsuite.conftest')
    }
    $arguments += $PytestArgs

    Write-Note "pytest $($arguments -join ' ')"
    return Invoke-Native -FilePath $ctx.Python -Arguments $arguments
}

function Test-TcpPort {
    param([string]$HostName = '127.0.0.1', [int]$Port = 6379, [int]$TimeoutMs = 400)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs)) { return $false }
        $client.EndConnect($async)
        return $true
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Get-ReportTool {
    param([string]$Name, [string]$Install)
    $path = Resolve-RepoTool -Name $Name
    if ($path) { Write-Pass "$Name -> $path" }
    else {
        Write-Fail "$Name not installed"
        Write-Note "install: $Install"
    }
    return $path
}

# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------

function Invoke-Doctor {
    Write-Step 'environment'
    Write-Item "PowerShell   $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition))"
    Write-Item "OS          $($PSVersionTable.OS)"
    Write-Item "repo        $(Get-RepoRoot)"

    $gitVersion = (& git --version)
    Write-Item "git         $gitVersion"
    $branch = (& git rev-parse --abbrev-ref HEAD)
    $dirty = @(& git status --porcelain)
    Write-Item "branch      $branch ($($dirty.Count) uncommitted path(s))"

    Write-Host ''
    Write-Step 'interpreter'
    $ctx = Get-Context
    if ($ctx) {
        Write-Item "python      $($ctx.Python)"
        Write-Item "virtualenv  $(if ($ctx.IsVenv) { $ctx.Venv } else { '<none: using PATH python>' })"
        $version = (& $ctx.Python -c 'import sys; print(sys.version.split()[0])')
        Write-Item "version     $version"
        Set-Location $ctx.Root
        $pythonPath = Initialize-RepoEnv -Root $ctx.Root
        Write-Item "PYTHONPATH  $pythonPath"

        Write-Host ''
        Write-Step 'test suite'
        # Captured deliberately: this is a diagnostic path, not test output.
        $suitePath = (& $ctx.Python -c 'import pathlib, rhosocial.activerecord.testsuite as t; print(pathlib.Path(t.__file__).parent)' 2>&1)
        if ($LASTEXITCODE -eq 0 -and $suitePath) {
            Write-Pass "testsuite   $suitePath"
            if ($suitePath -like '*\.worktree\*') {
                Write-Note 'this resolves inside a git worktree. CI installs the testsuite'
                Write-Note 'from a pinned release branch instead, so local results may differ.'
            }
        }
        else {
            Write-Fail 'rhosocial-activerecord-testsuite is not importable'
            Write-Note 'install: pip install rhosocial-activerecord-testsuite'
            Write-Note 'or   : pip install -e ../python-activerecord-testsuite'
        }
    }

    Write-Host ''
    Write-Step 'tools'
    Get-ReportTool -Name 'rg' -Install 'winget install BurntSushi.ripgrep.MSVC  (AGENTS.md requires rg for searches)' | Out-Null
    Get-ReportTool -Name 'ruff' -Install 'uv tool install ruff' | Out-Null
    Get-ReportTool -Name 'mypy' -Install 'uv tool install mypy' | Out-Null
    Get-ReportTool -Name 'black' -Install 'uv tool install black' | Out-Null
    Get-ReportTool -Name 'isort' -Install 'uv tool install isort' | Out-Null
    Get-ReportTool -Name 'towncrier' -Install 'uv tool install towncrier' | Out-Null
    Get-ReportTool -Name 'gh' -Install 'winget install GitHub.cli' | Out-Null
    Get-ReportTool -Name 'docker' -Install 'winget install Docker.DockerDesktop' | Out-Null

    Write-Host ''
    Write-Step 'services'
    if (Test-TcpPort -Port 6379) {
        Write-Pass 'redis reachable on 127.0.0.1:6379'
    }
    else {
        Write-Fail 'redis not reachable on 127.0.0.1:6379'
        Write-Note 'the `redis` marked cache tests need it; start with: ./scripts/dev.ps1 redis up'
    }

    Write-Host ''
    Write-Step 'portability'
    $hasFcntl = (& $ctx.Python -c 'import importlib.util; print("yes" if importlib.util.find_spec("fcntl") else "no")')
    if ($hasFcntl -eq 'yes') {
        Write-Pass 'fcntl available (POSIX slot locking for pooled databases)'
    }
    else {
        Write-Fail 'fcntl unavailable -- pooled (file-based) SQLite scenarios will error'
        Write-Note 'testsuite/core/pool.py imports fcntl unconditionally for slot locking.'
        Write-Note 'On Windows every fixture reaching pooled_database_path() raises'
        Write-Note 'ModuleNotFoundError at setup. In-memory scenarios are unaffected.'
        Write-Note 'This is an upstream testsuite issue, not a repository defect.'
    }

    Write-Host ''
    Write-Step 'git hooks'
    $hooksPath = (& git config --get core.hooksPath)
    if ($LASTEXITCODE -ne 0 -or -not $hooksPath) { $hooksPath = '.git/hooks' }
    if (-not [System.IO.Path]::IsPathRooted($hooksPath)) { $hooksPath = Join-Path (Get-RepoRoot) $hooksPath }
    $hook = Join-Path $hooksPath 'pre-commit'
    if (Test-Path -LiteralPath $hook) { Write-Pass "pre-commit installed at $hook" }
    else {
        Write-Fail 'pre-commit hook not installed'
        Write-Note 'install: ./scripts/dev.ps1 hooks'
    }
    return 0
}

function Invoke-Lint {
    $split = Split-Rest $Rest
    $target = if ($split.Args.Count) { $split.Args[0] } else { 'src' }
    $extra = if ($split.Args.Count -gt 1) { $split.Args[1..($split.Args.Count - 1)] } else { @() }
    $ruff = Resolve-RepoTool -Name 'ruff'
    if (-not $ruff) {
        Write-Fail 'ruff not installed (uv tool install ruff)'
        return 2
    }
    Write-Step "ruff check $target"
    return Invoke-Native -FilePath $ruff -Arguments (@('check', $target) + $extra)
}

function Invoke-Fmt {
    # --with-black / --with-isort are claimed by this script, not by ruff, so
    # they are stripped before the target is read.
    $flags = @($Rest | Where-Object { $_ -in @('--with-black', '--with-isort') })
    $args = @($Rest | Where-Object { $_ -notin @('--with-black', '--with-isort', '-Parallel', '-Serial') })
    $target = if ($args.Count) { $args[0] } else { 'src' }
    $code = 0

    $ruff = Resolve-RepoTool -Name 'ruff'
    if ($ruff) {
        Write-Step "ruff check --fix $target"
        $code = Invoke-Native -FilePath $ruff -Arguments (@('check', '--fix', $target))
    }
    else {
        Write-Fail 'ruff not installed (uv tool install ruff)'
        $code = 2
    }

    # black/isort are configured in pyproject.toml (line-length 100) but are not
    # installed by default, and ruff's own line-length is 120 -- so they are
    # opt-in to keep `ruff format` from silently reformatting against black.
    if ($flags -contains '--with-isort') {
        $isort = Resolve-RepoTool -Name 'isort'
        if ($isort) {
            Write-Step "isort $target"
            $result = Invoke-Native -FilePath $isort -Arguments @($target)
            if ($result -ne 0) { $code = $result }
        }
        else { Write-Fail 'isort not installed (uv tool install isort)'; $code = 2 }
    }

    if ($flags -contains '--with-black') {
        $black = Resolve-RepoTool -Name 'black'
        if ($black) {
            Write-Step "black $target  (line-length 100, per [tool.black])"
            $result = Invoke-Native -FilePath $black -Arguments @($target)
            if ($result -ne 0) { $code = $result }
        }
        else { Write-Fail 'black not installed (uv tool install black)'; $code = 2 }
    }
    else {
        Write-Note 'add --with-black / --with-isort to also run the configured formatters'
    }

    return $code
}

function Invoke-TypeCheck {
    $mypy = Resolve-RepoTool -Name 'mypy'
    if (-not $mypy) {
        Write-Fail 'mypy not installed (uv tool install mypy)'
        return 2
    }
    $target = if ($Rest.Count) { $Rest[0] } else { 'src' }
    Write-Note '[tool.mypy] pins python_version = 3.8; expect 3.8-compat diagnostics'
    Write-Step "mypy $target"
    return Invoke-Native -FilePath $mypy -Arguments @($target)
}

function Invoke-PreflightOnly {
    $path = Join-Path $PSScriptRoot 'preflight.ps1'
    $args = @($Rest)
    & $path @args
    return $LASTEXITCODE
}

function Invoke-Hooks {
    $path = Join-Path $PSScriptRoot 'install-git-hooks.ps1'
    & $path @Rest
    return $LASTEXITCODE
}

function Invoke-ChangelogCheck {
    $path = Join-Path $PSScriptRoot 'changelog-check.ps1'
    & $path @Rest
    return $LASTEXITCODE
}

function Invoke-Fragment {
    if ($Rest.Count -lt 2) {
        Write-Fail 'usage: dev.ps1 fragment <pr-number> <type> ["<text>"]'
        Write-Note "types: $((Get-TowncrierTypes) -join ', ')"
        return 2
    }

    $number = $Rest[0]
    $type = $Rest[1]
    $text = if ($Rest.Count -ge 3) { $Rest[2] } else { '' }

    if ($number -notmatch '^\d+$') {
        Write-Fail "'$number' is not a PR number"
        return 2
    }

    $knownTypes = Get-TowncrierTypes
    if ($type -notin $knownTypes) {
        Write-Fail "'$type' is not a configured towncrier type"
        Write-Note "types: $($knownTypes -join ', ')"
        return 2
    }

    $root = Get-RepoRoot
    $path = Join-Path $root "changelog.d/$number.$type.md"
    if (Test-Path -LiteralPath $path) {
        Write-Fail "changelog.d/$number.$type.md already exists"
        Write-Note 'a PR may add several fragments, but only one per type'
        return 1
    }

    if (-not $text) {
        $text = 'TODO: describe the user-visible change in past tense (see changelog.d/README.md)'
    }

    # LF, per .gitattributes.
    [System.IO.File]::WriteAllText($path, "$text`n", [System.Text.UTF8Encoding]::new($false))
    Write-Pass "created changelog.d/$number.$type.md"
    Write-Note "git add changelog.d/$number.$type.md"
    return 0
}

function Invoke-Redis {
    $container = 'ar-test-redis'
    # 8.8 matches the redis service version used by the main CI test job.
    $image = 'redis:8.8'
    $action = if ($Rest.Count) { $Rest[0] } else { 'status' }

    switch ($action) {
        'up' {
            $existing = (& docker ps -a --filter "name=^/$container$" --format '{{.Names}}')
            if ($existing) {
                Write-Step "redis: starting existing container $container"
                return Invoke-Native -FilePath 'docker' -Arguments @('start', $container)
            }
            Write-Step "redis: starting $image on 127.0.0.1:6379"
            return Invoke-Native -FilePath 'docker' -Arguments @(
                'run', '-d', '--name', $container, '-p', '6379:6379', $image
            )
        }
        'down' {
            Write-Step "redis: stopping $container"
            return Invoke-Native -FilePath 'docker' -Arguments @('stop', $container)
        }
        'logs' {
            return Invoke-Native -FilePath 'docker' -Arguments @('logs', '--tail', '50', $container)
        }
        'status' {
            if (Test-TcpPort -Port 6379) { Write-Pass 'redis reachable on 127.0.0.1:6379' }
            else { Write-Fail 'redis not reachable on 127.0.0.1:6379' }
            return 0
        }
        default {
            Write-Fail "unknown redis action '$action' (up | down | status | logs)"
            return 2
        }
    }
}

function Invoke-Clean {
    $dry = $Rest -contains '-Dry'
    $removed = 0

    Write-Step 'stray test databases in TEMP'
    $strays = @(Get-ChildItem -Path $env:TEMP -Filter 'test_activerecord_*.sqlite' -File -ErrorAction SilentlyContinue)
    Write-Item "$($strays.Count) file(s) matching test_activerecord_*.sqlite"
    if ($strays -and -not $dry) {
        $strays | Remove-Item -Force
        $removed += $strays.Count
    }

    Write-Host ''
    Write-Step '__pycache__ under src/ and tests/'
    $cacheRoots = @((Join-Path (Get-RepoRoot) 'src'), (Join-Path (Get-RepoRoot) 'tests'))
    $caches = @(Get-ChildItem -Path $cacheRoots -Filter '__pycache__' -Directory -Recurse -ErrorAction SilentlyContinue)
    Write-Item "$($caches.Count) director(ies)"
    if ($caches -and -not $dry) {
        # Deepest first: removing a parent invalidates the children's paths.
        $caches | Sort-Object { $_.FullName.Length } -Descending | Remove-Item -Recurse -Force
        $removed += $caches.Count
    }

    Write-Host ''
    Write-Step '.pytest_cache'
    $pytestCache = Join-Path (Get-RepoRoot) '.pytest_cache'
    if (Test-Path -LiteralPath $pytestCache) {
        Write-Item $pytestCache
        if (-not $dry) { Remove-Item -LiteralPath $pytestCache -Recurse -Force; $removed++ }
    }
    else { Write-Item 'absent' }

    Write-Host ''
    if ($dry) { Write-Note '-Dry: nothing was deleted' }
    else { Write-Pass "removed $removed item(s)" }
    return 0
}

function Invoke-Version {
    $root = Get-RepoRoot
    Write-Step 'version'
    $pyproject = Get-Content -LiteralPath (Join-Path $root 'pyproject.toml')
    $declared = ($pyproject | Where-Object { $_ -match '^\s*version\s*=' } | Select-Object -First 1)
    if ($declared -match '"([^"]+)"') {
        Write-Item "pyproject    $($Matches[1])"
        $changelog = Join-Path $root 'CHANGELOG.md'
        if (Test-Path -LiteralPath $changelog) {
            $top = Get-Content -LiteralPath $changelog | Where-Object { $_ -match '^## \[' } | Select-Object -First 1
            if ($top) { Write-Item "CHANGELOG    $top" }
        }
    }

    Write-Item "branch      $(& git rev-parse --abbrev-ref HEAD)"
    $describe = (& git describe --tags --always 2>$null)
    if ($describe) { Write-Item "describe    $describe" }

    $fragments = @(Get-ChildItem -Path (Join-Path $root 'changelog.d') -Filter '*.md' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^\d+\.[A-Za-z]+\.md$' })
    Write-Item "fragments   $($fragments.Count) pending: $(($fragments.Name) -join ', ')"
    return 0
}

function Invoke-Verify {
    # Everything CI checks cheaply, in the order that fails fastest.
    Write-Step 'verify: lint'
    $lintCode = Invoke-Lint
    Write-Host ''
    Write-Step 'verify: collection'
    $collectCode = Invoke-Pytest -PytestArgs @('--collect-only', '-q', '-p', 'no:cacheprovider')
    Write-Host ''
    Write-Step 'verify: changelog fragments'
    $changelogCode = Invoke-ChangelogCheck

    $code = 0
    if ($lintCode -ne 0) { $code = 1 }
    if ($collectCode -ne 0) { $code = 1 }
    if ($changelogCode -ne 0) { $code = 1 }

    Write-Host ''
    if ($code -eq 0) { Write-Pass 'verify OK' } else { Write-Fail 'verify FAILED' }
    return $code
}

function Write-Help {
    Write-Step 'dev.ps1 -- local development entry point'
    Write-Host ''
    Write-Host '  USAGE'
    Write-Host '    ./scripts/dev.ps1 <command> [arguments...]'
    Write-Host ''
    Write-Host '  ENVIRONMENT'
    Write-Host '    doctor              report interpreter, tools, services, git hooks'
    Write-Host '    version             pyproject version, CHANGELOG head, pending fragments'
    Write-Host '    clean [-Dry]        remove stray test_activerecord_*.sqlite, __pycache__, .pytest_cache'
    Write-Host '    redis up|down|status|logs    manage the CI redis service via docker'
    Write-Host ''
    Write-Host '  TESTS (serial unless -Parallel is passed)'
    Write-Host '    test [pytest args]  run pytest, default target: tests'
    Write-Host '    cov [pytest args]   same, with --cov=rhosocial --cov-branch'
    Write-Host '    collect             pytest --collect-only (import check, no tests run)'
    Write-Host '    bench [pytest args] run tests/benchmark with -m benchmark'
    Write-Host ''
    Write-Host '  QUALITY'
    Write-Host '    lint [target]       ruff check (default: src)'
    Write-Host '    fmt [target]        ruff check --fix; add --with-black / --with-isort'
    Write-Host '    type [target]       mypy (default: src)'
    Write-Host '    preflight [args]    lint + import smoke + collection (scripts/preflight.ps1)'
    Write-Host '    verify              lint + collection + changelog fragment rules'
    Write-Host ''
    Write-Host '  WORKFLOW'
    Write-Host '    hooks [-Remove]     install/remove the pre-commit pre-flight hook'
    Write-Host '    fragment <pr> <type> ["text"]'
    Write-Host '                        create changelog.d/<pr>.<type>.md'
    Write-Host '    changelog-check [args]'
    Write-Host '                        local mirror of the CI fragment rules'
    Write-Host ''
    Write-Host '  EXAMPLES'
    Write-Host "    ./scripts/dev.ps1 test -k cte"
    Write-Host "    ./scripts/dev.ps1 test -Parallel"
    Write-Host "    ./scripts/dev.ps1 test tests/rhosocial/activerecord_test/feature/query --tb=short"
    Write-Host "    ./scripts/dev.ps1 fragment 124 fixed 'Fixed alias contamination in as_().'"
    Write-Host ''
    Write-Host '  ENVIRONMENT OVERRIDES'
    Write-Host '    AR_VENV=<dir>   use this virtualenv instead of .venv3.14'
    Write-Host '    AR_RUFF=<file>  use this ruff executable'
    return 0
}

# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

Set-Location (Get-RepoRoot)

$split = Split-Rest $Rest
$code = switch ($Command) {
    'doctor' { Invoke-Doctor }
    'version' { Invoke-Version }
    'clean' { Invoke-Clean }
    'redis' { Invoke-Redis }
    'test' { Invoke-Pytest -PytestArgs $split.Args -Parallel:$split.Parallel }
    'cov' {
        Invoke-Pytest -Parallel:$split.Parallel -PytestArgs (@(
                '--cov=rhosocial', '--cov-branch',
                '--cov-report=term', '--cov-report=xml'
            ) + $split.Args)
    }
    'collect' { Invoke-Pytest -NoDefaultTarget -PytestArgs (@('--collect-only', '-q', '-p', 'no:cacheprovider') + $split.Args) }
    'bench' { Invoke-Pytest -Target 'tests/benchmark' -PytestArgs (@('-m', 'benchmark') + $split.Args) }
    'lint' { Invoke-Lint }
    'fmt' { Invoke-Fmt }
    'type' { Invoke-TypeCheck }
    'preflight' { Invoke-PreflightOnly }
    'hooks' { Invoke-Hooks }
    'changelog-check' { Invoke-ChangelogCheck }
    'fragment' { Invoke-Fragment }
    'verify' { Invoke-Verify }
    { $_ -in @('help', '-h', '--help', '-?', '/?') } { Write-Help }
    default {
        Write-Fail "unknown command '$Command'"
        Write-Host ''
        Write-Help | Out-Null
        2
    }
}

if ($null -eq $code) { $code = 0 }
exit $code
