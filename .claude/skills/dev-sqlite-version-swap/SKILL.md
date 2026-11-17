---
name: dev-sqlite-version-swap
description: Run Python against a different or full-featured SQLite engine for one process on Linux, WSL, Windows or macOS - build a SONAME-matched libsqlite3 or a feature-complete sqlite3.dll, point the loader at it, and verify version, compile options and capability probes before trusting the tests
license: MIT
compatibility: opencode
metadata:
  category: testing
  level: intermediate
  audience: developers
  order: 12
---

# Swapping the SQLite Engine for One Process

Some behaviour can only be checked against the engine that has it: a capability
added in a later SQLite, a compile option the distribution build omits, a
virtual table module. Waiting for a CI image to ship that build turns a
one-line question into a release-cycle question.

Python's `sqlite3` module does not contain SQLite. It is a thin extension
(`_sqlite3`) that calls a shared library. On Linux that library is normally
`libsqlite3.so.0`, resolved at process start by the dynamic loader. Build a
library with that exact **SONAME**, keep it in a private directory, and start
the process with `LD_LIBRARY_PATH` pointing there: the extension loads yours,
and the interpreter, the venv and the installed packages are untouched.

This is a *per-process* substitution. Nothing is installed, nothing is
overwritten, and closing the shell restores the system engine.

## When this is the right tool

- A test is gated on an engine version or compile option and has never actually
  run in CI.
- A dialect advertises a capability, and you want to execute the statement on
  the engine that supposedly has it.
- You need a module (`FTS5`, R-Tree, Geopoly, `dbstat`) that the distro build
  left out.

## When it is not

- The question is about a different database, not a different SQLite build.
- You need a change visible to other commands after the test command exits.
  Export the variables per command instead of persisting them.
- The Python build links SQLite statically. This method cannot reach it; see
  *Diagnose* below.

## Preflight: prove the link is dynamic

Before building anything, confirm the extension goes through a shared library.

```bash
python3 - <<'PY'
import _sqlite3, sqlite3
print("module:", _sqlite3.__file__)
print("engine:", sqlite3.sqlite_version)
PY
ldd "$(python3 -c 'import _sqlite3; print(_sqlite3.__file__)')" | grep -i sqlite
```

A line naming `libsqlite3.so.0` is the precondition. No such line means the
engine is compiled into the extension or into Python itself, and the rest of
this skill does nothing. Record the engine version printed here as the baseline.

## Build a replacement

The `scripts/` directory of this skill holds four helpers:

| Script | Platform | Purpose |
|---|---|---|
| `build_sqlite_swap.sh <version> [prefix]` | Linux / WSL | Build `libsqlite3.so.0` with a matching SONAME. |
| `build_sqlite_swap.ps1 -Version <ver>` | Windows | Build a full-featured `sqlite3.dll` with MSVC and copy `_sqlite3.pyd` beside it. |
| `verify_sqlite_features.py` | all | Print version, check compile options and probe reachable modules/functions. |
| `run_with_sqlite_swap.py` | Windows (works elsewhere) | Put the private directory at `sys.path[0]`, then hand args to pytest. |

`scripts/build_sqlite_swap.sh` does the work: it resolves the amalgamation
archive for a version from the official download page, compiles it with the
features usually wanted for capability tests, writes `libsqlite3.so.0` with the
matching SONAME, and prints the verification command.

```bash
scripts/build_sqlite_swap.sh 3.53.0
```

The default destination is `~/.local/sqlite-swap/<version>`. Pass a second
argument to choose another directory. No `sudo`, and no write outside that
directory.

The official download page lists only the current release, so the script locates
an older archive by probing the year directories under `sqlite.org`. If that is
slow or the host is unreachable, pin the source explicitly:

```bash
SQLITE_AMALGAMATION_YEAR=2026 scripts/build_sqlite_swap.sh 3.53.0
SQLITE_AMALGAMATION_URL=https://example.invalid/sqlite-amalgamation-3530000.zip \
    scripts/build_sqlite_swap.sh 3.53.0
```

### What the link flags mean

