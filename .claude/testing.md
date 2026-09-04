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

## 4. Test Directory Structure

### 4.1 Testsuite Overview

**IMPORTANT**: The testsuite (`python-activerecord-testsuite`) tests **ActiveRecord layer** functionality, NOT backend-specific features. It provides shared fixtures and test contracts for cross-backend consistency.

**Testsuite Categories**:

| Category | Description |
|----------|-------------|
| `basic/` | Core CRUD, field types, type adapters, validation, column mapping, connection/worker lifecycle, composite PK CRUD, derived field |
| `query/` | ActiveQuery — building, execution, aggregation, joins, CTEs, window functions, eager loading, cross-database, composite PK queries/CTE/set operations |
| `relation/` | Relationship descriptors (BelongsTo/HasOne/HasMany), caching, eager loading, validation, modifiers, derived fields, edge cases |
| `events/` | Lifecycle hooks and event handler registration |
| `mixins/` | Built-in mixins — timestamps, soft delete, optimistic locking |
| `interface/` | Core interface utilities — ThreadSafeDict |
| `examples/` | Documentation examples for the capability-based framework |

### 4.2 Directory Hierarchy

Tests are organized by category, with subdirectories for each functional area.

```
tests/
├── rhosocial/activerecord_test/
│   ├── feature/                          # test category
│   │   ├── backend/                      # backend tests
│   │   │   ├── adapters/                 # common subject (value adapters)
│   │   │   ├── backend/                  # common subject (lifecycle/config)
│   │   │   ├── cli/                      # common subject (CLI)
│   │   │   ├── concurrency/              # common subject (concurrency protocol)
│   │   │   ├── ddl/                      # common subject (DDL)
│   │   │   ├── dialect/                  # common subject (dialect)
│   │   │   ├── dml/                      # common subject (DML)
│   │   │   ├── functions/                # common subject (functions)
│   │   │   ├── introspection/            # common subject (introspection)
│   │   │   ├── named_connection/         # common subject (named connections)
│   │   │   ├── protocol/                 # common subject (capability protocol)
│   │   │   ├── query/                    # common subject (query features)
│   │   │   ├── schema/                   # common subject (schema)
│   │   │   ├── transactions/             # common subject (transactions)
│   │   │   ├── views/                    # common subject (views)
│   │   │   ├── sqlite/                   # vendor-specific (SQLite features)
│   │   │   │   └── extensions/           #   └─ FTS5, R-Tree, GeoPoly, Pragma
│   │   │   ├── mysql/                    # vendor-specific (MySQL features)
│   │   │   │   ├── extensions/           #   ├─ partition, optimizer hints, JSON Duality View
│   │   │   │   └── spatial/              #   └─ spatial types and expressions
│   │   │   ├── postgres/                 # vendor-specific (PostgreSQL features)
│   │   │   │   ├── types/                #   ├─ hstore, ltree, range, uuid, xml, pgvector
│   │   │   │   ├── extensions/           #   ├─ PostGIS, pgcrypto, pg_trgm, citext
│   │   │   │   ├── ddl/                  #   ├─ DDL-specific features
│   │   │   │   ├── dialect/              #   ├─ dialect-specific features
│   │   │   │   ├── functions/            #   ├─ function-specific features
│   │   │   │   ├── query/                #   ├─ query-specific features
│   │   │   │   ├── schema/               #   ├─ schema-specific features
│   │   │   │   └── views/                #   └─ view-specific features
│   │   │   └── ...                       # other vendor-specific features
│   │   ├── basic/                        # testsuite-introduced tests
│   │   ├── query/                        # testsuite-introduced tests
│   │   ├── relation/                     # testsuite-introduced tests
│   │   ├── events/                       # testsuite-introduced tests
│   │   ├── interface/                    # testsuite-introduced tests
│   │   ├── mixins/                       # testsuite-introduced tests
│   │   └── connection/                   # custom fixtures
│   ├── benchmark/                        # performance benchmarks
│   └── realworld/                        # real-world scenarios
```

### 4.3 Test Classification Principles

| Classification | Directory | Description |
|---------------|-----------|-------------|
| **Common test subjects** | `feature/backend/{common-subject}/` | Each backend sets up according to its actual capabilities. Test files, case names, descriptions, and logic are basically consistent. Purpose: quickly confirm the backend's capability scope (what it supports, what it doesn't). |
| **Vendor-specific tests** | `feature/backend/{vendor}/` | Backend-exclusive features, subdivided by subject (e.g., `postgres/types/`, `sqlite/extensions/`), placed under the specific backend directory |
| **testsuite-introduced tests** | `feature/basic/`, `feature/query/`, `feature/relation/` | Bridge files introduce testsuite for cross-backend consistency |
| **Custom fixtures tests** | `feature/connection/` | Custom fixtures, no testsuite |
| **Performance benchmark tests** | `benchmark/` | Performance tests, independent of functional tests |
| **Real-world scenario tests** | `realworld/` | End-to-end scenario tests |

### 4.4 Common Test Subjects (feature/backend/)

