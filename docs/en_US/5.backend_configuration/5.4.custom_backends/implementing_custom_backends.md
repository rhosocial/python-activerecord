# Implementing Custom Database Backends

This guide provides detailed instructions on how to implement a custom database backend for rhosocial ActiveRecord.

## Prerequisites

Before implementing a custom database backend, you should:

1. Be familiar with the rhosocial ActiveRecord architecture
2. Understand the database system you want to implement
3. Have the necessary database driver package installed

## Implementation Steps

Implementing a custom database backend involves several key steps:

### 1. Create the Backend Directory Structure

Create a new directory for your backend under the implementation directory:

```
rhosocial/activerecord/backend/impl/your_backend_name/
```

Inside this directory, create the following files:

```
__init__.py       # Package initialization and exports
backend.py        # Main backend implementation
dialect.py        # SQL dialect implementation
types.py          # Type mapping definitions
```

### 2. Implement the Backend Class

In `backend.py`, create a class that inherits from `StorageBackend`:

```python
from ...base import StorageBackend, ColumnTypes

class YourBackendName(StorageBackend):
    """Your database backend implementation"""
    
    def __init__(self, **kwargs):
        """Initialize your backend
        
        Args:
            **kwargs: Configuration parameters
        """
        super().__init__(**kwargs)
        # Initialize your database connection and settings
        
    @property
    def dialect(self):
        """Get SQL dialect for this backend"""
        from .dialect import YourDialectClass
        return YourDialectClass()
    
    def connect(self):
        """Establish database connection"""
        # Implement connection logic
        
    def disconnect(self):
        """Close database connection"""
        # Implement disconnection logic
        
    def is_connected(self) -> bool:
        """Check if database is connected"""
        # Implement connection check
        
    def execute(self, query, params=None, **options):
        """Execute a query
        
        Args:
            query: SQL query string
            params: Query parameters
            **options: Additional options
            
        Returns:
            QueryResult: Result of the query
        """
        # Implement query execution logic
        
    # Implement other required methods
```

### 3. Implement the SQL Dialect

In `dialect.py`, create a class that inherits from `SQLDialectBase`:

```python
from ...dialect import SQLDialectBase, SQLBuilder

class YourDialectClass(SQLDialectBase):
    """SQL dialect implementation for your database"""
    
    def __init__(self):
        super().__init__()
    
    def create_builder(self) -> SQLBuilder:
        """Create SQL builder for this dialect"""
        return YourSQLBuilder(self)
    
    # Implement other dialect-specific methods

class YourSQLBuilder(SQLBuilder):
    """SQL builder for your database"""
    
    def __init__(self, dialect):
        super().__init__(dialect)
    
    def get_placeholder(self, index=None) -> str:
        """Get parameter placeholder syntax
        
        Args:
            index: Parameter index (optional)
            
        Returns:
            str: Placeholder string
        """
        # Return the appropriate placeholder syntax for your database
        # Examples: '?' for SQLite, '%s' for MySQL, '$1' for PostgreSQL
        
    # Implement other builder-specific methods
```

### 4. Implement Type Mappings

In `types.py`, define your database type mappings:

```python
from typing import Dict

from ...dialect import TypeMapping
from ...typing import DatabaseType
from ...helpers import format_with_length

# Your database type mapping configuration
YOUR_DB_TYPE_MAPPINGS: Dict[DatabaseType, TypeMapping] = {
    DatabaseType.TINYINT: TypeMapping("INTEGER"),
    DatabaseType.SMALLINT: TypeMapping("INTEGER"),
    DatabaseType.INTEGER: TypeMapping("INTEGER"),
    DatabaseType.BIGINT: TypeMapping("INTEGER"),
    DatabaseType.FLOAT: TypeMapping("REAL"),
    DatabaseType.DOUBLE: TypeMapping("REAL"),
    DatabaseType.DECIMAL: TypeMapping("REAL"),
    DatabaseType.CHAR: TypeMapping("TEXT", format_with_length),
    DatabaseType.VARCHAR: TypeMapping("TEXT", format_with_length),
    DatabaseType.TEXT: TypeMapping("TEXT"),
    DatabaseType.DATE: TypeMapping("TEXT"),
    DatabaseType.TIME: TypeMapping("TEXT"),
    DatabaseType.DATETIME: TypeMapping("TEXT"),
    DatabaseType.TIMESTAMP: TypeMapping("TEXT"),
    DatabaseType.BLOB: TypeMapping("BLOB"),
    DatabaseType.BOOLEAN: TypeMapping("INTEGER"),
    DatabaseType.UUID: TypeMapping("TEXT"),
    DatabaseType.JSON: TypeMapping("TEXT"),
    DatabaseType.ARRAY: TypeMapping("TEXT"),
    # Your database specific types are set as CUSTOM
    DatabaseType.CUSTOM: TypeMapping("TEXT"),
}


class YourDBTypes:
    """Your database specific type constants"""
    # Add your database specific types here


class YourDBColumnType:
    """Your database column type definition"""

    def __init__(self, sql_type: str, **constraints):
        """Initialize column type

        Args:
            sql_type: SQL type definition
            **constraints: Constraint conditions
        """
        self.sql_type = sql_type
        self.constraints = constraints

    def __str__(self):
        """Generate complete type definition statement"""
        # Implement type definition string generation
        pass

    @classmethod
    def get_type(cls, db_type: DatabaseType, **params) -> 'YourDBColumnType':
        """Create your database column type from generic type

        Args:
            db_type: Generic database type definition
            **params: Type parameters and constraints

        Returns:
            YourDBColumnType: Your database column type instance

        Raises:
            ValueError: If type is not supported
        """
        mapping = YOUR_DB_TYPE_MAPPINGS.get(db_type)
        if not mapping:
            raise ValueError(f"Unsupported type: {db_type}")

        sql_type = mapping.db_type
        if mapping.format_func:
            sql_type = mapping.format_func(sql_type, params)

        constraints = {k: v for k, v in params.items()
                     if k in ['primary_key', 'autoincrement', 'unique',
                             'not_null', 'default']}

        return cls(sql_type, **constraints)
```