| Flag | Why it is there |
|---|---|
| `-Wl,-soname,libsqlite3.so.0` | Makes the produced file declare the name the loader looks for. Without it the extension ignores the file and keeps using the system library. |
| `-fPIC -shared` | A shared object, not an executable. |
| `-DSQLITE_ENABLE_FTS5` | FTS5 module and `bm25`/`highlight`/`snippet`. |
| `-DSQLITE_ENABLE_RTREE` | R-Tree module. |
| `-DSQLITE_ENABLE_GEOPOLY` | Geopoly module. |
| `-DSQLITE_ENABLE_DBSTAT_VTAB` | The `dbstat` virtual table used by storage introspection. |
| `-DSQLITE_ENABLE_MATH_FUNCTIONS` | Built-in math functions. |
| `-DSQLITE_ENABLE_COLUMN_METADATA` | `sqlite3_column_*` metadata used by some drivers. |
| `-DSQLITE_ENABLE_PERCENTILE` | `percentile()` extension function. |
| `-DSQLITE_ENABLE_DBPAGE_VTAB` | Raw page `dbpage` virtual table. |
| `-DSQLITE_ENABLE_STMTVTAB` | `stmtvtab` virtual table. |
| `-DSQLITE_ENABLE_BYTECODE_VTAB` | `bytecode` virtual table. |
| `-DSQLITE_ENABLE_SERIALIZE` / `DESERIALIZE` | Serialization API (built in by default in modern SQLite; not printed in `compile_options`). |

For "all features" builds add `FTS3`, `FTS4`, `PREUPDATE_HOOK`, `SESSION`,
`NORMALIZE`, `EXPLAIN_COMMENTS`, `STMT_SCANSTATUS`, `UPDATE_DELETE_LIMIT`,
`LOAD_EXTENSION` and `THREADSAFE=1`. Note that `dbpage`, `stmtvtab` and
`bytecode` are compiled in but gated behind `sqlite3_db_config()` in the C API;
Python's stdlib `sqlite3` does not expose that call, so they cannot be created
from Python even though `compile_options` lists them. Treat that as a loader
limitation, not a failed build.

Build flags decide which features *exist*; `PRAGMA compile_options` is how a
dialect finds out. If a capability probe reads compile options, it will
answer according to this build.

## Verify before using it

```bash
PREFIX="$HOME/.local/sqlite-swap/3.53.0"
LD_LIBRARY_PATH="$PREFIX/lib" python3 - <<'PY'
import sqlite3
connection = sqlite3.connect(":memory:")
print("module sees:", sqlite3.sqlite_version)
print("engine says:", connection.execute("select sqlite_version()").fetchone()[0])
print("compile options:")
for (option,) in connection.execute("pragma compile_options"):
    print(" ", option)
PY
```

Both version lines must agree, and `compile_options` must contain the flags you
built with. If the version is unchanged, stop and read *Diagnose*.

Also confirm the loader really picked the private directory:

```bash
LD_DEBUG=libs LD_LIBRARY_PATH="$PREFIX/lib" python3 -c 'import sqlite3' 2>&1 | grep -i libsqlite3
```

## Run the tests

Pass both variables on the command line; do not export them in a shell profile.

```bash
PREFIX="$HOME/.local/sqlite-swap/3.53.0"
LD_LIBRARY_PATH="$PREFIX/lib" PYTHONPATH=src:tests python3 -m pytest path/to/tests -q
```

Tests that read `sqlite3.sqlite_version` or `PRAGMA compile_options` now see the
new engine, which is the point: a capability-gated test that used to skip must
run, and an execution test must execute the statement it renders.

### Version-cached state

Swapping is process-wide, but libraries may cache an engine fact after the first
read. A class-level version cache or a memoised `compile_options` answer will
still describe the previous build. Reset those caches in the test session (or
start a fresh process) before trusting the result. A leaked cache is worse than
a skip: the suite reports success for a version nobody is running.

## Diagnose

