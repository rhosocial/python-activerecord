# Creating Custom Backends

This guide explains how to create custom database backends for RhoSocial ActiveRecord.

## Overview

Creating a custom backend involves:
1. Implementing core interfaces
2. Creating type system
3. Building SQL components
4. Managing transactions

## Basic Structure

### Required Components

```
Custom Backend
├── Backend Implementation
│   ├── CustomBackend
│   └── ConnectionConfig
├── Type System
│   ├── CustomTypeMapper
│   └── CustomValueMapper
├── SQL Components
│   ├── CustomDialect
│   └── CustomExpression
└── Transaction
    └── CustomTransactionManager
```

## Backend Implementation

### Core Backend Class

```python
from rhosocial.activerecord.backend import StorageBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig, QueryResult

class CustomBackend(StorageBackend):
    """Custom database backend implementation."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._type_mapper = CustomTypeMapper()
        self._value_mapper = CustomValueMapper(self.config)
        self._dialect = CustomDialect()
        self._transaction_manager = None
    
    def connect(self) -> None:
        """Establish database connection."""
        try:
            # Initialize database connection
            self._connection = your_db_library.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                username=self.config.username,
                password=self.config.password
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False,
        column_types: Optional[Dict[str, DatabaseType]] = None
    ) -> QueryResult:
        """Execute SQL statement."""
        try:
            # Ensure connection
            if not self._connection:
                self.connect()
            
            cursor = self._connection.cursor()
            
            # Process SQL and parameters
            final_sql, final_params = self.build_sql(sql, params)
            
            # Convert parameters
            if final_params:
                processed_params = tuple(
                    self._value_mapper.to_database(value, None)
                    for value in final_params
                )
                cursor.execute(final_sql, processed_params)
            else:
                cursor.execute(final_sql)
            
            if returning:
                rows = cursor.fetchall()
                # Convert result types
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
                last_insert_id=cursor.lastrowid
            )
        except Exception as e:
            self._handle_error(e)
    
    def _handle_error(self, error: Exception) -> None:
        """Handle database-specific errors."""
        if isinstance(error, your_db_library.Error):
            if "connection" in str(error).lower():
                raise ConnectionError(str(error))
            elif "duplicate" in str(error).lower():
                raise IntegrityError(str(error))
            elif "timeout" in str(error).lower():
                raise OperationalError(str(error))
        raise DatabaseError(str(error))
```

## Type System Implementation

### Type Mapping

```python
class CustomTypeMapper(TypeMapper):
    """Custom type mapping implementation."""
    
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get database column type definition."""
        mappings = {
            DatabaseType.INTEGER: 'INTEGER',
            DatabaseType.FLOAT: 'FLOAT',
            DatabaseType.DECIMAL: 'DECIMAL',
            DatabaseType.VARCHAR: 'VARCHAR',
            DatabaseType.TEXT: 'TEXT',
            DatabaseType.DATE: 'DATE',
            DatabaseType.TIME: 'TIME',
            DatabaseType.DATETIME: 'TIMESTAMP',
            DatabaseType.BOOLEAN: 'BOOLEAN',
            DatabaseType.JSON: 'JSONB',
            DatabaseType.ARRAY: 'ARRAY',
            DatabaseType.UUID: 'UUID'
        }
        
        base_type = mappings.get(db_type)
        if not base_type:
            raise ValueError(f"Unsupported type: {db_type}")
        
        # Handle type parameters
        if db_type == DatabaseType.VARCHAR and 'length' in params:
            return f"VARCHAR({params['length']})"
        
        if db_type == DatabaseType.DECIMAL:
            precision = params.get('precision', 10)
            scale = params.get('scale', 2)
            return f"DECIMAL({precision},{scale})"
        
        return base_type
    
    def get_placeholder(self, db_type: DatabaseType) -> str:
        """Get parameter placeholder."""
        return "%s"  # Or your database's placeholder style
```

### Value Conversion

