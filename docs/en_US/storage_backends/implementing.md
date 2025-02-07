# Backend Implementation Guide

## Overview

RhoSocial ActiveRecord provides a modular backend system that allows implementation of custom database backends. This guide explains how to create a new database backend.

## Basic Structure

A complete backend implementation consists of the following components:

```
your_backend/
├── __init__.py                # Package entry point
├── backend.py                 # Main backend implementation
├── dialect.py                 # SQL dialect and type mapping
├── transaction.py            # Transaction management
└── types.py                  # Database type definitions
```

## Core Components

### 1. Storage Backend

The main backend class must inherit from `StorageBackend`:

```python
from rhosocial.activerecord.backend import StorageBackend
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.typing import QueryResult

class YourBackend(StorageBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dialect = YourDialect()
        self._type_mapper = YourTypeMapper()
        self._value_mapper = YourValueMapper(self.config)
        self._transaction_manager = None
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def connect(self) -> None:
        """Establish database connection"""
        try:
            # Implement connection logic
            self._connection = your_db_library.connect(
                database=self.config.database,
                user=self.config.username,
                # ... other connection parameters
            )
        except Exception as e:
            raise DatabaseError(f"Connection failed: {str(e)}")

    def disconnect(self) -> None:
        """Close database connection"""
        if self._connection:
            try:
                self._connection.close()
            finally:
                self._connection = None
                self._cursor = None
                self._transaction_manager = None

    def ping(self, reconnect: bool = True) -> bool:
        """Test database connection"""
        if not self._connection:
            if reconnect:
                self.connect()
                return True
            return False
        
        try:
            self._connection.execute("SELECT 1")
            return True
        except:
            if reconnect:
                self.connect()
                return True
            return False

    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False,
        column_types: Optional[ColumnTypes] = None
    ) -> QueryResult:
        """Execute SQL query"""
        start_time = time.perf_counter()
        try:
            cursor = self._cursor or self._connection.cursor()
            # Process SQL and parameters using dialect
            final_sql, final_params = self.build_sql(sql, params)
            
            # Execute query
            cursor.execute(final_sql, final_params)
            
            if returning:
                # Get raw data
                rows = cursor.fetchall()
                # Convert types if mapping provided
                if column_types:
                    data = []
                    for row in rows:
                        converted_row = {}
                        for key, value in dict(row).items():
                            db_type = column_types.get(key)
                            converted_row[key] = (
                                self._value_mapper.from_database(value, db_type)
                                if db_type is not None
                                else value
                            )
                        data.append(converted_row)
                else:
                    data = [dict(row) for row in rows]
            else:
                data = None
            
            return QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=time.perf_counter() - start_time
            )
        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """Handle database-specific errors"""
        # Map database-specific errors to ActiveRecord errors
        raise DatabaseError(str(error))
```

### 2. SQL Dialect

The dialect class handles SQL syntax differences:

```python
from rhosocial.activerecord.dialect import (
    TypeMapper, 
    ValueMapper,
    DatabaseType
)

class YourDialect(SQLDialectBase):
    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format SQL expression"""
        if not isinstance(expr, YourExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get parameter placeholder"""
        return "?"  # Or %s, $1, etc. depending on database

    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Create SQL expression"""
        return YourExpression(expression)

class YourTypeMapper(TypeMapper):
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Map generic type to database-specific type"""
        if db_type not in YOUR_TYPE_MAPPINGS:
            raise ValueError(f"Unsupported type: {db_type}")
        
        mapping = YOUR_TYPE_MAPPINGS[db_type]
        if mapping.format_func:
            return mapping.format_func(mapping.db_type, params)
        return mapping.db_type

    def get_placeholder(self, db_type: DatabaseType) -> str:
        """Get parameter placeholder"""
        return "?"  # Or database-specific placeholder

class YourValueMapper(ValueMapper):
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._setup_converters()
    
    def to_database(self, value: Any, db_type: Optional[DatabaseType] = None) -> Any:
        """Convert Python value to database value"""
        if value is None:
            return None
        
        try:
            # Apply type-specific conversion
            if db_type in self._db_type_converters:
                return self._db_type_converters[db_type](value)
            
            # Apply basic type conversion
            value_type = type(value)
            if value_type in self._base_converters:
                return self._base_converters[value_type](value)
            
            return value
        except Exception as e:
            raise TypeConversionError(f"Conversion failed: {str(e)}")

    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert database value to Python value"""
        if value is None:
            return None
        
        try:
            converter = self._from_db_converters.get(db_type)
            if converter:
                return converter(value)
            return value
        except Exception as e:
            raise TypeConversionError(f"Conversion failed: {str(e)}")
```

