---
name: dev-protocol-design
description: Protocol-based design guide for rhosocial-activerecord contributors - defining Protocols, runtime_checkable patterns, feature detection, and backend abstraction patterns
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
  audience: developers
  order: 7
  prerequisites:
    - dev-backend-development
    - dev-expression-dialect
---

# Protocol-Based Design Guide

This guide covers protocol-based design patterns for rhosocial-activerecord framework development, including Protocol definitions, runtime checking, feature detection, and backend abstraction patterns.

## Introduction to Protocols

Protocols enable structural subtyping in Python, allowing you to define interfaces without explicit inheritance. This is essential for the rhosocial-activerecord architecture.

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsTransaction(Protocol):
    """Protocol for transaction support."""
    
    def begin_transaction(self) -> None: ...
    
    def commit(self) -> None: ...
    
    def rollback(self) -> None: ...
```

## Core Protocols (Where They Live)

Protocol definitions are **authoritative in the source code** — do not duplicate them here. When
implementing or extending a protocol, **read the actual definition** at these locations:

| Protocol area | Location | Examples |
|---------------|----------|----------|
| SQL dialect feature protocols | `src/rhosocial/activerecord/backend/dialect/protocols.py` | `CTESupport`, `WindowFunctionSupport`, `JoinSupport`, `ReturningSupport`, `UpsertSupport`, `MergeSupport`, `GraphSupport`, `ArraySupport`, `JSONSupport`, ... (all `@runtime_checkable` `Support` protocols) |
| Backend / query access protocols | `src/rhosocial/activerecord/interface/query.py` | `IBackend`, `IAsyncBackend`, `IQueryBuilding` |
| Model interface | `src/rhosocial/activerecord/interface/model.py` | `IActiveRecord`, `IAsyncActiveRecord` |
| Base interfaces | `src/rhosocial/activerecord/interface/base.py` | backend/transaction base protocols |

The dialect protocols are **the primary feature-detection surface** — dozens of
`XxxSupport` protocols, each with a `supports_xxx()` method. The complete, up-to-date list is in
`backend/dialect/protocols.py`; **always check that file** rather than relying on any table in
this guide or other docs (the `dev-expression-dialect` skill lists them for quick reference, but
the source file is the source of truth).

**Conventions for these protocols:**
- All are `@runtime_checkable` `Protocol` classes
- Feature protocols expose a `supports_*() -> bool` method (feature detection)
- Formatting protocols expose `format_*()` methods (SQL generation)
- Backend/query access protocols expose accessor methods (e.g. `backend()`) and are mixed into
  ABC query/model classes

## Feature Detection Pattern

### Using Protocols for Conditional Feature Detection

Conceptual illustration — the real `with_cte`/`with_recursive_cte` are implemented in
`query/cte_query.py` (CTEQuery), and feature gates use `TypeError` (no `NotSupportedError`
class exists in the core):

```python
from typing import TYPE_CHECKING, Optional
from ..expression.bases import SQLExpression

if TYPE_CHECKING:
    from ...backend.base import StorageBackend


class CTEQuery:
    """ActiveRecord CTE query builder."""
    
    def __init__(self, model_class, backend=None):
        self.model_class = model_class
        self.backend = backend or model_class.__backend__
    
    def with_cte(
        self,
        name: str,
        cte_query: 'CTEQuery'
    ) -> 'CTEQuery':
        """Add CTE using protocol detection."""
        from ..dialect.protocols import CTESupport
        
        # Check if backend supports CTEs
        if not isinstance(self.backend.dialect, CTESupport):
            raise TypeError(
                f"Backend {type(self.backend).__name__} doesn't support CTEs"
            )
        
        if not self.backend.dialect.supports_cte():
            raise TypeError("CTEs are not supported")
        
        # Add CTE to query
        self._ctes.append((name, cte_query))
        return self
    
    def with_recursive_cte(
        self,
        name: str,
        base_query: 'CTEQuery',
        recursive_query: 'CTEQuery'
    ) -> 'CTEQuery':
        """Add recursive CTE."""
        from ..dialect.protocols import CTESupport
        
        if not isinstance(self.backend.dialect, CTESupport):
            raise TypeError(
                f"Backend {type(self.backend).__name__} doesn't support CTEs"
            )
        
        if not self.backend.dialect.supports_recursive_cte():
            raise TypeError("Recursive CTEs are not supported")
        
        self._recursive_cte = (name, base_query, recursive_query)
        return self