**Principle**: Each backend sets up common test subjects according to its actual capabilities. Test files, case names, descriptions, and logic are basically consistent. Purpose: quickly confirm the backend's capability scope — what it supports, what it doesn't. If a backend is missing a subject, it must be added.

Common test subjects are divided into Functional Tests, Transaction Tests, CLI Tests, Query Tests, and Other Common Tests.

#### Functional Tests

| Subject | Directory | Description |
|---------|-----------|-------------|
| DDL | `ddl/` | Data Definition Language (CREATE, ALTER, DROP, etc.) |
| DML | `dml/` | Data Manipulation Language (INSERT, UPDATE, DELETE, etc.) |
| Introspection | `introspection/` | Schema introspection (tables, columns, indexes, etc.) |
| Views | `views/` | View execution |
| Schema | `schema/` | Schema support |

#### Transaction Tests

| Subject | Directory | Description |
|---------|-----------|-------------|
| Transactions | `transactions/` | Transaction behavior and isolation |

#### CLI Tests

| Subject | Directory | Description |
|---------|-----------|-------------|
| CLI | `cli/` | Command-line interface |

#### Query Tests

| Subject | Directory | Description |
|---------|-----------|-------------|
| Query | `query/` | Query features (CTE, EXPLAIN, etc.) |

#### Other Common Tests

| Subject | Directory | Description |
|---------|-----------|-------------|
| Adapters | `adapters/` | Value adapters |
| Backend | `backend/` | Process-level lifecycle/config |
| Concurrency | `concurrency/` | Concurrency protocol |
| Named Connection | `named_connection/` | Named connections |
| Protocol | `protocol/` | Capability protocol |
### 4.5 Vendor-Specific Feature Directories (feature/backend/{vendor}/)

**Principle**: Backend-exclusive features (no commonality) are placed under the specific backend directory, subdivided by subject category. Test files, case names, descriptions, and logic may vary between backends.

**Naming convention**: `{vendor}/{subject}/`, e.g., `postgres/types/`, `sqlite/extensions/`.

| Backend | Vendor Directory | Contents |
|---------|-----------------|----------|
| SQLite | `sqlite/extensions/` | FTS5, R-Tree, GeoPoly, Pragma and other SQLite-specific extensions |
| MySQL | `mysql/extensions/` | Partition, optimizer hints, JSON Duality View, SET type, etc. |
| MySQL | `mysql/spatial/` | MySQL spatial types and expressions |
| PostgreSQL | `postgres/types/` | hstore, ltree, range, uuid, xml, jsonpath, geometry, pgvector, etc. |
| PostgreSQL | `postgres/extensions/` | PostGIS, pgcrypto, pg_trgm, btree_gin, hstore, citext, cube, fuzzystrmatch, intarray, pg_stat_statements, pg_partman, pg_cron, orafce, tablefunc, uuid-ossp, etc. |
| PostgreSQL | `postgres/ddl/` | PostgreSQL-specific DDL features |
| PostgreSQL | `postgres/dialect/` | PostgreSQL-specific dialect features |
| PostgreSQL | `postgres/functions/` | PostgreSQL-specific functions |
| PostgreSQL | `postgres/query/` | PostgreSQL-specific query features |
| PostgreSQL | `postgres/schema/` | PostgreSQL-specific schema features |
| PostgreSQL | `postgres/views/` | PostgreSQL-specific view features |
| MariaDB | `mariadb/extensions/` | MariaDB-specific features (fulltext index, SET type, etc.) |
| SQL Server | `sqlserver/extensions/` | SQL Server-specific features (partition, spatial, xml, etc.) |
| Oracle | `oracle/extensions/` | Oracle-specific features (property graph, XML, etc.) |

## 5. Sync/Async Parity

### 5.1 Principle

**Principle**: Every sync test file must have a corresponding `_async.py` async test file.

| Rule | Description |
|------|-------------|
| File naming | Sync: `test_xxx.py`, Async: `test_xxx_async.py` |
| Class naming | Sync: `TestXxx`, Async: `AsyncTestXxx` |
| Method naming | Sync: `test_xxx`, Async: `test_xxx` (same name) |
| Fixture parity | If sync tests use fixtures, async tests must use corresponding async fixtures |
| Backend limitation | If backend only supports sync or async, only set corresponding tests |
| Missing = gap | If `_async` file exists, sync counterpart must exist, and vice versa |

### 5.2 Current Sync/Async Parity Status

**Policy (per cross-backend test taxonomy §4, refined)**: parity pairs are required only for
tests exercising **I/O-bearing APIs** (backend execute/fetch/transactions/introspection/migration).
Pure-sync surfaces — expression/dialect construction (`to_sql()`), mock-based unit tests, CLI,
record stores — have no async API to call and are exempt (P4: sync-only surface → no file).
Async twins use `TestAsyncXxx` class names (`python_classes = ["Test*"]`), co-located as
`test_x_async.py` next to `test_x.py`, with identical test-method names.