| Symptom | Likely cause |
|---|---|
| Version unchanged, `ldd` shows `libsqlite3.so.0` | The file's SONAME does not match, or the loader found the system copy first. Check `readelf -d "$PREFIX/lib/libsqlite3.so.0" \| grep SONAME`. |
| Version unchanged, `ldd` shows no sqlite line | The extension or interpreter links SQLite statically; this method cannot reach it. |
| A feature is still missing though the version is right | The build did not enable it. Check `PRAGMA compile_options`, then rebuild with the flag. |
| `LD_DEBUG` names another path | Another entry in the search order wins (a wrapper script, a container, an RPATH). Inspect with `LD_DEBUG=libs`. |
| Other libraries in the process fail | They resolved the same SONAME to your build. For a test process that is acceptable; do not use this method for unrelated workloads. |

## Windows: swap the DLL for one process

CPython on Windows keeps `DLLs/_sqlite3.pyd` and `DLLs/sqlite3.dll` side by side
in each installation. The extension loads `sqlite3.dll` by name from the
directory of the loaded module, so a private directory containing **both files**
wins if it sits at `sys.path[0]` before anything imports `sqlite3`.

`PYTHONPATH` alone does **not** work: CPython puts its own `DLLs/` ahead of
`PYTHONPATH` on `sys.path`. Use the launcher.

1. Build with MSVC (BuildTools provides `vcvars64.bat`):

   ```powershell
   .claude/skills/dev-sqlite-version-swap/scripts/build_sqlite_swap.ps1 -Version 3.53.4
   ```

   The script downloads the amalgamation if needed, compiles a full-featured
   `sqlite3.dll` into `%LOCALAPPDATA%\sqlite-swap\<version>\bin`, and copies
   `_sqlite3.pyd` next to it. The `/DSQLITE_API=__declspec(dllexport)` define is
   **mandatory**: without it the DLL loads via `ctypes` but exports no
   `sqlite3_*` symbols, and importing `_sqlite3.pyd` fails with "not a valid
   Win32 application".
2. Verify the engine the launcher will load. Use the **project venv** interpreter
   (it has pytest and the project installed); the probe itself needs only stdlib:

   ```powershell
   $env:SQLITE_SWAP_DIR="$env:LOCALAPPDATA\sqlite-swap\3.53.4\bin"
   .\.venv3.15\Scripts\python.exe `
       .claude/skills/dev-sqlite-version-swap/scripts/verify_sqlite_features.py
   ```

   The probe inserts `SQLITE_SWAP_DIR` at `sys.path[0]` itself on Windows, so it
   reports the engine that tests will actually use.

3. Run tests with the same venv interpreter:

   ```powershell
   .\.venv3.15\Scripts\python.exe `
       .claude/skills/dev-sqlite-version-swap/scripts/run_with_sqlite_swap.py `
       tests/... -q
   ```

   The launcher inserts the private directory at `sys.path[0]`, imports
   `sqlite3` early, prints the loaded engine version to stderr, then calls
   `pytest.main()`. Stopping use of the launcher restores the system engine.

An alternative is to back up `DLLs/sqlite3.dll`, copy the custom DLL over it,
run plain `python -m pytest`, then restore the backup. That changes every
process using the interpreter and is easy to forget — prefer the launcher.

Bitness and version must match: an x64 DLL for x64 Python, built from exactly
the version reported by `sqlite3.sqlite_version`, and with the other compile
options from `PRAGMA compile_options` preserved.

## macOS

The ELF mechanism above does not apply. Use `DYLD_LIBRARY_PATH` (or
`DYLD_INSERT_LIBRARIES`) with a matching `install_name`; SIP may ignore the
former for protected binaries. Verify with the same version/compile-option
probe before trusting a test run.

## Cleanup

Nothing was installed. Delete the private directory when done:

```bash
rm -rf "$HOME/.local/sqlite-swap/<version>"
```

## Checklist

1. `ldd` names `libsqlite3.so.0` before the build.
2. The built file's SONAME is `libsqlite3.so.0`.
3. `sqlite3.sqlite_version` and `select sqlite_version()` both report the target.
4. `PRAGMA compile_options` contains the features the tests need.
5. Any engine-fact cache in the code under test is reset.
6. `scripts/verify_sqlite_features.py` reports PASS (wanted options present, reachable probes OK).
7. On Windows, the private directory is at `sys.path[0]` via the launcher — `PYTHONPATH` alone is not enough.
8. The capability-gated tests now run instead of skip, and execute real SQL.