```
### Protocol-Based Validation

Conceptual example (no such `validators.py` in the core — adapt the pattern to the real
`interface/` layer):

```python
from typing import Protocol, runtime_checkable, TypeVar, Type


T = TypeVar('T', bound='ValidatableBackend')


@runtime_checkable
class ValidatableBackend(Protocol):
    """Protocol for backend validation."""
    
    @property
    def dialect(self) -> 'SQLDialect':
        """Get the dialect."""
        ...
    
    def validate(self) -> bool:
        """Validate backend configuration."""
        ...


def validate_backend(backend: T) -> T:
    """Validate a backend before use."""
    if not isinstance(backend, ValidatableBackend):
        raise TypeError(
            f"Backend must implement ValidatableProtocol, "
            f"got {type(backend).__name__}"
        )
    
    if not backend.validate():
        raise ValueError(f"Backend validation failed: {backend}")
    
    return backend
```

### Decorator-Based Protocol Checking

The **`requires_protocol`** decorator exists in the **testsuite** package
(`rhosocial.activerecord.testsuite.utils.common`), applied to tests via a pytest marker;
the runtime check is done by the testsuite's `check_protocol_requirements` fixture in
`conftest.py`:

```python
from rhosocial.activerecord.testsuite.utils import requires_protocol
from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport

# Protocol-level requirement
@requires_protocol(WindowFunctionSupport)
def test_window_functions(fixtures):
    pass

# Specific-method requirement
@requires_protocol(WindowFunctionSupport, 'supports_window_functions')
def test_window_functions(fixtures):
    pass
```

The `requires_functions(*names)` marker checks dialect `supports_functions()` support the same
way. Use these markers (not hand-rolled decorators) for tests that need a backend feature.

## Backend Abstraction Examples

### Abstract Base with Protocol

```python
# src/rhosocial/activerecord/backend/base/base.py
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, Any, List, Optional, Tuple
from ..expression.bases import SQLQueryAndParams


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backend."""
    
    @property
    def dialect(self) -> 'SQLDialect':
        """Get the dialect."""
        ...
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL."""
        ...


class AbstractStorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @property
    @abstractmethod
    def dialect(self) -> 'SQLDialect':
        """Get the dialect."""
        ...
    
    @abstractmethod
    def connect(self) -> None:
        """Connect to database."""
        ...
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from database."""
        ...
    
    @abstractmethod
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL query."""
        ...
```

### SQLite Backend Implementation

Conceptual illustration of a concrete backend implementing the protocols (the real SQLite
backend lives in `backend/impl/sqlite/backend/` as a package — `sync.py`, `async_backend.py`,
`common.py` — and composes `StorageBackend` from `backend/base/`):

```python
import sqlite3
from typing import Any, List, Optional, Tuple, Type
from ...base import StorageBackend as BaseStorageBackend
from ..dialect import SQLiteDialect


class SQLiteBackend(BaseStorageBackend):
    """SQLite storage backend implementation."""
    
    _connection: Optional[sqlite3.Connection] = None
    _dialect: Optional[SQLiteDialect] = None
    
    def __init__(self, database: str = ":memory:"):
        """Initialize SQLite backend."""
        self.database = database
    
    @property
    def dialect(self) -> SQLiteDialect:
        """Get SQLite dialect."""
        if self._dialect is None:
            self._dialect = SQLiteDialect()
        return self._dialect
    
    def connect(self) -> None:
        """Establish SQLite connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.database)
    
    def disconnect(self) -> None:
        """Close SQLite connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL query."""
        if self._connection is None:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        if sql.strip().upper().startswith("SELECT"):
            return cursor.fetchall()
        else:
            self._connection.commit()
            return cursor.rowcount
    
    def execute_many(
        self,
        sql: str,
        params_list: List[Tuple] = None
    ) -> List[Any]:
        """Execute SQL with multiple parameter sets."""
        if self._connection is None:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        results = []
        
        for params in params_list:
            cursor.execute(sql, params)
            results.append(cursor.fetchall())
        
        return results
    
    def executemany(
        self,
        sql: str,
        params_list: List[Tuple]
    ) -> None:
        """Execute SQL with many parameter sets (batch)."""
        if self._connection is None:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        cursor.executemany(sql, params_list)
        self._connection.commit()
```

## Async Protocol Definition

Async variants mirror the sync protocols 1:1 — same structure, same feature surface, with
`async def` methods. The authoritative async interfaces live in `interface/` (e.g.
`IAsyncBackend`, `IAsyncActiveRecord`, `IAsyncQuery`); **read those files** rather than copying
a protocol listing here. See the `dev-sync-async-parity` skill for the equivalence rules.

```python
# Conceptual shape only — the async protocol's I/O-bound methods are async.
async def connect(self) -> None: ...
async def disconnect(self) -> None: ...
async def execute(self, sql, params=None) -> Any: ...
```

## Protocol Composition

### Composing Multiple Protocols

Conceptual example of composing protocols to describe a combined capability (the async SQLite
backend is real at `backend/impl/sqlite/backend/async_backend.py`, but the exact classes below
are illustrative):

```python
from typing import Protocol, runtime_checkable, Any, List, Optional, Tuple
from ....backend.dialect.protocols import CTESupport, WindowFunctionSupport


@runtime_checkable
class AsyncSQLiteBackendProtocol(
    CTESupport,
    WindowFunctionSupport,
    Protocol
):
    """Combined protocol for SQLite async backend."""
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL query."""
        ...


