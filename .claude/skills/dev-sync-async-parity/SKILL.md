---
name: dev-sync-async-parity
description: Sync/async API parity rules for rhosocial-activerecord contributors - backend/transaction symmetry, naming conventions, docstrings, field ordering, and testing parity
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: intermediate
  audience: developers
  order: 2
  prerequisites:
    - dev-backend-development
---

# Sync/Async API Parity Rules

This guide covers the strict sync/async parity requirements for rhosocial-activerecord
framework development, with emphasis on **backend and transaction symmetry** as the foundation
of all parity.

## Core Philosophy

### Backend & Transaction: The True Foundation

**Backend and Transaction are the real foundation of sync/async equivalence.**

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│     ActiveRecord / AsyncActiveRecord (depends on Backend)     │
│     ActiveQuery / AsyncActiveQuery (depends on Backend)       │
├─────────────────────────────────────────────────────────────┤
│                    Backend Layer                             │
│     StorageBackend / AsyncStorageBackend (core parity)        │
│     Transaction / AsyncTransaction (core parity)              │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                            │
│            SQLite / PostgreSQL / MySQL / etc.               │
└─────────────────────────────────────────────────────────────┘
```

**Key insight:**
- `ActiveRecord` depends on `StorageBackend`
- `AsyncActiveRecord` depends on `AsyncStorageBackend`
- Without an async `StorageBackend`, `AsyncActiveRecord` cannot truly work
- **Backend/Transaction parity is the prerequisite for the whole framework's sync/async parity**

## Backend Implementation Status

### Current Status

**Not every backend must ship both sync and async variants.** The async SQLite backend is
already **implemented in the production source**; a separate test-only async backend also exists
for validating the async abstraction.

| Location | Sync implementation | Async implementation | Purpose |
|----------|---------------------|----------------------|---------|
| `src/rhosocial/activerecord/backend/impl/sqlite/` | ✅ `SQLiteBackend` (`backend/sync.py`) | ✅ `AsyncSQLiteBackend` (`backend/async_backend.py`) | Production |
| `tests/rhosocial/activerecord_test/feature/backend/sqlite_async/` | — | ✅ test-only async backend (aiosqlite) | Testing only |

```python
# Production sync backend
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class SQLiteBackend(StorageBackend):
    def connect(self): ...
    def execute(self, sql: str, params=None): ...

# Production async backend (backend/impl/sqlite/backend/async_backend.py)
class AsyncSQLiteBackend(AsyncStorageBackend):
    async def connect(self): ...
    async def execute(self, sql: str, params=None): ...

# Test-only async backend (tests/.../backend/sqlite_async/async_backend.py)
# Validates the async abstraction with aiosqlite; NOT for production use.
class AsyncSQLiteBackend(AsyncStorageBackend):
    async def execute(self, sql: str, params=None): ...
```

### When an Async Backend May Not Be Needed

Async support follows the **driver's native capabilities** — respect whichever variant the
backend genuinely provides (see Q1/Q2). Reasons an async backend may be absent:

1. **No native async driver**: the database driver is synchronous-only (e.g. Firebird), and we do
   not force an artificial async wrapper
2. **Pure-sync use cases**: many applications do not need async database access
3. **Community contribution**: async support can be added on demand when a driver enables it

## The Two Parity Chains

### Chain 1: Backend Layer (core)

```
StorageBackend (sync foundation)
    ↓ dependency
BaseActiveRecord / ActiveQuery (sync API)

AsyncStorageBackend (async foundation)
    ↓ dependency
AsyncBaseActiveRecord / AsyncActiveQuery (async API)
```

### Chain 2: Transaction Layer

```
Transaction (sync transactions)
    ↓ provides transaction support
BaseActiveRecord.save() / BaseActiveRecord.delete()

AsyncTransaction (async transactions)
    ↓ provides transaction support
AsyncBaseActiveRecord.save() / AsyncBaseActiveRecord.delete()
```

## Six Core Rules

### Rule 1: Class Naming

Every layer on the parity chain adds an `Async` prefix:

```python
# Backend layer
StorageBackend → AsyncStorageBackend

# Transaction layer
Transaction → AsyncTransaction

# ActiveRecord layer
BaseActiveRecord → AsyncBaseActiveRecord

# Query layer
ActiveQuery → AsyncActiveQuery
RelationQuery → AsyncRelationQuery
```

### Rule 2: Method Naming (critical)

**Method names must be identical** — the `_async` suffix is forbidden:

```python
# ✅ Correct - same method names
class StorageBackend:
    def execute(self, sql: str, params=None): ...

