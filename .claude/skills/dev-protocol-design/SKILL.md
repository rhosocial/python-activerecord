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

## Core Protocols

### Storage Backend Protocol

The base protocol for all storage backends.

```python
# src/rhosocial/activerecord/backend/base/protocols.py
from typing import Protocol, runtime_checkable, Any, List, Optional, Tuple
from ..expression.bases import SQLQueryAndParams


@runtime_checkable
class StorageBackendProtocol(Protocol):
    """Protocol that all storage backends must implement."""
    
    @property
    def dialect(self) -> 'SQLDialectProtocol':
        """Get the SQL dialect for this backend."""
        ...
    
    def connect(self) -> None:
        """Establish database connection."""
        ...
    
    def disconnect(self) -> None:
        """Close database connection."""
        ...
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False
    ) -> Any:
        """Execute a SQL query."""
        ...
    
    def execute_many(
        self,
        sql: str,
        params_list: List[Tuple] = None
    ) -> List[Any]:
        """Execute the same SQL with multiple parameter sets."""
        ...


@runtime_checkable
class AsyncStorageBackendProtocol(Protocol):
    """Protocol for async storage backends."""
    
    @property
    def dialect(self) -> 'SQLDialectProtocol':
        """Get the SQL dialect for this backend."""
        ...
    
    async def connect(self) -> None:
        """Establish database connection asynchronously."""
        ...
    
    async def disconnect(self) -> None:
        """Close database connection asynchronously."""
        ...
    
    async def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False
    ) -> Any:
        """Execute a SQL query asynchronously."""
        ...
    
    async def execute_many(
        self,
        sql: str,
        params_list: List[Tuple] = None
    ) -> List[Any]:
        """Execute the same SQL with multiple parameter sets asynchronously."""
        ...
```

### SQL Dialect Protocol

Protocol for SQL dialect implementations.

