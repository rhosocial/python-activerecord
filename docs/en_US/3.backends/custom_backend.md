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

To be continued...