class AsyncStorageBackend:
    async def execute(self, sql: str, params=None): ...

# ✅ Correct - transaction methods
class Transaction:
    def commit(self): ...

class AsyncTransaction:
    async def commit(self): ...

# ❌ Wrong - _async suffix is forbidden
class AsyncStorageBackend:
    async def execute_async(self, sql: str, params=None): ...
```

### Rule 3: Docstring Requirements

The first sentence of the async version must contain "asynchronously":

```python
class StorageBackend:
    def execute(self, sql: str, params=None):
        """Execute a SQL query."""
        ...

class AsyncStorageBackend:
    async def execute(self, sql: str, params=None):
        """Execute a SQL query asynchronously."""
        ...

class Transaction:
    def commit(self):
        """Commit the current transaction."""
        ...

class AsyncTransaction:
    async def commit(self):
        """Commit the current transaction asynchronously."""
        ...
```

### Rule 4: Field/Property Declaration Order

The sync and async versions must declare attributes in exactly the same order:

```python
# StorageBackend attribute order
class StorageBackend:
    _connection: Optional[Connection]
    _dialect: Optional[SQLDialect]
    _transaction: Optional[Transaction]
    
    @property
    def dialect(self): ...

# AsyncStorageBackend must keep the same order
class AsyncStorageBackend:
    _connection: Optional[AsyncConnection]
    _dialect: Optional[SQLDialect]
    _transaction: Optional[AsyncTransaction]
    
    @property
    def dialect(self): ...  # same order
```

### Rule 5: Functional Parity

If the sync version has a feature, the async version must provide the corresponding feature:

```python
# ✅ Correct - functional parity
class StorageBackend:
    def execute(self, sql: str, params=None): ...
    def execute_many(self, sql: str, params_list): ...
    def begin_transaction(self): ...
    def commit(self): ...
    def rollback(self): ...

class AsyncStorageBackend:
    async def execute(self, sql: str, params=None): ...
    async def execute_many(self, sql: str, params_list): ...
    async def begin_transaction(self): ...
    async def commit(self): ...
    async def rollback(self): ...

# ❌ Wrong - missing functionality
class AsyncStorageBackend:
    async def execute(self, sql: str, params=None): ...
    # missing execute_many and transaction methods
```

### Rule 6: Testing Parity

Tests must follow strict sync/async parity:

```python
# Fixture parity
@pytest.fixture
def backend(sqlite_provider): ...
@pytest.fixture
def async_backend(sqlite_provider): ...

# Test class parity
class TestBackendExecute:
    def test_execute_basic(self, backend): ...

class TestAsyncBackendExecute:
    @pytest.mark.asyncio
    async def test_execute_basic(self, async_backend): ...  # same method name

# Test method parity
class TestTransactionCommit:
    def test_commit_success(self, backend): ...
    def test_commit_failure(self, backend): ...

class TestAsyncTransactionCommit:
    @pytest.mark.asyncio
    async def test_commit_success(self, async_backend): ...  # same method name
    @pytest.mark.asyncio
    async def test_commit_failure(self, async_backend): ...  # same method name
```

## Implementing an Async Backend

### When to Implement an Async Backend?

1. **Production need**: the app uses an async/await framework (e.g. FastAPI)
2. **Performance requirements**: high-concurrency scenarios need async database access
3. **Community demand**: users explicitly need async support

### Async Backend Implementation Strategies

> Real async backends are built on the driver's **native async support**. The strategies below
> illustrate the surface an async backend must provide; prefer a native async driver over any
> synthetic wrapping (see Q2).

#### Strategy 1: Wrap the sync version

> **⚠️ Conceptual illustration only** as a mental model for what an async backend must surface to
> the application. This thread-pool wrapping approach is **not** an endorsed production pattern —
> per Q2 we respect the driver and do not fabricate async by wrapping sync in an executor. A
> production async backend should be backed by a native async driver.

```python
# backend/impl/sqlite/backend/async_backend.py (conceptual)
import asyncio
from typing import Optional, Tuple, Any


