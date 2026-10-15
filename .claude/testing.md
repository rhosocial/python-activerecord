# Testing Guide for rhosocial-activerecord

> **Scope**: This file is the **runtime runbook** — how to set up the environment and execute the
> test suite. **Writing/authoring tests** (testsuite architecture, provider pattern, protocol-based
> feature selection, sync/async parity, fixture rules) lives in the **`dev-testing-contributor`**
> skill. Load that skill when writing or modifying tests.
>
> Rules index and navigation: `AGENTS.md` → "Rules Index".

## 1. Python Version Support

Python 3.8+ required. Full per-Python dependency pins: see `version_control.md` §1 and the
`requirements-3.8.txt` file (for Python 3.8 environments).

## 2. CRITICAL: PYTHONPATH Configuration

**Set `PYTHONPATH=src:tests` before running pytest.** `src` is already declared in `pyproject.toml` under `[tool.pytest.ini_options] pythonpath = [".", "src"]`, so it is `tests` that is load-bearing: it makes `providers/registry.py` importable. The test directory is **not** on the
module path; tests import `rhosocial.activerecord` from the `src/` tree.

```
project-root/
├── src/rhosocial/activerecord/  # ← importable
└── tests/                       # ← NOT on path by default
```

### Commands

Linux/macOS:
```bash
PYTHONPATH=src:tests pytest         # single run
export PYTHONPATH=src          # persistent for session
```

Windows PowerShell 7 (recommended):
```powershell
$env:PYTHONPATH="src;tests"; pytest
$env:PYTHONPATH="src;tests"
```

Extension projects (`python-activerecord-mysql`, `-postgres`, ...) use their own `src/`. With the
core installed as a dependency, only the extension's `src/` is needed:
```bash
PYTHONPATH=src:tests pytest                       # extension alone
PYTHONPATH=src:tests:../python-activerecord/src pytest   # when core not installed
```

**Common error without it**: `ModuleNotFoundError: No module named 'rhosocial.activerecord'`.

IDE setup: PyCharm — mark `src/` as Sources Root; VS Code — set `.env`/`pytestArgs` to `tests`.

## 3. CRITICAL: Test Suite Dependency

Tests rely on the shared `rhosocial-activerecord-testsuite` package (fixtures, provider registry,
protocol helpers). Without it: `ModuleNotFoundError: No module named 'rhosocial.activerecord.testsuite'`.

```bash
pip install rhosocial-activerecord-testsuite        # from PyPI
pip install -e ../python-activerecord-testsuite     # editable, for local test-suite dev
```

## 4. Test Execution Commands

`pytest` with no args runs everything in `testpaths` (`pyproject.toml`). Prefer **directory-based**
selection (markers remain for legacy/global grouping):

```bash
export PYTHONPATH=src:tests

# Feature tests by category
pytest tests/rhosocial/activerecord_test/feature/basic/
pytest tests/rhosocial/activerecord_test/feature/query/
pytest tests/rhosocial/activerecord_test/feature/relation/
pytest tests/rhosocial/activerecord_test/feature/events/
pytest tests/rhosocial/activerecord_test/feature/mixins/

# Backend-specific + dialect/interface tests
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite/
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite2/
pytest tests/rhosocial/activerecord_test/feature/backend/dialect/

# Real-world scenarios and benchmarks
pytest tests/rhosocial/activerecord_test/feature/basic/
pytest tests/rhosocial/activerecord_test/feature/query/
pytest tests/benchmark/
```

## 5. Parallel Test Execution

CI runs the suite in parallel with `pytest-xdist` (`-n auto`/`-n 8 --dist=loadgroup`) loading the
testsuite plugin (`-p rhosocial.activerecord.testsuite.conftest`). Shared-state tests — Redis
caches, worker pools, hook ordering, batch-loading state — are pinned to one worker with the
`serial` marker, and scenario pools use per-database names, so concurrent workers do not collide
on SQLite connections or temp files.

Locally, only parallelize **with the testsuite plugin loaded**:

```bash
export PYTHONPATH=src:tests
python -m pytest tests/ -n auto --dist=loadgroup -p rhosocial.activerecord.testsuite.conftest
```

Running `pytest -n` without the plugin still risks collisions on shared `:memory:`/named SQLite
connections and temp files — in that case run serially.

On Windows, run DB-backed scenarios in parallel with pooling disabled (`--db-pool-size 0`): the pool
then stays off and every test takes its own unique database name, so no cross-process slot lock is
needed. Pooled slot locking uses `fcntl`, which is POSIX-only.

## 6. Free-Threaded Python (3.13t / 3.14t)

Free-threaded builds are fully supported and all tests pass. Setup:

```bash
pyenv install 3.13t && pyenv local 3.13t   # macOS/Linux example
export PYTHONPATH=src:tests
python -m pytest tests/                      # local tests
python -m PYTHONPATH=src:tests pytest ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/
```

Free-threading exposes race conditions hidden by the GIL — keep shared state synchronized.

## 7. Temporary Database Files

File-based scenarios create temp SQLite files named `test_activerecord_{scenario}_{uuid}.sqlite`
in the system temp dir. Interrupted runs may leave strays — clean up manually:

```bash
find /tmp -name "test_activerecord_*.sqlite" -delete   # macOS/Linux
Get-ChildItem -Path $env:TEMP -Name "test_activerecord_*.sqlite" | Remove-Item   # PowerShell
```

## 8. Windows / PowerShell 7

`scripts/preflight.sh` and `scripts/install-git-hooks.sh` are POSIX. On Windows use their
counterparts, which share helpers via `scripts/_devlib.ps1`:

| Task | Command |
|------|---------|
| Environment report | `./scripts/dev.ps1 doctor` |
| Serial test run | `./scripts/dev.ps1 test` |
| Test run with pytest arguments | `./scripts/dev.ps1 test -k cte` |
| Parallel test run (opt-in, §5) | `./scripts/dev.ps1 test -Parallel` |
| Import check, no tests run | `./scripts/dev.ps1 collect` |
| Coverage | `./scripts/dev.ps1 cov -Parallel` |
| Lint / format / types | `./scripts/dev.ps1 lint` / `fmt` / `type` |
| Pre-flight (lint + import + collect) | `./scripts/dev.ps1 preflight` |
| Pre-push bundle | `./scripts/dev.ps1 verify` |
| Install / remove the pre-commit hook | `./scripts/dev.ps1 hooks [-Remove]` |
| Create a changelog fragment | `./scripts/dev.ps1 fragment <pr> <type> "<text>"` |
| Changelog rules locally (§ mirrors CI) | `./scripts/dev.ps1 changelog-check` |
| Redis service for `-m redis` | `./scripts/dev.ps1 redis up` / `down` / `status` |
| Remove stray temp databases and caches | `./scripts/dev.ps1 clean [-Dry]` |

Notes:

- **Serial by default.** `test` runs serially; `-Parallel` is the opt-in and adds
  `-n auto --dist=loadgroup -p rhosocial.activerecord.testsuite.conftest`, matching §5 and CI.
  Parallel execution is a supported and encouraged mode — iron rule 1 requires the plugin and the
  `serial` marker, it does not mandate a serial run.
- **`PYTHONPATH` is set for you**, as absolute `<root>/src;<root>/tests` (Windows path
  separator). An existing `PYTHONPATH` is preserved after ours.
- **Overrides**: `AR_VENV=<dir>` selects the virtualenv (default `.venv3.14`), `AR_RUFF=<file>`
  pins an executable. `doctor` reports both.
- **The git hook is a POSIX sh script** even when installed from PowerShell, because git for
  Windows runs hooks through its bundled shell. It prefers `preflight.ps1` and falls back to
  `preflight.sh`.
- **`doctor` checks the things that silently break a Windows run**: tool availability, the
  resolved testsuite path (it is an editable install and may point into a worktree), Redis
  reachability, hook installation, and whether `fcntl` is importable (see below).

### fcntl and pooled databases

`rhosocial-activerecord-testsuite`'s `core/pool.py` locks per-slot files with `fcntl.flock` while
the database pool is active — that is, parallel runs with a positive `--db-pool-size`. `fcntl` is
POSIX-only, so on Windows run DB scenarios in parallel with `--db-pool-size 0`: pooling stays off,
each test takes its own unique database name, and no cross-process slot lock is needed.

A serial Windows run used to fail after *every* test with `ModuleNotFoundError: No module named
'fcntl'` — the teardown hook releases slots unconditionally and imported `fcntl` at function entry,
although a serial run never holds a slot. Fixed in testsuite `458af92`: the release path returns
before the import.

## 9. Authoring Tests

**Writing/adding tests is covered by the `dev-testing-contributor` skill** — load it for: testsuite
vs backend division of responsibilities, provider pattern & composite fixtures (tuples), protocol
feature detection (`@requires_protocol(ProtocolClass)` / `@requires_protocol(ProtocolClass, 'method')`),
schema file management, and sync/async parity rules.

Quick correctness checklist (also see skill):
- ✅ `PYTHONPATH=src:tests` before pytest
- ✅ install testsuite; parallelize only with the plugin + serial markers (see §5)
- ✅ provider always returns tuples
- ✅ backend access via `model.backend()` / `model.__backend__` (per `IActiveRecord`)
- ✅ access fixtures via `pytest_runtest_call` + `item.funcargs` in plugins
- ✅ check leftover temp files after interruptions