### 3. Transaction Management

Implement transaction support:

```python
from rhosocial.activerecord.transaction import (
    TransactionManager,
    IsolationLevel
)

class YourTransactionManager(TransactionManager):
    def __init__(self, connection):
        super().__init__()
        self._connection = connection
        
    def _do_begin(self) -> None:
        """Begin transaction"""
        try:
            if self._isolation_level:
                level = self._get_isolation_sql()
                self._connection.execute(level)
            self._connection.execute("BEGIN TRANSACTION")
        except Exception as e:
            raise TransactionError(f"Begin failed: {str(e)}")
    
    def _do_commit(self) -> None:
        """Commit transaction"""
        try:
            self._connection.execute("COMMIT")
        except Exception as e:
            raise TransactionError(f"Commit failed: {str(e)}")
    
    def _do_rollback(self) -> None:
        """Rollback transaction"""
        try:
            self._connection.execute("ROLLBACK")
        except Exception as e:
            raise TransactionError(f"Rollback failed: {str(e)}")
    
    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported"""
        return True  # Or False depending on database
    
    def _do_create_savepoint(self, name: str) -> None:
        """Create savepoint"""
        self._connection.execute(f"SAVEPOINT {name}")
    
    def _do_release_savepoint(self, name: str) -> None:
        """Release savepoint"""
        self._connection.execute(f"RELEASE SAVEPOINT {name}")
    
    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to savepoint"""
        self._connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
```

### 4. Type Mappings

Define database-specific type mappings:

```python
from rhosocial.activerecord.dialect import DatabaseType, TypeMapping

# Define type mappings
YOUR_TYPE_MAPPINGS: Dict[DatabaseType, TypeMapping] = {
    DatabaseType.INTEGER: TypeMapping("INTEGER"),
    DatabaseType.FLOAT: TypeMapping("REAL"),
    DatabaseType.TEXT: TypeMapping("TEXT"),
    DatabaseType.DATETIME: TypeMapping("TIMESTAMP"),
    DatabaseType.BOOLEAN: TypeMapping("BOOLEAN"),
    DatabaseType.JSON: TypeMapping("JSONB"),
    # ... other type mappings
}

class YourColumnType:
    """Database-specific column type definition"""
    def __init__(self, sql_type: str, **constraints):
        self.sql_type = sql_type
        self.constraints = constraints
    
    def __str__(self):
        """Generate complete type definition"""
        sql = self.sql_type
        
        if "primary_key" in self.constraints:
            sql += " PRIMARY KEY"
        if "not_null" in self.constraints:
            sql += " NOT NULL"
        if "default" in self.constraints:
            sql += f" DEFAULT {self.constraints['default']}"
        
        return sql
```

## Implementation Checklist

1. **Basic Setup**
   - [ ] Create package structure
   - [ ] Implement StorageBackend subclass
   - [ ] Implement connection management

2. **SQL Support**
   - [ ] Implement SQL dialect
   - [ ] Define type mappings
   - [ ] Implement value conversion

3. **Transaction Support**
   - [ ] Implement transaction manager
   - [ ] Add savepoint support if available
   - [ ] Implement isolation levels

4. **Error Handling**
   - [ ] Map database errors to ActiveRecord errors
   - [ ] Implement proper cleanup on errors
   - [ ] Add connection retry logic

5. **Testing**
   - [ ] Unit tests for all components
   - [ ] Integration tests with actual database
   - [ ] Performance benchmarks
   - [ ] Edge case testing
   - [ ] Error handling tests

6. **Documentation**
   - [ ] API documentation
   - [ ] Configuration guide
   - [ ] Type mapping reference
   - [ ] Transaction behavior guide
   - [ ] Error handling guide

## Testing Your Backend

### 1. Unit Tests