class AsyncSQLiteBackend:
    """Async SQLite backend implementation."""
    
    def __init__(self, database: str = ":memory:"):
        """Initialize async SQLite backend."""
        self.sync_backend = SQLiteBackend(database)
    
    @property
    def dialect(self):
        """Get dialect."""
        return self.sync_backend.dialect
    
    async def connect(self) -> None:
        """Establish connection."""
        self.sync_backend.connect()
    
    async def disconnect(self) -> None:
        """Close connection."""
        self.sync_backend.disconnect()
    
    async def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL query asynchronously."""
        return self.sync_backend.execute(sql, params)
    
    # Protocol implementations
    def supports_cte(self) -> bool:
        """Check CTE support."""
        return True
    
    def supports_window_functions(self) -> bool:
        """Check window function support."""
        return True
```

## Testing with Protocols

### Protocol Verification in Tests

```python
# Conceptual test — verify a backend/dialect satisfies the required protocols via isinstance()
import pytest
from typing import Type


def test_sqlite_backend_protocol():
    """Test SQLite backend implements required protocols."""
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.dialect.protocols import CTESupport
    
    backend = SQLiteBackend(":memory:")
    
    # Check dialect supports CTEs via the feature protocol
    assert isinstance(backend.dialect, CTESupport)
    assert backend.dialect.supports_cte() is True
```

### Protocol-Based Feature Detection in Tests

Conceptual fixture pattern for feature gating (the testsuite prefers the `@requires_protocol`
marker, which handles skipping centrally — see above):

```python
import pytest


@pytest.fixture
def supports_ctes(backend) -> bool:
    """Check if backend supports CTEs."""
    from rhosocial.activerecord.backend.dialect.protocols import CTESupport
    return isinstance(backend.dialect, CTESupport)


# Usage in tests
class TestCTEQueries:
    """Test CTE functionality."""
    
    def test_basic_cte(self, backend, supports_ctes):
        """Test basic CTE query."""
        if not supports_ctes:
            pytest.skip("Backend doesn't support CTEs")
        
        # CTE test implementation
        ...
    
    def test_recursive_cte(self, backend, supports_ctes):
        """Test recursive CTE query."""
        from rhosocial.activerecord.backend.dialect.protocols import CTESupport
        
        if not isinstance(backend.dialect, CTESupport):
            pytest.skip("Backend doesn't support CTEs")
        
        if not backend.dialect.supports_recursive_cte():
            pytest.skip("Backend doesn't support recursive CTEs")
        
        # Recursive CTE test implementation
        ...
```

## Best Practices

1. **Define protocols for all public interfaces**
2. **Use `@runtime_checkable` for runtime type checking**
3. **Keep protocols focused** - one protocol per responsibility
4. **Use protocol composition** for complex backends
5. **Test protocol implementations** with `isinstance()` checks
6. **Use protocols for feature detection** in conditional code
7. **Document protocol requirements** for backend implementations
8. **Follow the Expression-Dialect separation** - protocols define interface, implementations provide behavior

## Protocol Checklist

- [ ] Define Protocol for each backend feature
- [ ] Use `@runtime_checkable` decorator
- [ ] Include all required methods in Protocol
- [ ] Use type hints for all method signatures
- [ ] Test protocol implementations with isinstance()
- [ ] Document protocol requirements
- [ ] Use protocols for feature detection in code
- [ ] Create async versions of sync protocols