```python
class CustomValueMapper(ValueMapper):
    """Custom value conversion implementation."""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._base_converters = {
            int: int,
            float: float,
            Decimal: str,
            bool: self._convert_boolean,
            uuid.UUID: str,
            date: self._convert_date,
            time: self._convert_time,
            datetime: self._convert_datetime,
            dict: safe_json_dumps,
            list: array_converter
        }
    
    def to_database(self, value: Any, db_type: Optional[DatabaseType]) -> Any:
        """Convert Python value to database value."""
        if value is None:
            return None
        
        # Try base type conversion
        value_type = type(value)
        if value_type in self._base_converters:
            return self._base_converters[value_type](value)
        
        # Try database type conversion
        if db_type:
            if db_type == DatabaseType.JSON:
                return safe_json_dumps(value)
            if db_type == DatabaseType.ARRAY:
                return array_converter(value)
            if db_type == DatabaseType.BOOLEAN:
                return self._convert_boolean(value)
            if db_type in (DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME):
                return self._convert_datetime(value)
        
        return value
    
    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert database value to Python value."""
        if value is None:
            return None
        
        if db_type == DatabaseType.JSON:
            return safe_json_loads(value)
        
        if db_type == DatabaseType.BOOLEAN:
            return bool(value)
        
        if db_type == DatabaseType.DATE:
            return parse_date(value)
        
        if db_type == DatabaseType.DATETIME:
            return parse_datetime(value)
        
        if db_type == DatabaseType.ARRAY:
            return safe_json_loads(value)
        
        return value
    
    def _convert_boolean(self, value: Any) -> Any:
        """Convert to database boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def _convert_date(self, value: date) -> str:
        """Convert date to database format."""
        return value.isoformat()
    
    def _convert_time(self, value: time) -> str:
        """Convert time to database format."""
        return value.isoformat()
    
    def _convert_datetime(self, value: datetime) -> str:
        """Convert datetime to database format."""
        if self.config.timezone:
            value = value.astimezone(pytz.timezone(self.config.timezone))
        return value.isoformat(sep=' ', timespec='seconds')
```

## Transaction Implementation

```python
class CustomTransactionManager:
    """Custom transaction manager implementation."""
    
    def __init__(self, connection):
        self._connection = connection
        self._savepoint_id = 0
        self._isolation_level = None
    
    def begin(self):
        """Begin transaction."""
        try:
            # Set isolation level if specified
            if self._isolation_level:
                self._connection.execute(
                    f"SET TRANSACTION ISOLATION LEVEL {self._isolation_level.name}"
                )
            self._connection.execute("BEGIN TRANSACTION")
        except Exception as e:
            raise TransactionError(f"Failed to begin transaction: {str(e)}")
    
    def commit(self):
        """Commit transaction."""
        try:
            self._connection.execute("COMMIT")
        except Exception as e:
            raise TransactionError(f"Failed to commit transaction: {str(e)}")
    
    def rollback(self):
        """Rollback transaction."""
        try:
            self._connection.execute("ROLLBACK")
        except Exception as e:
            raise TransactionError(f"Failed to rollback transaction: {str(e)}")
    
    def create_savepoint(self, name: str):
        """Create savepoint."""
        try:
            self._connection.execute(f"SAVEPOINT {name}")
        except Exception as e:
            raise TransactionError(f"Failed to create savepoint: {str(e)}")
    
    def release_savepoint(self, name: str):
        """Release savepoint."""
        try:
            self._connection.execute(f"RELEASE SAVEPOINT {name}")
        except Exception as e:
            raise TransactionError(f"Failed to release savepoint: {str(e)}")
    
    def rollback_savepoint(self, name: str):
        """Rollback to savepoint."""
        try:
            self._connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        except Exception as e:
            raise TransactionError(f"Failed to rollback to savepoint: {str(e)}")

## Error Handling

```python
class CustomErrorHandler:
    """Custom database error handler."""
    
    @staticmethod
    def handle_error(error: Exception) -> None:
        """Convert database-specific errors to ActiveRecord errors."""
        error_msg = str(error).lower()
        
        if "connection" in error_msg:
            raise ConnectionError(str(error))
        
        if "duplicate" in error_msg:
            raise IntegrityError(str(error))
        
        if "constraint" in error_msg:
            raise IntegrityError(str(error))
        
        if "timeout" in error_msg:
            raise OperationalError(str(error))
        
        if "deadlock" in error_msg:
            raise DeadlockError(str(error))
        
        raise DatabaseError(str(error))

# Usage in backend
def execute(self, sql: str, params: Optional[Tuple] = None) -> QueryResult:
    try:
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        return QueryResult(...)
    except Exception as e:
        CustomErrorHandler.handle_error(e)
```

## Configuration

```python
class CustomBackendConfig:
    """Configuration for custom database backend."""
    
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 5432)
        self.database = kwargs.get('database')
        self.user = kwargs.get('user')
        self.password = kwargs.get('password')
        
        # Connection pool settings
        self.pool_size = kwargs.get('pool_size', 5)
        self.pool_timeout = kwargs.get('pool_timeout', 30)
        
        # Query settings
        self.query_timeout = kwargs.get('query_timeout', 30)
        
        # Type mapping settings
        self.use_native_json = kwargs.get('use_native_json', True)
        self.use_native_uuid = kwargs.get('use_native_uuid', True)
        
        # Additional options
        self.options = kwargs.get('options', {})
    
    def get_connection_params(self) -> dict:
        """Get connection parameters for database."""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            **self.options
        }