```python
import pytest
from rhosocial.activerecord.backend.testing import BackendTestCase

class TestYourBackend(BackendTestCase):
    def setup_method(self):
        self.backend = YourBackend(database=":memory:")
        self.backend.connect()
    
    def teardown_method(self):
        self.backend.disconnect()
    
    def test_basic_operations(self):
        # Test basic CRUD operations
        result = self.backend.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )
        assert result.affected_rows >= 0
        
        result = self.backend.execute(
            "INSERT INTO test (name) VALUES (?)",
            ("test",)
        )
        assert result.affected_rows == 1
        assert result.last_insert_id is not None
    
    def test_transactions(self):
        with self.backend.transaction():
            self.backend.execute(
                "INSERT INTO test (name) VALUES (?)",
                ("test",)
            )
            # Test rollback
            raise Exception("Test rollback")
        
        # Verify rollback
        result = self.backend.execute(
            "SELECT COUNT(*) as count FROM test"
        )
        assert result.data[0]["count"] == 0
```

### 2. Integration Tests

```python
class TestIntegration:
    def setup_class(self):
        # Setup test database
        self.backend = YourBackend(
            host="localhost",
            database="test_db",
            username="test_user",
            password="test_pass"
        )
    
    def test_complex_queries(self):
        # Test joins
        result = self.backend.execute("""
            SELECT u.*, p.title 
            FROM users u 
            LEFT JOIN posts p ON u.id = p.user_id 
            WHERE u.status = ?
        """, ("active",))
        
        assert result.data is not None
        
    def test_concurrent_operations(self):
        import threading
        
        def worker():
            with self.backend.transaction():
                self.backend.execute(
                    "UPDATE counters SET value = value + 1 WHERE id = ?",
                    (1,)
                )
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
```

## Distribution

### 1. Package Structure

```
your-backend/
├── pyproject.toml
├── README.md
├── setup.py
├── src/
│   └── rhosocial_activerecord_yourdb/
│       ├── __init__.py
│       ├── backend.py
│       ├── dialect.py
│       ├── transaction.py
│       └── types.py
└── tests/
    ├── __init__.py
    ├── test_backend.py
    ├── test_dialect.py
    └── test_transaction.py
```

### 2. Setup Configuration

```python
# pyproject.toml
[project]
name = "rhosocial-activerecord-yourdb"
version = "1.0.0"
description = "YourDB backend for RhoSocial ActiveRecord"
dependencies = [
    "rhosocial-activerecord>=1.0.0",
    "your-db-driver>=1.0.0"
]

[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "coverage>=7.0.0"
]
```

### 3. Documentation

```markdown
# YourDB Backend for RhoSocial ActiveRecord

## Installation

```bash
pip install rhosocial-activerecord-yourdb
```

## Usage

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial_activerecord_yourdb import YourBackend

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str

User.configure(
    ConnectionConfig(
        host='localhost',
        database='mydb',
        username='user',
        password='pass'
    ),
    backend_class=YourBackend
)
```

## Configuration Options

- `host`: Database host
- `port`: Database port
- `database`: Database name
- `username`: Database user
- `password`: Database password
- `pool_size`: Connection pool size
- `charset`: Character set
```

## Best Practices

1. **Error Handling**
   - Map database-specific errors to ActiveRecord errors
   - Provide detailed error messages
   - Handle connection failures gracefully

2. **Type Conversion**
   - Implement robust type conversion
   - Handle edge cases
   - Preserve data precision

3. **Transaction Management**
   - Implement proper savepoint support
   - Handle nested transactions correctly
   - Support different isolation levels

4. **Performance**
   - Use connection pooling
   - Implement efficient batch operations
   - Cache prepared statements when possible

5. **Testing**
   - Comprehensive test suite
   - Test with real database
   - Test edge cases and error conditions

## Common Issues

1. **Connection Management**
   ```python
   # Bad - not cleaning up
   def execute(self, sql, params):
       conn = self.connect()
       return conn.execute(sql, params)
   
   # Good - proper cleanup
   def execute(self, sql, params):
       try:
           return self._connection.execute(sql, params)
       finally:
           self._cleanup()
   ```

2. **Transaction Handling**
   ```python
   # Bad - not handling errors
   def commit(self):
       self._connection.commit()
   
   # Good - proper error handling
   def commit(self):
       try:
           self._connection.commit()
       except Exception as e:
           self.rollback()
           raise TransactionError(f"Commit failed: {str(e)}")
   ```

## Next Steps

1. Review the [Backend API Reference](backend_api.md)
2. Study the [SQLite Backend Implementation](sqlite_implementation.md)
3. Understand [Transaction Management](transactions.md)
4. Learn about [Performance Optimization](performance.md)