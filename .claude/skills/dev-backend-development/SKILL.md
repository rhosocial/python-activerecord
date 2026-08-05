---
name: dev-backend-development
description: Complete guide for implementing new database backends for rhosocial-activerecord - StorageBackend, dialect, type adaptation, transactions, error handling, async equivalence, testing and release readiness
license: MIT
compatibility: opencode
metadata:
  category: backend
  level: advanced
  audience: developers
---

# Backend Development Guide

Complete instructions for implementing new database backends. A robust backend is more than a
query executor: it includes a database-specific **SQL Dialect**, a precise **Type Adaptation**
system, reliable **Transaction Management**, robust **Error Handling**, clear **Feature
Detection**, and **Performance Optimizations**.

> Use this skill together with **`dev-expression-dialect`** for the Expression-Dialect
> separation rules. Reference implementations: `rhosocial-activerecord-mysql`,
> `rhosocial-activerecord-postgres`. Study their `backend.py`/`adapters.py`/`tests/`.

**Design constraint**: use **native database drivers only** (`mysql-connector-python`,
`psycopg`, ...). No SQLAlchemy/Django ORM dependencies.

## Package Structure

Standardized layout (namespace packages):

```
rhosocial-activerecord-{backend}/
├── src/rhosocial/activerecord/backend/impl/{backend}/
│   ├── __init__.py
│   ├── backend.py       # Storage implementation (may be a `backend/` subpackage)
│   ├── adapters.py      # Type adapters (may be an `adapters/` subpackage)
│   ├── config.py        # Connection configuration
│   ├── dialect.py       # SQL dialect handling
│   ├── transaction.py   # Transaction management
│   ├── expression/      # Backend-specific expressions (DIRECTORY, required)
│   │   └── __init__.py
│   ├── functions/       # Backend-specific SQL functions (DIRECTORY, required)
│   │   └── __init__.py
│   └── features.py      # Optional: Feature detection
```

Layout evolution note: PostgreSQL splits `backend.py` into a `backend/` subpackage
(`base.py`, `sync.py`, `async_backend.py`) and `adapters.py` into `adapters/`; MySQL keeps flat
files. Both add `mixins/`, `cli/`, `explain/`, `introspection/`, `schema/`, `protocols.py`.
Mirror current reference implementations where practical; `expression/` and `functions/`
**directories** are required conventions.

Use **absolute imports** for expressions from core/other backends; avoid deep relative imports.

## StorageBackend Interface

Implement every abstract method:

- `connect()` / `disconnect()` / `ping(reconnect=True)`
- `execute(sql, params=None, returning=None, column_adapters=None) -> QueryResult`
- `get_server_version() -> tuple`
- `introspect_and_adapt()` — connect, query server version, re-init dialect + adapters by
  version (no-op for backends that don't need version adaptation, e.g. SQLite/Dummy)
- `_initialize_capabilities() -> DatabaseCapabilities`
- `_handle_error(error)` — map driver exceptions to standard `DatabaseError` subclasses
- `transaction_manager` / `dialect` properties
- `get_default_adapter_suggestions()` — preferred conversion strategy for the core
- `_register_my_adapters()` — instantiate + register adapters (allow `allow_override=True`)

## Connection Configuration

Immutable `@dataclass(frozen=True)` extending `BaseConfig` (`backend/config.py`):

```python
from dataclasses import dataclass
from rhosocial.activerecord.backend.config import BaseConfig

@dataclass(frozen=True)
class MyDatabaseConfig(BaseConfig):
    host: str = "localhost"
    port: int = 5432
    database: str
    user: str | None = None
    password: str | None = None
```

## SQL Dialect

- Inherits `SQLDialectBase` + relevant mixins + protocols (`backend/dialect.py`).
- Implement `quote_identifier`, `get_placeholder`, `format_limit_offset`, `get_type_mappings`,
  plus protocol methods.
- **Protocol-Mixin architecture**: Protocols (`protocols.py`) define the contract; Mixins
  (`mixins.py`) provide SQL-standard defaults a dialect overrides.
- Adding a protocol: SQL-standard features go in the main package; dialect-specific features in
  the extension dialect; update `DummyDialect`; add tests. See `dev-expression-dialect` for the
  full protocol/mixin table and workflow.

## Type Adaptation

Two-part: define `SQLTypeAdapter`s, then register them and expose suggestions.

```python
# adapters: subclass BaseSQLTypeAdapter; implement _do_to_database / _do_from_database
# backend registration:
def _register_my_adapters(self):
    for adapter in (DateTimeAdapter(), DecimalAdapter(), MyCustomJSONAdapter()):
        for py_type, driver_types in adapter.supported_types.items():
            for driver_type in driver_types:
                self.adapter_registry.register(adapter, py_type, driver_type, allow_override=True)

def get_default_adapter_suggestions(self):
    # e.g. datetime->str, Decimal->str, dict->str via adapter_registry.get_adapter(...)
```

## Transaction Management

```python
class MyTransactionManager:
    @contextmanager
    def transaction(self, isolation_level=None):
        self.connection.begin()
        try:
            yield self
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    @contextmanager
    def savepoint(self, name=None):
        # SAVEPOINT / RELEASE / ROLLBACK TO SAVEPOINT
        ...
```

## Error Handling

Map driver exceptions to core `DatabaseError` subclasses (`IntegrityError`, `ConnectionError`, ...):

```python
def _handle_error(self, error):
    if isinstance(error, native_driver.UniqueConstraintViolation):
        raise IntegrityError("Unique constraint failed") from error
    if isinstance(error, native_driver.CannotConnectNow):
        raise ConnectionError("Connection failed") from error
    raise DatabaseError(f"Unexpected database error: {error}") from error
```

## Asynchronous Backends

`AsyncStorageBackend` must provide **functional equivalence** with the sync `StorageBackend`:
implement async versions of all I/O-bound methods (`async def connect(...)`, `async def
execute(...)`) and use async-compatible mixins.

## Testing Requirements

- Connection & configuration (success, disconnect, ping, bad-config failure modes)
- CRUD & query execution (`execute`, `fetch_one`, `fetch_all`, ...)
- Type adaptation: unit tests per adapter + `get_default_adapter_suggestions` + end-to-end save/retrieve
- Transaction: commit, rollback, savepoints
- Dialect & SQL formatting: `LIMIT`/`OFFSET`, `RETURNING`, ...
- Error handling mapping
- Expression formatting integration tests

## Release Readiness

1. Comprehensive backend test suite
2. Pass the official `rhosocial-activerecord-testsuite`
3. CI pipeline across Python versions (see `.github/workflows/` in the main project)

## Checklist

Required implementation: all `StorageBackend` abstract methods; config class; SQL dialect; full
type adaptation system (adapters + registration + suggestions); transaction management; error
handling; feature detection/capabilities; async functional equivalence if providing async.
Required tests: everything in Testing Requirements. Release: tests green, testsuite compliant, CI set up.