```python
# src/rhosocial/activerecord/backend/dialect/protocols.py
from typing import Protocol, runtime_checkable, List, Optional, Tuple
from ..expression.bases import SQLQueryAndParams


@runtime_checkable
class SQLDialectProtocol(Protocol):
    """Protocol for SQL dialect implementations."""
    
    def format_identifier(self, identifier: str) -> str:
        """Format a SQL identifier with proper quoting."""
        ...
    
    def format_string_literal(self, value: str) -> str:
        """Format a string literal for SQL."""
        ...
    
    def format_column_reference(
        self,
        table: Optional[str],
        column: str
    ) -> str:
        """Format a column reference for SQL."""
        ...
    
    def supports_returning_clause(self) -> bool:
        """Check if RETURNING clause is supported."""
        ...
    
    def supports_window_functions(self) -> bool:
        """Check if window functions are supported."""
        ...
    
    def supports_cte(self) -> bool:
        """Check if CTEs are supported."""
        ...
    
    def supports_recursive_cte(self) -> bool:
        """Check if recursive CTEs are supported."""
        ...
    
    def supports_transactions(self) -> bool:
        """Check if transactions are supported."""
        ...
    
    def supports_foreign_keys(self) -> bool:
        """Check if foreign keys are supported."""
        ...
    
    def supports_indexed_by(self) -> bool:
        """Check if INDEXED BY is supported."""
        ...
    
    def supports_auto_increment(self) -> bool:
        """Check if AUTOINCREMENT is supported."""
        ...
    
    def supports_default_values(self) -> bool:
        """Check if DEFAULT values are supported."""
        ...
    
    def supports_is_null(self) -> bool:
        """Check if IS NULL is supported."""
        ...
    
    def supports_like(self) -> bool:
        """Check if LIKE operator is supported."""
        ...
    
    def supports_ilike(self) -> bool:
        """Check if ILIKE (case-insensitive LIKE) is supported."""
        ...
    
    def supports_between(self) -> bool:
        """Check if BETWEEN operator is supported."""
        ...
    
    def supports_in_clause(self) -> bool:
        """Check if IN clause is supported."""
        ...
    
    def supports_exists(self) -> bool:
        """Check if EXISTS subquery is supported."""
        ...
    
    def supports_subqueries(self) -> bool:
        """Check if subqueries are supported."""
        ...
    
    def supports_join(self) -> bool:
        """Check if JOINs are supported."""
        ...
    
    def supports_left_join(self) -> bool:
        """Check if LEFT JOIN is supported."""
        ...
    
    def supports_right_join(self) -> bool:
        """Check if RIGHT JOIN is supported."""
        ...
    
    def supports_inner_join(self) -> bool:
        """Check if INNER JOIN is supported."""
        ...
    
    def supports_outer_join(self) -> bool:
        """Check if OUTER JOIN is supported."""
        ...
    
    def supports_cross_join(self) -> bool:
        """Check if CROSS JOIN is supported."""
        ...
    
    def supports_distinct(self) -> bool:
        """Check if DISTINCT is supported."""
        ...
    
    def supports_group_by(self) -> bool:
        """Check if GROUP BY is supported."""
        ...
    
    def supports_having(self) -> bool:
        """Check if HAVING is supported."""
        ...
    
    def supports_order_by(self) -> bool:
        """Check if ORDER BY is supported."""
        ...
    
    def supports_limit(self) -> bool:
        """Check if LIMIT is supported."""
        ...
    
    def supports_offset(self) -> bool:
        """Check if OFFSET is supported."""
        ...
    
    def supports_union(self) -> bool:
        """Check if UNION is supported."""
        ...
    
    def supports_union_all(self) -> bool:
        """Check if UNION ALL is supported."""
        ...
    
    def supports_intersect(self) -> bool:
        """Check if INTERSECT is supported."""
        ...
    
    def supports_except(self) -> bool:
        """Check if EXCEPT is supported."""
        ...
    
    def supports_case(self) -> bool:
        """Check if CASE expression is supported."""
        ...
    
    def supports_case_when(self) -> bool:
        """Check if CASE WHEN expression is supported."""
        ...
    
    def supports_coalesce(self) -> bool:
        """Check if COALESCE function is supported."""
        ...
    
    def supports_nullif(self) -> bool:
        """Check if NULLIF function is supported."""
        ...
    
    def supports_concat(self) -> bool:
        """Check if CONCAT function is supported."""
        ...
    
    def supports_substring(self) -> bool:
        """Check if SUBSTRING function is supported."""
        ...
    
    def supports_length(self) -> bool:
        """Check if LENGTH function is supported."""
        ...
    
    def supports_upper(self) -> bool:
        """Check if UPPER function is supported."""
        ...
    
    def supports_lower(self) -> bool:
        """Check if LOWER function is supported."""
        ...
    
    def supports_trim(self) -> bool:
        """Check if TRIM function is supported."""
        ...
    
    def supports_replace(self) -> bool:
        """Check if REPLACE function is supported."""
        ...
    
    def supports_date_functions(self) -> bool:
        """Check if date functions are supported."""
        ...
    
    def supports_datetime_functions(self) -> bool:
        """Check if datetime functions are supported."""
        ...
    
    def supports_extract(self) -> bool:
        """Check if EXTRACT function is supported."""
        ...
    
    def supports_date_trunc(self) -> bool:
        """Check if DATE_TRUNC function is supported."""
        ...
    
    def supports_date_add(self) -> bool:
        """Check if DATE_ADD function is supported."""
        ...
    
    def supports_date_diff(self) -> bool:
        """Check if DATE_DIFF function is supported."""
        ...
    
    def supports_aggregate_functions(self) -> bool:
        """Check if aggregate functions are supported."""
        ...
    
    def supports_count(self) -> bool:
        """Check if COUNT function is supported."""
        ...
    
    def supports_sum(self) -> bool:
        """Check if SUM function is supported."""
        ...
    
    def supports_avg(self) -> bool:
        """Check if AVG function is supported."""
        ...
    
    def supports_min(self) -> bool:
        """Check if MIN function is supported."""
        ...
    
    def supports_max(self) -> bool:
        """Check if MAX function is supported."""
        ...
    
    def supports_first(self) -> bool:
        """Check if FIRST function is supported."""
        ...
    
    def supports_last(self) -> bool:
        """Check if LAST function is supported."""
        ...
    
    def supports_stddev(self) -> bool:
        """Check if STDDEV function is supported."""
        ...
    
    def supports_variance(self) -> bool:
        """Check if VARIANCE function is supported."""
        ...
    
    def supports_round(self) -> bool:
        """Check if ROUND function is supported."""
        ...
    
    def supports_floor(self) -> bool:
        """Check if FLOOR function is supported."""
        ...
    
    def supports_ceil(self) -> bool:
        """Check if CEILING function is supported."""
        ...
    
    def supports_abs(self) -> bool:
        """Check if ABS function is supported."""
        ...
    
    def supports_power(self) -> bool:
        """Check if POWER function is supported."""
        ...
    
    def supports_sqrt(self) -> bool:
        """Check if SQRT function is supported."""
        ...
    
    def supports_mod(self) -> bool:
        """Check if MOD function is supported."""
        ...
    
    def supports_cast(self) -> bool:
        """Check if CAST expression is supported."""
        ...
    
    def supports_type_cast(self) -> bool:
        """Check if type casting is supported."""
        ...
```

### Query Protocol

Protocol for query builders.

