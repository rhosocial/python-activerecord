# Backend Architecture

This document explains the architecture of RhoSocial ActiveRecord's backend system, including its components, relationships, and extension mechanisms.

## System Overview

The backend system consists of several key components:

```
Backend System
├── StorageBackend (Abstract Base)
│   ├── Connection Management
│   ├── Query Execution
│   └── Transaction Handling
│
├── Type System
│   ├── DatabaseType (Enum)
│   ├── TypeMapper (Interface)
│   └── ValueMapper (Interface)
│
├── SQL Components
│   ├── SQLDialect (Interface)
│   ├── SQLExpression (Interface)
│   └── QueryBuilder
│
└── Transaction Management
    ├── TransactionManager (Abstract)
    ├── IsolationLevel (Enum)
    └── Savepoint Support
```

## Core Components

### Storage Backend

The abstract base class defining core functionality:

```python
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass
    
    @abstractmethod
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False
    ) -> QueryResult:
        """Execute SQL statement."""
        pass
    
    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin transaction."""
        pass
    
    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit transaction."""
        pass
    
    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        pass
```

### Type System

Handles type mapping and conversion:

```python
from enum import Enum, auto
from typing import Any, Optional

class DatabaseType(Enum):
    """Unified database type definitions."""
    INTEGER = auto()
    FLOAT = auto()
    DECIMAL = auto()
    VARCHAR = auto()
    TEXT = auto()
    DATETIME = auto()
    BOOLEAN = auto()
    JSON = auto()
    # ...

class TypeMapper(ABC):
    """Abstract interface for type mapping."""
    
    @abstractmethod
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get database column type definition."""
        pass
    
    @abstractmethod
    def get_placeholder(self, db_type: DatabaseType) -> str:
        """Get parameter placeholder."""
        pass

class ValueMapper(ABC):
    """Abstract interface for value conversion."""
    
    @abstractmethod
    def to_database(self, value: Any, db_type: Optional[DatabaseType]) -> Any:
        """Convert Python value to database value."""
        pass
    
    @abstractmethod
    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert database value to Python value."""
        pass
```

### SQL Components

Handle SQL generation and execution:

```python
class SQLDialect(ABC):
    """Abstract interface for SQL dialects."""
    
    @abstractmethod
    def format_expression(self, expr: SQLExpression) -> str:
        """Format SQL expression."""
        pass
    
    @abstractmethod
    def get_placeholder(self) -> str:
        """Get parameter placeholder."""
        pass
    
    @abstractmethod
    def create_expression(self, expression: str) -> SQLExpression:
        """Create SQL expression."""
        pass

class QueryBuilder:
    """SQL query builder."""
    
    def build_where(self, conditions: List[Tuple]) -> Tuple[str, List]:
        """Build WHERE clause."""
        pass
    
    def build_order(self, clauses: List[str]) -> str:
        """Build ORDER BY clause."""
        pass
    
    def build_group(self, clauses: List[str]) -> str:
        """Build GROUP BY clause."""
        pass
```

### Transaction Management

Handles transaction control:

```python
class TransactionManager(ABC):
    """Abstract base for transaction management."""
    
    @abstractmethod
    def begin(self) -> None:
        """Begin transaction."""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Commit transaction."""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction."""
        pass
    
    @abstractmethod
    def create_savepoint(self, name: str) -> None:
        """Create savepoint."""
        pass
    
    @abstractmethod
    def release_savepoint(self, name: str) -> None:
        """Release savepoint."""
        pass
    
    @abstractmethod
    def rollback_savepoint(self, name: str) -> None:
        """Rollback to savepoint."""
        pass
```

## Implementation Example

Here's how SQLite implements these interfaces:

```python
class SQLiteBackend(StorageBackend):
    """SQLite backend implementation."""
    
    def __init__(self, **kwargs):
        self._connection = None
        self._type_mapper = SQLiteTypeMapper()
        self._value_mapper = SQLiteValueMapper()
        self._dialect = SQLiteDialect()
    
    def connect(self) -> None:
        self._connection = sqlite3.connect(
            self.config.database,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False
    ) -> QueryResult:
        cursor = self._connection.cursor()
        cursor.execute(sql, params or ())
        
        if returning:
            rows = cursor.fetchall()
            return QueryResult(
                data=rows,
                affected_rows=cursor.rowcount
            )
        
        return QueryResult(
            affected_rows=cursor.rowcount
        )

class SQLiteTypeMapper(TypeMapper):
    """SQLite type mapping implementation."""
    
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        mappings = {
            DatabaseType.INTEGER: 'INTEGER',
            DatabaseType.TEXT: 'TEXT',
            DatabaseType.FLOAT: 'REAL',
            DatabaseType.BOOLEAN: 'INTEGER',
            # ...
        }
        return mappings[db_type]
    
    def get_placeholder(self, db_type: DatabaseType) -> str:
        return "?"

class SQLiteValueMapper(ValueMapper):
    """SQLite value conversion implementation."""
    
    def to_database(self, value: Any, db_type: Optional[DatabaseType]) -> Any:
        if value is None:
            return None
            
        if db_type == DatabaseType.BOOLEAN:
            return 1 if value else 0
            
        if db_type == DatabaseType.JSON:
            return json.dumps(value)
            
        return value
    
    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        if value is None:
            return None
            
        if db_type == DatabaseType.BOOLEAN:
            return bool(value)
            
        if db_type == DatabaseType.JSON:
            return json.loads(value)
            
        return value
```

## Extension Points

To create a new backend:

1. **Implement StorageBackend**
   - Connection management
   - Query execution
   - Transaction handling

2. **Implement Type System**
   - Create TypeMapper implementation
   - Create ValueMapper implementation
   - Define type mappings

3. **Implement SQL Components**
   - Create SQLDialect implementation
   - Create SQLExpression implementation
   - Extend QueryBuilder if needed

4. **Implement Transaction Management**
   - Create TransactionManager implementation
   - Support required isolation levels
   - Implement savepoint handling

## Component Interaction

Example of component interaction:

```python
class Order(ActiveRecord):
    id: int
    total: Decimal
    status: str

# Configuration
Order.configure(config, SQLiteBackend)

# Save operation
order = Order(total=Decimal('100'), status='pending')
order.save()

# Internal flow:
# 1. Model prepares data
# 2. Backend starts transaction
# 3. TypeMapper converts field types
# 4. ValueMapper converts values
# 5. QueryBuilder constructs SQL
# 6. SQLDialect formats SQL
# 7. Backend executes query
# 8. Transaction commits
# 9. ValueMapper converts results
```

## Best Practices

1. **Interface Adherence**
   - Implement all abstract methods
   - Follow interface contracts
   - Maintain type safety

2. **Type Handling**
   - Support all DatabaseType values
   - Handle NULL values properly
   - Implement proper type conversion

3. **Transaction Support**
   - Implement proper nesting
   - Support savepoints
   - Handle isolation levels

4. **Error Handling**
   - Convert database errors
   - Provide detailed messages
   - Maintain consistency

## Next Steps

1. See [SQLite Usage](sqlite_usage.md) for practical examples
2. Study [SQLite Implementation](sqlite_impl.md) for details
3. Learn to [Create Backends](custom_backend.md)