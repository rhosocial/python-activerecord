<#
.SYNOPSIS
Build a full-featured sqlite3.dll for the current Python on Windows.

.EXAMPLE
.\build_sqlite_swap.ps1 -Version 3.53.4

The DLL is written to $env:LOCALAPPDATA\sqlite-swap\3.53.4\bin together with a
copy of _sqlite3.pyd. Use run_with_sqlite_swap.py with SQLITE_SWAP_DIR pointing
at that bin directory to run tests against it. Nothing in the Python install is
modified.
#>
param(
    [string]$Version = '3.53.4',
    [string]$AmalgamationZip = '',
    [string]$Vcvars = '',
    [string]$PythonExe = '',
    [int]$AmalgamationYear = 2026
)

$ErrorActionPreference = 'Stop'

if (-not $PythonExe) {
    $PythonExe = (& py -3.15 -c 'import sys; print(sys.executable)' 2>$null).Trim()
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    throw 'Python executable not found; pass -PythonExe.'
}

if (-not $Vcvars) {
    $roots = @(
        'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools',
        'C:\Program Files\Microsoft Visual Studio\18\BuildTools',
        'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools',
        'C:\Program Files\Microsoft Visual Studio\2022\Community',
        'C:\Program Files\Microsoft Visual Studio\2022\Professional',
        'C:\Program Files\Microsoft Visual Studio\2022\Enterprise'
    )
    foreach ($root in $roots) {
        $candidate = Join-Path $root 'VC\Auxiliary\Build\vcvars64.bat'
        if (Test-Path $candidate) { $Vcvars = $candidate; break }
    }
}
if (-not $Vcvars -or -not (Test-Path $Vcvars)) {
    throw 'vcvars64.bat not found; pass -Vcvars.'
}

$parts = $Version.Split('.')
$major = [int]$parts[0]
$minor = [int]$parts[1]
$patch = if ($parts.Count -gt 2) { [int]$parts[2] } else { 0 }
$num = '{0}{1:00}{2:00}00' -f $major, $minor, $patch
$archive = "sqlite-amalgamation-$num.zip"
$prefix = Join-Path $env:LOCALAPPDATA "sqlite-swap\$Version"
$srcDir = Join-Path $prefix 'src'
$binDir = Join-Path $prefix 'bin'
New-Item -ItemType Directory -Force $srcDir, $binDir | Out-Null

if (-not $AmalgamationZip) { $AmalgamationZip = Join-Path $srcDir $archive }
if (-not (Test-Path $AmalgamationZip)) {
    $url = "https://www.sqlite.org/$AmalgamationYear/$archive"
    $env:HTTP_PROXY = 'http://127.0.0.1:7897'
    $env:HTTPS_PROXY = $env:HTTP_PROXY
    Invoke-WebRequest -Uri $url -OutFile $AmalgamationZip
}

if (-not (Test-Path (Join-Path $srcDir 'sqlite3.c'))) {
    Expand-Archive -Path $AmalgamationZip -DestinationPath $srcDir -Force
}
$sqliteC = (Get-ChildItem $srcDir -Recurse -Filter 'sqlite3.c' | Select-Object -First 1).FullName
if (-not $sqliteC) { throw 'sqlite3.c not found in the amalgamation archive.' }

$defines = @(
    'SQLITE_DLL',
    'SQLITE_API=__declspec(dllexport)',
    'SQLITE_ENABLE_FTS3',
    'SQLITE_ENABLE_FTS4',
    'SQLITE_ENABLE_FTS5',
    'SQLITE_ENABLE_RTREE',
    'SQLITE_ENABLE_GEOPOLY',
    'SQLITE_ENABLE_DBSTAT_VTAB',
    'SQLITE_ENABLE_DBPAGE_VTAB',
    'SQLITE_ENABLE_STMTVTAB',
    'SQLITE_ENABLE_BYTECODE_VTAB',
    'SQLITE_ENABLE_MATH_FUNCTIONS',
    'SQLITE_ENABLE_PERCENTILE',
    'SQLITE_ENABLE_COLUMN_METADATA',
    'SQLITE_ENABLE_SERIALIZE',
    'SQLITE_ENABLE_DESERIALIZE',
    'SQLITE_ENABLE_UPDATE_DELETE_LIMIT',
    'SQLITE_ENABLE_LOAD_EXTENSION',
    'SQLITE_ENABLE_NORMALIZE',
    'SQLITE_ENABLE_PREUPDATE_HOOK',
    'SQLITE_ENABLE_SESSION',
    'SQLITE_ENABLE_EXPLAIN_COMMENTS',
    'SQLITE_ENABLE_STMT_SCANSTATUS',
    'SQLITE_THREADSAFE=1'
)
$defineArgs = ($defines | ForEach-Object { "/D$_" }) -join ' '

$buildBat = Join-Path $prefix 'build.bat'
@"
@echo off
call "$Vcvars"
cd /d "$binDir"
cl /nologo /O2 $defineArgs /LD "$sqliteC" /link /out:sqlite3.dll
"@ | Set-Content -Encoding ASCII $buildBat
cmd /c "`"$buildBat`"" | Out-Null
if (-not (Test-Path (Join-Path $binDir 'sqlite3.dll'))) { throw 'build failed: no sqlite3.dll produced.' }

$dlls = Join-Path (Split-Path $PythonExe -Parent) 'DLLs'
$pyd = Join-Path $dlls '_sqlite3.pyd'
if (Test-Path $pyd) { Copy-Item $pyd $binDir -Force }

Write-Output "built: $(Join-Path $binDir 'sqlite3.dll')"
Write-Output 'verify:'
Write-Output "  & '$PythonExe' '$PSScriptRoot\verify_sqlite_features.py'"
Write-Output 'run tests:'
Write-Output "  `$env:SQLITE_SWAP_DIR='$binDir'"
Write-Output "  & '$PythonExe' '$PSScriptRoot\run_with_sqlite_swap.py' <pytest-args>"