```python
# src/rhosocial/activerecord/query/protocols.py
from typing import Protocol, runtime_checkable, List, Optional, Any
from ..expression.bases import SQLExpression


@runtime_checkable
class QueryProtocol(Protocol):
    """Protocol for query builders."""
    
    def where(
        self,
        condition: SQLExpression
    ) -> 'QueryProtocol':
        """Add WHERE clause."""
        ...
    
    def and_(
        self,
        condition: SQLExpression
    ) -> 'QueryProtocol':
        """Add AND condition."""
        ...
    
    def or_(
        self,
        condition: SQLExpression
    ) -> 'QueryProtocol':
        """Add OR condition."""
        ...
    
    def order_by(
        self,
        *columns: SQLExpression,
        ascending: bool = True
    ) -> 'QueryProtocol':
        """Add ORDER BY clause."""
        ...
    
    def group_by(
        self,
        *columns: SQLExpression
    ) -> 'QueryProtocol':
        """Add GROUP BY clause."""
        ...
    
    def having(
        self,
        condition: SQLExpression
    ) -> 'QueryProtocol':
        """Add HAVING clause."""
        ...
    
    def limit(self, count: int) -> 'QueryProtocol':
        """Add LIMIT clause."""
        ...
    
    def offset(self, count: int) -> 'QueryProtocol':
        """Add OFFSET clause."""
        ...
    
    def select(self, *columns: str) -> 'QueryProtocol':
        """Select specific columns."""
        ...
    
    def distinct(self) -> 'QueryProtocol':
        """Add DISTINCT clause."""
        ...
    
    def all(self) -> List[Any]:
        """Execute query and return all results."""
        ...
    
    def first(self) -> Optional[Any]:
        """Execute query and return first result."""
        ...
    
    def count(self) -> int:
        """Return count of matching records."""
        ...
    
    def exists(self) -> bool:
        """Check if any records match."""
        ...
    
    def delete(self) -> int:
        """Delete matching records."""
        ...
    
    def update(self, **kwargs) -> int:
        """Update matching records."""
        ...
    
    def to_sql(self) -> str:
        """Get SQL query string."""
        ...
    
    def compile(self) -> SQLExpression:
        """Compile to SQL expression."""
        ...
```

## Feature Detection Pattern

### Using Protocols for Conditional Feature Detection

```python
# src/rhosocial/activerecord/query/active_query.py
from typing import TYPE_CHECKING, Optional
from ..expression.bases import SQLExpression

if TYPE_CHECKING:
    from ...backend.base import StorageBackend


class ActiveQuery:
    """ActiveRecord query builder."""
    
    def __init__(self, model_class, backend=None):
        self.model_class = model_class
        self.backend = backend or model_class.__backend__
    
    def with_cte(
        self,
        name: str,
        cte_query: 'ActiveQuery'
    ) -> 'ActiveQuery':
        """Add CTE using protocol detection."""
        from ..dialect.protocols import CTESupport
        
        # Check if backend supports CTEs
        if not isinstance(self.backend.dialect, CTESupport):
            raise NotSupportedError(
                f"Backend {type(self.backend).__name__} doesn't support CTEs"
            )
        
        if not self.backend.dialect.supports_cte():
            raise NotSupportedError("CTEs are not supported")
        
        # Add CTE to query
        self._ctes.append((name, cte_query))
        return self
    
    def with_recursive_cte(
        self,
        name: str,
        base_query: 'ActiveQuery',
        recursive_query: 'ActiveQuery'
    ) -> 'ActiveQuery':
        """Add recursive CTE."""
        from ..dialect.protocols import CTESupport
        
        if not isinstance(self.backend.dialect, CTESupport):
            raise NotSupportedError(
                f"Backend {type(self.backend).__name__} doesn't support CTEs"
            )
        
        if not self.backend.dialect.supports_recursive_cte():
            raise NotSupportedError("Recursive CTEs are not supported")
        
        self._recursive_cte = (name, base_query, recursive_query)
        return self
```

### Protocol-Based Validation

```python
# src/rhosocial/activerecord/backend/base/validators.py
from typing import Protocol, runtime_checkable, TypeVar, Type


T = TypeVar('T', bound='ValidatableBackend')


@runtime_checkable
class ValidatableBackend(Protocol):
    """Protocol for backend validation."""
    
    @property
    def dialect(self) -> 'SQLDialectProtocol':
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


# Usage
backend = SQLiteBackend("sqlite:///app.db")
validate_backend(backend)
backend.connect()
```

### Decorator-Based Protocol Checking

