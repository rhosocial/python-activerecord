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

**MUST set `PYTHONPATH=src` before running any pytest.** The test directory is **not** on the
module path; tests import `rhosocial.activerecord` from the `src/` tree.

```
project-root/
├── src/rhosocial/activerecord/  # ← importable
└── tests/                       # ← NOT on path by default
```

### Commands

Linux/macOS:
```bash
PYTHONPATH=src pytest         # single run
export PYTHONPATH=src          # persistent for session
```

Windows PowerShell 7 (recommended):
```powershell
$env:PYTHONPATH="src"; pytest
$env:PYTHONPATH="src"
```

Extension projects (`python-activerecord-mysql`, `-postgres`, ...) use their own `src/`. With the
core installed as a dependency, only the extension's `src/` is needed:
```bash
PYTHONPATH=src pytest                       # extension alone
PYTHONPATH=src:../python-activerecord/src pytest   # when core not installed
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
export PYTHONPATH=src

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
pytest tests/rhosocial/activerecord_test/realworld/ecommerce/
pytest tests/rhosocial/activerecord_test/realworld/finance/
pytest tests/benchmark/
```

## 5. CRITICAL: No Parallel Test Execution

Do **not** run tests with `pytest-xdist`/parallel workers. Concurrent runs collide on shared
`:memory:`/named SQLite connections and temporary files. Run tests serially.

## 6. Free-Threaded Python (3.13t / 3.14t)

Free-threaded builds are fully supported and all tests pass. Setup:

```bash
pyenv install 3.13t && pyenv local 3.13t   # macOS/Linux example
export PYTHONPATH=src
python -m pytest tests/                      # local tests
python -m pytest tests/ --run-testsuite      # include testsuite
```

Free-threading exposes race conditions hidden by the GIL — keep shared state synchronized.

## 7. Temporary Database Files

File-based scenarios create temp SQLite files named `test_activerecord_{scenario}_{uuid}.sqlite`
in the system temp dir. Interrupted runs may leave strays — clean up manually:

```bash
find /tmp -name "test_activerecord_*.sqlite" -delete   # macOS/Linux
Get-ChildItem -Path $env:TEMP -Name "test_activerecord_*.sqlite" | Remove-Item   # PowerShell
```

## 8. Authoring Tests

**Writing/adding tests is covered by the `dev-testing-contributor` skill** — load it for: testsuite
vs backend division of responsibilities, provider pattern & composite fixtures (tuples), protocol
feature detection (`@requires_protocol(ProtocolClass)` / `@requires_protocol(ProtocolClass, 'method')`),
schema file management, and sync/async parity rules.

Quick correctness checklist (also see skill):
- ✅ `PYTHONPATH=src` before pytest
- ✅ install testsuite, never run parallel
- ✅ provider always returns tuples
- ✅ backend access via `model.backend()` / `model.__backend__` (per `IActiveRecord`)
- ✅ access fixtures via `pytest_runtest_call` + `item.funcargs` in plugins
- ✅ check leftover temp files after interruptions