# Usage
config = CustomBackendConfig(
    host='db.example.com',
    database='app_db',
    user='app_user',
    password='secret',
    pool_size=10,
    options={
        'ssl': True,
        'application_name': 'MyApp'
    }
)
```

## Testing

```python
import pytest
from unittest.mock import Mock, patch

class TestCustomBackend:
    @pytest.fixture
    def backend(self):
        """Create test backend instance."""
        config = CustomBackendConfig(database=':memory:')
        return CustomBackend(config)
    
    def test_connection(self, backend):
        """Test database connection."""
        backend.connect()
        assert backend.is_connected()
        backend.disconnect()
        assert not backend.is_connected()
    
    def test_query_execution(self, backend):
        """Test query execution."""
        with backend.transaction():
            result = backend.execute(
                "SELECT * FROM users WHERE id = ?",
                (1,)
            )
            assert result is not None
    
    def test_transaction_management(self, backend):
        """Test transaction handling."""
        with backend.transaction() as tx:
            # Execute query
            backend.execute("INSERT INTO users (name) VALUES (?)", ("Test",))
            
            # Create savepoint
            tx.create_savepoint("test_point")
            
            try:
                # This will fail
                backend.execute("INSERT INTO invalid_table VALUES (1)")
            except:
                # Rollback to savepoint
                tx.rollback_savepoint("test_point")
    
    def test_error_handling(self, backend):
        """Test error conversion."""
        with pytest.raises(ConnectionError):
            backend.execute("SELECT * FROM non_existent_table")
        
        with pytest.raises(IntegrityError):
            backend.execute("INSERT INTO users (id) VALUES (1)")  # Duplicate key
    
    @patch('custom_backend.connection')
    def test_connection_pool(self, mock_connection):
        """Test connection pooling."""
        mock_pool = Mock()
        mock_connection.create_pool.return_value = mock_pool
        
        config = CustomBackendConfig(pool_size=5)
        backend = CustomBackend(config)
        
        # First connection should create pool
        backend.connect()
        mock_connection.create_pool.assert_called_once()
        
        # Subsequent connections should reuse pool
        backend.connect()
        mock_connection.create_pool.assert_called_once()
```

## Best Practices

1. **Error Handling**
   - Convert database-specific errors to ActiveRecord errors
   - Provide detailed error messages
   - Handle connection issues gracefully
   - Implement proper logging

2. **Transaction Management**
   - Support nested transactions
   - Implement proper savepoint handling
   - Handle transaction isolation levels
   - Clean up resources properly

3. **Configuration**
   - Make backend configurable
   - Support connection pooling
   - Allow type mapping customization
   - Provide sensible defaults

4. **Testing**
   - Write comprehensive tests
   - Mock database connections
   - Test error conditions
   - Verify transaction behavior

5. **Implementation**
   - Follow interface contracts
   - Maintain type safety
   - Document public APIs
   - Write clean, maintainable code

## Example Implementation

Here's a complete example of implementing a custom backend for a hypothetical database:

```python
class CustomBackend(StorageBackend):
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._type_mapper = CustomTypeMapper()
        self._value_mapper = CustomValueMapper()
        self._dialect = CustomDialect()
        self._error_handler = CustomErrorHandler()
        self._pool = None
    
    def connect(self) -> None:
        """Establish database connection."""
        if self._pool is None:
            self._pool = create_connection_pool(
                size=self.config.pool_size,
                **self.config.get_connection_params()
            )
        self._connection = self._pool.get_connection()
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False
    ) -> QueryResult:
        """Execute SQL statement."""
        try:
            if not self._connection:
                self.connect()
            
            cursor = self._connection.cursor()
            
            # Process SQL and parameters
            final_sql, final_params = self.build_sql(sql, params)
            
            # Convert parameters
            if final_params:
                processed_params = tuple(
                    self._value_mapper.to_database(value, None)
                    for value in final_params
                )
                cursor.execute(final_sql, processed_params)
            else:
                cursor.execute(final_sql)
            
            if returning:
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
            else:
                data = None
            
            return QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid
            )
            
        except Exception as e:
            self._error_handler.handle_error(e)
    
    def transaction(self) -> ContextManager:
        """Get transaction context manager."""
        if not hasattr(self, '_transaction_manager'):
            self._transaction_manager = CustomTransactionManager(self._connection)
        return self._transaction_manager

    def supports_returning(self) -> bool:
        """Check if RETURNING clause is supported."""
        return True

# Usage example
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str

# Configure with custom backend
User.configure(
    ConnectionConfig(
        database='app_db',
        host='localhost',
        pool_size=5
    ),
    backend_class=CustomBackend
)

# Use in application
with User.transaction():
    user = User(name='John', email='john@example.com')
    user.save()
```

This implementation provides a complete example of creating a custom backend with all required functionality.