```python
# src/rhosocial/activerecord/backend/base/decorators.py
from functools import wraps
from typing import Protocol, runtime_checkable, TypeVar, Callable, Any


F = TypeVar('F', bound=Callable[..., Any])


def requires_protocol(
    protocol_class: Type[Protocol],
    feature_name: str
) -> Callable[[F], F]:
    """Decorator to require a protocol for a method."""
    
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            if not isinstance(self, protocol_class):
                raise NotImplementedError(
                    f"{self.__class__.__name__} doesn't implement "
                    f"{protocol_class.__name__} required for {feature_name}"
                )
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


# Usage
class StorageBackend:
    """Base storage backend."""
    
    @requires_protocol(CTESupport, 'CTE support')
    def with_cte(self, name: str, query):
        """Add CTE to query."""
        ...
```

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
    def dialect(self) -> 'SQLDialectProtocol':
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
    def dialect(self) -> 'SQLDialectProtocol':
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

```python
# src/rhosocial/activerecord/backend/impl/sqlite/backend.py
import sqlite3
from typing import Any, List, Optional, Tuple, Type
from ...base import StorageBackend as BaseStorageBackend
from ...base.protocols import (
    StorageBackendProtocol,
    AsyncStorageBackendProtocol,
)
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

```python
# src/rhosocial/activerecord/backend/base/async_protocols.py
from typing import Protocol, runtime_checkable, Any, List, Optional, Tuple
from ..expression.bases import SQLQueryAndParams


@runtime_checkable
class AsyncStorageBackendProtocol(Protocol):
    """Protocol for async storage backends."""
    
    @property
    def dialect(self) -> 'SQLDialectProtocol':
        """Get the SQL dialect."""
        ...
    
    async def connect(self) -> None:
        """Establish database connection asynchronously."""
        ...
    
    async def disconnect(self) -> None:
        """Close database connection asynchronously."""
        ...
    
    async def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL query asynchronously."""
        ...
    
    async def execute_many(
        self,
        sql: str,
        params_list: List[Tuple] = None
    ) -> List[Any]:
        """Execute SQL with multiple parameter sets asynchronously."""
        ...
    
    async def begin_transaction(self) -> None:
        """Begin transaction asynchronously."""
        ...
    
    async def commit(self) -> None:
        """Commit transaction asynchronously."""
        ...
    
    async def rollback(self) -> None:
        """Rollback transaction asynchronously."""
        ...
```

## Protocol Composition

### Composing Multiple Protocols

```python
# src/rhosocial/activerecord/backend/impl/sqlite/async_backend.py
from typing import Protocol, runtime_checkable, Any, List, Optional, Tuple
from ....backend.base.async_protocols import AsyncStorageBackendProtocol
from ....backend.dialect.protocols import CTESupport, WindowFunctionSupport
from ..backend import SQLiteBackend


@runtime_checkable
class AsyncSQLiteBackendProtocol(
    AsyncStorageBackendProtocol,
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
# tests/test_protocols.py
import pytest
from typing import Type


def test_sqlite_backend_protocol():
    """Test SQLite backend implements required protocols."""
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.base.protocols import (
        StorageBackendProtocol,
    )
    from rhosocial.activerecord.backend.dialect.protocols import (
        SQLDialectProtocol,
        CTESupport,
    )
    
    backend = SQLiteBackend(":memory:")
    
    # Check backend implements StorageBackendProtocol
    assert isinstance(backend, StorageBackendProtocol)
    
    # Check dialect implements SQLDialectProtocol
    assert isinstance(backend.dialect, SQLDialectProtocol)
    
    # Check dialect supports CTEs
    assert isinstance(backend.dialect, CTESupport)
    assert backend.dialect.supports_cte() is True


def test_async_backend_protocol():
    """Test async backend implements required protocols."""
    from rhosocial.activerecord.backend.impl.sqlite import (
        AsyncSQLiteBackend,
    )
    from rhosocial.activerecord.backend.base.async_protocols import (
        AsyncStorageBackendProtocol,
    )
    
    backend = AsyncSQLiteBackend(":memory:")
    
    # Check async backend implements AsyncStorageBackendProtocol
    assert isinstance(backend, AsyncStorageBackendProtocol)
```

### Protocol-Based Feature Detection in Tests

```python
# tests/conftest.py
import pytest
from typing import Type


@pytest.fixture
def supports_ctes(backend) -> bool:
    """Check if backend supports CTEs."""
    from rhosocial.activerecord.backend.dialect.protocols import (
        CTESupport,
    )
    return isinstance(backend.dialect, CTESupport)


@pytest.fixture
def supports_window_functions(backend) -> bool:
    """Check if backend supports window functions."""
    from rhosocial.activerecord.backend.dialect.protocols import (
        WindowFunctionSupport,
    )
    return isinstance(backend.dialect, WindowFunctionSupport)


@pytest.fixture
def supports_transactions(backend) -> bool:
    """Check if backend supports transactions."""
    from rhosocial.activerecord.backend.dialect.protocols import (
        TransactionSupport,
    )
    return isinstance(backend.dialect, TransactionSupport)


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
        from rhosocial.activerecord.backend.dialect.protocols import (
            CTESupport,
        )
        
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