class AsyncSQLiteBackend:
    """Async SQLite backend - wraps the sync version."""
    
    def __init__(self, database: str = ":memory:"):
        """Initialize with the same parameters as the sync version."""
        self._sync_backend = SQLiteBackend(database)
        self._connected = False
    
    @property
    def dialect(self):
        """Delegate to sync dialect."""
        return self._sync_backend.dialect
    
    async def connect(self) -> None:
        """Connect asynchronously (delegates to sync)."""
        self._sync_backend.connect()
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect asynchronously."""
        self._sync_backend.disconnect()
        self._connected = False
    
    async def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL asynchronously (runs sync in a thread pool)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_backend.execute(sql, params)
        )
    
    async def begin_transaction(self) -> None:
        """Begin transaction asynchronously."""
        await self.execute("BEGIN TRANSACTION")
    
    async def commit(self) -> None:
        """Commit transaction asynchronously."""
        await self.execute("COMMIT")
    
    async def rollback(self) -> None:
        """Rollback transaction asynchronously."""
        await self.execute("ROLLBACK")
```

#### Strategy 2: Use a native async driver

```python
# backend/impl/postgres/backend/async_backend.py (conceptual)
# Uses asyncpg or another native async driver
import asyncpg


class AsyncPostgreSQLBackend:
    """Backend using a native async driver."""
    
    def __init__(self, dsn: str):
        """Initialize with connection string."""
        self._pool: Optional[asyncpg.Pool] = None
        self._dsn = dsn
    
    async def connect(self) -> None:
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(self._dsn)
    
    async def execute(self, sql: str, params=None) -> Any:
        """Execute using async connection pool."""
        async with self._pool.acquire() as conn:
            if params:
                return await conn.fetch(sql, *params)
            return await conn.fetch(sql)
```

## Verification Checklist

Use this checklist when implementing or modifying code:

### Backend Layer Verification

- [ ] Sync backend implements the `StorageBackend` protocol
- [ ] Async backend implements the `AsyncStorageBackend` protocol
- [ ] Sync/async method names are identical
- [ ] Async methods use `async def`
- [ ] Async method first sentence contains "asynchronously"
- [ ] Attribute declaration order is consistent
- [ ] Transaction methods are fully parallel

### Testing Layer Verification

- [ ] Sync tests use the `backend` fixture
- [ ] Async tests use the `async_backend` fixture
- [ ] Test class names add an `Async` prefix
- [ ] Test method names are identical
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] Shared architecture files

### Documentation Layer Verification

- [ ] Sync API documentation is complete
- [ ] Async API documentation first sentence contains "asynchronously"
- [ ] Sync/async backend availability status is documented

## FAQ

### Q1: When may I provide only a sync backend?

**Whenever the underlying driver has no native async support — that is the default, not an
exception.** Async implementation is opt-in and follows the driver:

- The driver provides no async interface (e.g. many native DB drivers are synchronous-only)
- The use case is clearly sync
- The community has not yet contributed an async implementation

No artificial async wrapper should be created for such backends (see Q2).

### Q2: Can I use the async API when a backend only has a sync implementation?

**Respect the backend's actual driver.** Async support is a property of the underlying driver,
not something to force. Use whichever variant the backend genuinely provides — and if a backend
does not have a native async driver, do **not** paper over it by wrapping the sync implementation
in asyncio plumbing to make it "async".

For example, Firebird currently ships only a sync backend (no native async driver). That is fine:
applications targeting Firebird simply use the sync API. Forcing an async wrapper there would add
blocking thread-pool machinery with no real async I/O benefit, so we deliberately do not do it.

**Policy:**
- Backends expose an async implementation **only when** their driver natively supports it.
- Use the sync variant as-is when async is unavailable; the async API is simply not offered for
  that backend.
- Do **not** create artificial async wrappers (thread-pool / executor bridges) to emulate async
  where the driver has no async support.
- A test-only async backend exists for the SQLite feature tree purely to validate the async
  abstraction in the test suite — it is not a substitute for a real async production backend.

### Q3: How do I verify the correctness of an async backend?

1. **Reuse sync tests**: write async tests based on the same logic
2. **Compare results**: ensure sync/async return the same data
3. **Test error handling**: verify async error propagation

```python
class TestAsyncBackendErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_sql_error(
        self,
        async_backend: AsyncSQLiteBackend
    ):
        """Verify async error handling matches sync."""
        with pytest.raises(SyntaxError):
            await async_backend.execute("INVALID SQL")
```

## Quick Reference

### Naming Table

| Sync | Async | Layer |
|------|-------|-------|
| `StorageBackend` | `AsyncStorageBackend` | Backend |
| `Transaction` | `AsyncTransaction` | Transaction |
| `BaseActiveRecord` | `AsyncBaseActiveRecord` | ActiveRecord |
| `ActiveQuery` | `AsyncActiveQuery` | Query |

### Import Paths

```python
# Production sync/async backends
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

# Sync/async common
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
```