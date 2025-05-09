# Design Principles

To maintain the Open-Closed Principle and decouple the backend module from specific storage backend implementations, the following adjustments are needed:

1. Module Structure:
```
backend/
    __init__.py                  # Only exports interfaces and base classes
    base.py                      # Core interfaces and class definitions
    typing.py                    # Type definitions
    dialect.py                   # Dialect-related abstract definitions
    errors.py                    # Error definitions
    helpers.py                   # Helper utilities

impl/                            # Concrete implementations package
    __init__.py 
    sqlite/                      # SQLite implementation
        __init__.py
        backend.py               # SQLite backend
        dialect.py               # SQLite dialect
        types.py                 # SQLite type mapping
    mysql/                       # MySQL implementation (distributed separately)
        __init__.py
        backend.py
        dialect.py  
        types.py
    postgresql/                  # PostgreSQL implementation (distributed separately)
        __init__.py
        backend.py
        dialect.py
        types.py
```

2. The backend package only defines interfaces and base classes, without any concrete implementation code or specific database dependencies.

3. Load concrete implementations at runtime through configuration and dynamic importing:
```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend  # If mysql package is installed

def create_backend(backend_type: str, **config) -> StorageBackend:
    """Factory function to create concrete backend instances"""
    if backend_type == 'sqlite':
        return SQLiteBackend(**config)
    elif backend_type == 'mysql':
        return MySQLBackend(**config)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")
```

4. For testing, use a separate test_implementations package for different backend test code.

Benefits of this design:

1. The backend module only depends on abstract interfaces
2. Adding database support doesn't require modifying existing code
3. Users can import database implementations as needed
4. Test code is better organized

## Details of Each Module

```python
# backend/
    # __init__.py
    """Exports public interfaces only
    from .base import StorageBackend
    from .dialect import DatabaseType, TypeMapping
    from .errors import DatabaseError, ConnectionError
    from .typing import ConnectionConfig, DatabaseValue
    """

    # base.py  
    """Core abstract base class for storage backends
    - StorageBackend ABC
    - Basic CRUD interface definitions 
    - Connection management interface
    - Transaction management interface
    Without any concrete implementation or database-specific code
    """

    # typing.py
    """Type definitions
    - Custom type aliases
    - Configuration-related data classes (ConnectionConfig, etc.)
    - Query result types (QueryResult, etc.)
    - Type mapping-related generic definitions
    """

    # dialect.py
    """SQL dialect-related abstract definitions
    - DatabaseType enum (unified type system)
    - TypeMapping interface (type mapping rules)
    - ValueMapper interface (value conversion rules) 
    Without specific database mapping implementations
    """

    # errors.py
    """Error class definitions
    - DatabaseError base class
    - ConnectionError
    - TransactionError
    - ValidationError
    And other core exception class definitions
    """

    # helpers.py
    """Common helper utilities
    - Type conversion utility functions
    - SQL building helper functions
    - Connection utility functions
    And other database-agnostic utility functions
    """
```

# Database Backend Implementation Comparison

| Feature | SQLite | MySQL | MariaDB | PostgreSQL |
|---------|--------|-------|---------|------------|
| **RETURNING Support** | ✅ Since v3.35.0 | ❌ Not supported | ✅ Since v10.5.0 | ✅ All versions |
| **Python Version Compatibility** | ⚠️ Issues with 3.9 and below | N/A | ✅ All versions | ✅ All versions |
| **Expression Support** | ✅ Basic expressions | N/A | ✅ Basic expressions | ✅ Complex expressions |
| **RETURNING Emulation** | N/A | ⚠️ Limited fallback | N/A | N/A |

## Hook Method Implementation Status

| Hook Method | SQLite | MySQL | MariaDB |
|-------------|--------|-------|---------|
| `_get_statement_type` | ✅ Custom | ❌ Base | ❌ Base |
| `_is_select_statement` | ✅ Custom | ✅ Custom | ✅ Custom |
| `_is_dml_statement` | ❌ Base | ❌ Base | ❌ Base |
| `_check_returning_compatibility` | ✅ Custom | ❌ Base | ✅ Custom |
| `_prepare_returning_clause` | ❌ Base | ✅ Custom | ✅ Custom |
| `_get_cursor` | ✅ Custom | ✅ Custom | ✅ Custom |
| `_execute_query` | ✅ Custom | ❌ Base | ✅ Custom |
| `_process_result_set` | ✅ Custom | ✅ Custom | ✅ Custom |
| `_build_query_result` | ❌ Base | ✅ Custom | ✅ Custom |
| `_handle_auto_commit_if_needed` | ✅ Custom | ✅ Custom | ✅ Custom |
| `_handle_execution_error` | ✅ Custom | ✅ Custom | ✅ Custom |

## Database-Specific Features

### SQLite
- PRAGMA statements handled as special case
- Python version compatibility checks
- SQLite version compatibility checks

### MySQL
- RETURNING clause emulation for INSERT with LAST_INSERT_ID()
- Separate query for fetching after INSERT
- Limited UPDATE/DELETE tracking

### MariaDB
- Version compatibility checks for RETURNING
- Custom error handling for specific MariaDB error codes