| Directory | Sync files | Async twins | Status |
|-----------|-----------|-------------|--------|
| backend/ | 18 | 9 | paired for I/O; config/exceptions/helpers/hooks/sqlite_core are sync-only surface |
| transactions/ | 4 | 4 | fully paired (base_transaction is sync-only TransactionManager unit surface) |
| dml/ | 12 | 6 | paired; protocol/clause files are dialect-construction only |
| ddl/ | 8 | 3 | paired; auto_increment/drop_cascade/generated_columns are expression-construction; migration async runs inline in test_migration.py + test_migration_async.py |
| functions/ | 8 | 1 | paired (sqlite_functions_integration is the I/O-bearing file; others are dialect formatting) |
| introspection/ | 17 | 12 | paired; to_sql/3_53_features/specific_params are sync surface |
| views/ | 2 | 1 | paired; materialized_view is expression-construction |
| concurrency/ | 1 | 1 | fully paired |
| query/ | 21 | 4 | explain trio paired; procedure files are mock-based with inline async classes; expression files sync-only |
| sqlite/extensions/ | 8 | 5 | paired; pragma_base/dialect_integration/extension_detection are dialect-detection only |
| sqlite/examples/ | 1 | 1 | fully paired |
| dialect/ protocol/ schema/ cli/ adapters/ named_connection/ dummy/ dummy2/ | 130+ | 0 | sync-only surface (no async API in subject) |

Acceptance check (twin pairing):

```bash
for f in $(find tests/rhosocial/activerecord_test/feature/backend -name 'test_*_async.py'); do
  base=${f%_async.py}.py; [ ! -f "$base" ] && echo "Missing sync counterpart: $f"
done   # must print nothing
```

## 6. Test Execution Commands

`pytest` with no args runs everything in `testpaths` (`pyproject.toml`). Prefer **directory-based**
selection (markers remain for legacy/global grouping):

```bash
export PYTHONPATH=src

# Backend standard tests (ddl, dml, dialect, etc.)
pytest tests/rhosocial/activerecord_test/feature/backend/ddl/
pytest tests/rhosocial/activerecord_test/feature/backend/dml/
pytest tests/rhosocial/activerecord_test/feature/backend/dialect/
pytest tests/rhosocial/activerecord_test/feature/backend/functions/
pytest tests/rhosocial/activerecord_test/feature/backend/introspection/
pytest tests/rhosocial/activerecord_test/feature/backend/query/
pytest tests/rhosocial/activerecord_test/feature/backend/transactions/
pytest tests/rhosocial/activerecord_test/feature/backend/views/

# Backend-specific tests (SQLite, MySQL, PostgreSQL, etc.)
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite/
pytest tests/rhosocial/activerecord_test/feature/backend/mysql/
pytest tests/rhosocial/activerecord_test/feature/backend/postgres/

# testsuite-introduced tests (via bridge files)
pytest tests/rhosocial/activerecord_test/feature/basic/
pytest tests/rhosocial/activerecord_test/feature/query/
pytest tests/rhosocial/activerecord_test/feature/relation/
pytest tests/rhosocial/activerecord_test/feature/events/
pytest tests/rhosocial/activerecord_test/feature/mixins/
pytest tests/rhosocial/activerecord_test/feature/interface/
pytest tests/rhosocial/activerecord_test/feature/connection/

# Real-world scenarios
pytest tests/rhosocial/activerecord_test/realworld/

# Performance benchmarks
pytest tests/benchmark/
```

## 7. Parallel Test Execution

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

## 8. Free-Threaded Python (3.13t / 3.14t)

Free-threaded builds are fully supported and all tests pass. Setup:

```bash
pyenv install 3.13t && pyenv local 3.13t   # macOS/Linux example
export PYTHONPATH=src
python -m pytest tests/                      # local tests
python -m pytest tests/ --run-testsuite      # include testsuite
```

Free-threading exposes race conditions hidden by the GIL — keep shared state synchronized.

## 9. Temporary Database Files

File-based scenarios create temp SQLite files named `test_activerecord_{scenario}_{uuid}.sqlite`
in the system temp dir. Interrupted runs may leave strays — clean up manually:

```bash
find /tmp -name "test_activerecord_*.sqlite" -delete   # macOS/Linux
Get-ChildItem -Path $env:TEMP -Name "test_activerecord_*.sqlite" | Remove-Item   # PowerShell
```

## 10. Authoring Tests

**Writing/adding tests is covered by the `dev-testing-contributor` skill** — load it for: testsuite
vs backend division of responsibilities, provider pattern & composite fixtures (tuples), protocol
feature detection (`@requires_protocol(ProtocolClass)` / `@requires_protocol(ProtocolClass, 'method')`),
schema file management, and sync/async parity rules.

Quick correctness checklist (also see skill):
- ✅ `PYTHONPATH=src` before pytest
- ✅ install testsuite; parallelize only with the plugin + serial markers (see §5)
- ✅ provider always returns tuples
- ✅ backend access via `model.backend()` / `model.__backend__` (per `IActiveRecord`)
- ✅ access fixtures via `pytest_runtest_call` + `item.funcargs` in plugins
- ✅ check leftover temp files after interruptions