### 5. Update the Package Initialization

In `__init__.py`, export your backend class:

```python
"""Your database backend implementation for rhosocial ActiveRecord.

This module provides:
- Your database backend with connection management and query execution
- SQL dialect implementation for your database
- Type mapping between ActiveRecord types and your database types
"""

from .backend import YourBackendName
from .dialect import YourDialectClass

__all__ = [
    # Dialect
    'YourDialectClass',
    
    # Backend
    'YourBackendName',
]
```

## Required Methods

Your backend implementation must provide the following methods:

| Method | Description |
|--------|-------------|
| `connect()` | Establish database connection |
| `disconnect()` | Close database connection |
| `is_connected()` | Check if database is connected |
| `execute()` | Execute a query |
| `begin_transaction()` | Begin a transaction |
| `commit_transaction()` | Commit a transaction |
| `rollback_transaction()` | Rollback a transaction |
| `create_table()` | Create a database table |
| `drop_table()` | Drop a database table |
| `table_exists()` | Check if a table exists |
| `get_columns()` | Get column information for a table |

## Transaction Support

Implementing transaction support is crucial for a database backend. Your implementation should handle:

1. Transaction nesting (if supported by your database)
2. Savepoints (if supported)
3. Different isolation levels

```python
def begin_transaction(self, isolation_level=None):
    """Begin a transaction
    
    Args:
        isolation_level: Optional isolation level
    """
    if self._transaction_level == 0:
        # Start a new transaction
        cursor = self._get_cursor()
        if isolation_level:
            # Set isolation level if specified
            cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
        cursor.execute("BEGIN TRANSACTION")
    else:
        # Create a savepoint for nested transaction if supported
        cursor = self._get_cursor()
        cursor.execute(f"SAVEPOINT sp_{self._transaction_level}")
    
    self._transaction_level += 1
```

## Error Handling

Your backend should handle database-specific errors and translate them to ActiveRecord exceptions:

```python
def _handle_execution_error(self, error):
    """Handle database-specific errors
    
    Args:
        error: Original database error
        
    Raises:
        Appropriate ActiveRecord exception
    """
    # Map database-specific errors to ActiveRecord exceptions
    error_code = getattr(error, 'code', None)
    
    if error_code == 'YOUR_DB_CONSTRAINT_ERROR':
        from ...errors import ConstraintViolationError
        raise ConstraintViolationError(str(error))
    elif error_code == 'YOUR_DB_CONNECTION_ERROR':
        from ...errors import ConnectionError
        raise ConnectionError(str(error))
    # Handle other specific errors
    
    # Re-raise as generic database error if not handled
    from ...errors import DatabaseError
    raise DatabaseError(str(error))
```

## Testing Your Backend

Create comprehensive tests for your backend implementation:

1. Basic connection tests
2. CRUD operation tests
3. Transaction tests
4. Error handling tests
5. Performance tests

## Integration with ActiveRecord

To make your backend available to ActiveRecord, you need to register it in the backend factory:

```python
# In rhosocial.activerecord.backend.__init__.py or a custom factory

from rhosocial.activerecord.backend.impl.your_backend_name import YourBackendName

def create_backend(backend_type, **config):
    # Existing backends...
    elif backend_type == 'your_backend_name':
        return YourBackendName(**config)
```

## Example Usage

Once implemented, your backend can be used like any other ActiveRecord backend:

```python
from rhosocial.activerecord import ActiveRecord, configure

# Configure ActiveRecord to use your backend
configure(backend='your_backend_name', host='localhost', database='your_db')

# Define models using your backend
class User(ActiveRecord):
    __tablename__ = 'users'
```

## Implementation Location

When implementing your custom backend, you have flexibility in where to place your code:

1. **Within the ActiveRecord Package**: You can place your implementation directly in the `rhosocial.activerecord.backend.impl` directory if you're modifying the core package.
2. **In a Separate Package**: You can create your own package structure outside the core ActiveRecord package, which is recommended if you plan to distribute your backend separately.

Both approaches are valid, with the separate package offering better isolation and easier distribution.

## Testing Your Custom Backend

Thoroughly testing your custom backend is crucial for ensuring reliability. You should:

1. **Mirror Existing Tests**: Study and mirror the test structure of existing backends (e.g., in the `tests/rhosocial/activerecord/backend` directory)
2. **Ensure Branch Coverage**: Write tests that cover all code branches and edge cases
3. **Simulate Real-World Scenarios**: Create tests that simulate various usage scenarios your backend will encounter
4. **Test Integration**: Verify that your custom backend works correctly with the rest of the ActiveRecord framework

## Best Practices

1. **Follow Existing Patterns**: Study the existing backend implementations (SQLite, MySQL, PostgreSQL) for guidance
2. **Handle Edge Cases**: Consider all possible error scenarios and edge cases
3. **Document Thoroughly**: Provide clear documentation for your backend's features and limitations
4. **Test Comprehensively**: Create thorough tests for all aspects of your backend
5. **Consider Performance**: Optimize your implementation for performance

## Conclusion

Implementing a custom database backend for rhosocial ActiveRecord requires careful attention to detail and thorough understanding of both the ActiveRecord architecture and your target database system. By following this guide, you can create a robust backend implementation that integrates seamlessly with the ActiveRecord framework.