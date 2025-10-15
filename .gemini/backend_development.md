# Backend Development Guide

## Overview

This guide provides comprehensive instructions for implementing new database backends for the rhosocial-activerecord ecosystem. Whether you're adding support for a new SQL database or a NoSQL system, this document outlines the requirements, patterns, and best practices.

**Important Design Constraint**: Backend implementations must be built using **native database drivers only** (e.g., `mysql-connector-python`, `psycopg2`). Do not use or depend on other ORMs like SQLAlchemy, Django ORM, or similar. This ensures the rhosocial-activerecord ecosystem remains lightweight and independent.

## Backend Architecture

### Package Structure

```
rhosocial-activerecord-{backend}/
├── src/
│   └── rhosocial/
│       └── activerecord/
│           └── backend/
│               └── impl/
│                   └── {backend}/
│                       ├── __init__.py
│                       ├── backend.py       # Main backend implementation
│                       ├── config.py        # Connection configuration
│                       ├── dialect.py       # SQL dialect handling
│                       ├── type_converters.py # Type conversion
│                       ├── transaction.py   # Transaction management
│                       └── features.py      # Feature detection
├── tests/
│   └── rhosocial/
│       └── activerecord_{backend}_test/
│           ├── test_backend.py
│           ├── test_transactions.py
│           └── test_types.py
├── pyproject.toml
├── README.md
└── LICENSE
```

## Core Requirements

### Design Philosophy

Backend implementations should:
- **Avoid ORM dependencies**: Do not use SQLAlchemy, Django ORM, or other ORMs
- **Use database drivers directly**: Interact with native database drivers (e.g., `mysql-connector-python`, `psycopg2`)
- **Maintain minimal dependencies**: Only add the database driver as a dependency

### 1. StorageBackend Interface

Every backend must implement the `StorageBackend` abstract base class:

```python
# backend.py
# Example implementation using native driver only
import mysql.connector  # Native MySQL driver - NOT SQLAlchemy!
from rhosocial.activerecord.backend.base import StorageBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from typing import Any, Dict, List, Optional

class MyBackend(StorageBackend):
    """Implementation of MyDatabase backend using native driver."""
    
    def __init__(self, connection_config: ConnectionConfig):
        """Initialize backend with configuration."""
        super().__init__(connection_config)
        self._connection = None  # Will hold native driver connection
        self._transaction_level = 0
    
    # Connection Management
    def connect(self) -> None:
        """Establish database connection."""
        pass
    
    def disconnect(self) -> None:
        """Close database connection."""
        pass
    
    def is_connected(self) -> bool:
        """Check if connected to database."""
        pass
    
    def ping(self, reconnect: bool = True) -> bool:
        """Test database connection."""
        pass
    
    # Query Execution
    def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        returning: bool = False
    ) -> QueryResult:
        """Execute SQL query."""
        pass
    
    def fetch_one(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row."""
        pass
    
    def fetch_many(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch multiple rows."""
        pass
    
    def fetch_all(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        pass
    
    # Transaction Management
    def begin(self) -> None:
        """Begin transaction."""
        pass
    
    def commit(self) -> None:
        """Commit transaction."""
        pass
    
    def rollback(self) -> None:
        """Rollback transaction."""
        pass
    
    @property
    def in_transaction(self) -> bool:
        """Check if in transaction."""
        return self._transaction_level > 0
    
    # Schema Operations
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        pass
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information."""
        pass
```

### 2. Connection Configuration

Define configuration class for your backend:

```python
# config.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from rhosocial.activerecord.backend.config import BaseConfig

@dataclass
class MyDatabaseConfig(BaseConfig):
    """Configuration for MyDatabase connections."""
    
    host: str = "localhost"
    port: int = 5432
    database: str
    user: Optional[str] = None
    password: Optional[str] = None
    charset: str = "utf8mb4"
    connect_timeout: int = 10
    pool_size: int = 5
    ssl_mode: Optional[str] = None
    
    def to_connection_string(self) -> str:
        """Convert to database connection string."""
        parts = [f"mydatabase://{self.user}"]
        if self.password:
            parts.append(f":{self.password}")
        parts.append(f"@{self.host}:{self.port}/{self.database}")
        return "".join(parts)
    
    def validate(self) -> None:
        """Validate configuration."""
        if not self.database:
            raise ValueError("Database name is required")
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")
```

### 3. SQL Dialect

Implement SQL dialect for database-specific syntax:

```python
# dialect.py
from rhosocial.activerecord.backend.dialect import (
    SQLDialect, ReturningClauseHandler, TypeMapping
)
from typing import Dict, List, Optional

class MyDatabaseDialect(SQLDialect):
    """SQL dialect for MyDatabase."""
    
    def __init__(self):
        super().__init__()
        self.returning_handler = MyDatabaseReturningHandler()
    
    def quote_identifier(self, identifier: str) -> str:
        """Quote table/column names."""
        return f'"{identifier}"'
    
    def get_placeholder(self, name: str = None) -> str:
        """Get parameter placeholder."""
        return "$1" if name else "?"
    
    def format_limit_offset(
        self,
        sql: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> str:
        """Format LIMIT/OFFSET clause."""
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        return sql
    
    def get_type_mappings(self) -> Dict[DatabaseType, TypeMapping]:
        """Get database type mappings."""
        return {
            DatabaseType.INTEGER: TypeMapping("INTEGER"),
            DatabaseType.BIGINT: TypeMapping("BIGINT"),
            DatabaseType.FLOAT: TypeMapping("REAL"),
            DatabaseType.DECIMAL: TypeMapping("DECIMAL({precision},{scale})"),
            DatabaseType.VARCHAR: TypeMapping("VARCHAR({length})"),
            DatabaseType.TEXT: TypeMapping("TEXT"),
            DatabaseType.BOOLEAN: TypeMapping("BOOLEAN"),
            DatabaseType.DATE: TypeMapping("DATE"),
            DatabaseType.DATETIME: TypeMapping("TIMESTAMP"),
            DatabaseType.JSON: TypeMapping("JSONB"),
            DatabaseType.UUID: TypeMapping("UUID"),
        }

class MyDatabaseReturningHandler(ReturningClauseHandler):
    """RETURNING clause handler for MyDatabase."""
    
    @property
    def is_supported(self) -> bool:
        """Check if RETURNING is supported."""
        return True  # Most modern databases support RETURNING
    
    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """Format RETURNING clause."""
        if columns:
            return f" RETURNING {', '.join(columns)}"
        return " RETURNING *"
```

### 4. Type Conversion

Implement type converters for data transformation:

```python
# type_converters.py
from rhosocial.activerecord.backend.type_converters import (
    BaseTypeConverter, TypeRegistry
)
from datetime import datetime, date
from decimal import Decimal
import json

class MyDatabaseTypeConverter(BaseTypeConverter):
    """Type converter for MyDatabase."""
    
    def __init__(self):
        self.registry = TypeRegistry()
        self._register_converters()
    
    def _register_converters(self):
        """Register all type converters."""
        # DateTime converter
        self.registry.register(DateTimeConverter())
        
        # JSON converter
        self.registry.register(JSONConverter())
        
        # Decimal converter
        self.registry.register(DecimalConverter())
        
        # Custom converters
        self.registry.register(MyCustomTypeConverter())

class DateTimeConverter(BaseTypeConverter):
    """Convert datetime objects."""
    
    priority = 10
    
    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        return isinstance(value, (datetime, date))
    
    def to_database(self, value: Any, target_type: Any = None) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        return value
    
    def from_database(self, value: Any, source_type: Any = None) -> datetime:
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

class JSONConverter(BaseTypeConverter):
    """Convert JSON data."""
    
    priority = 5
    
    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        return isinstance(value, (dict, list)) or target_type == "JSON"
    
    def to_database(self, value: Any, target_type: Any = None) -> str:
        return json.dumps(value)
    
    def from_database(self, value: Any, source_type: Any = None) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value
```

### 5. Transaction Management

Implement transaction support:

```python
# transaction.py
from contextlib import contextmanager
from typing import Optional

class TransactionManager:
    """Manage database transactions."""
    
    def __init__(self, backend):
        self.backend = backend
        self._savepoint_counter = 0
    
    @contextmanager
    def transaction(self, isolation_level: Optional[str] = None):
        """Transaction context manager."""
        # Set isolation level if specified
        if isolation_level:
            self.set_isolation_level(isolation_level)
        
        # Begin transaction
        self.backend.begin()
        
        try:
            yield self
            self.backend.commit()
        except Exception as e:
            self.backend.rollback()
            raise
    
    @contextmanager
    def savepoint(self, name: Optional[str] = None):
        """Savepoint context manager."""
        if not name:
            self._savepoint_counter += 1
            name = f"sp_{self._savepoint_counter}"
        
        self.backend.execute(f"SAVEPOINT {name}")
        
        try:
            yield
            self.backend.execute(f"RELEASE SAVEPOINT {name}")
        except Exception:
            self.backend.execute(f"ROLLBACK TO SAVEPOINT {name}")
            raise
    
    def set_isolation_level(self, level: str):
        """Set transaction isolation level."""
        valid_levels = [
            "READ UNCOMMITTED",
            "READ COMMITTED",
            "REPEATABLE READ",
            "SERIALIZABLE"
        ]
        
        if level.upper() not in valid_levels:
            raise ValueError(f"Invalid isolation level: {level}")
        
        self.backend.execute(
            f"SET TRANSACTION ISOLATION LEVEL {level.upper()}"
        )
```

## Feature Detection

### Version-Based Features

```python
# features.py
from typing import Tuple

class FeatureDetector:
    """Detect database features based on version."""
    
    def __init__(self, backend):
        self.backend = backend
        self._version = None
        self._features = {}
    
    @property
    def version(self) -> Tuple[int, int, int]:
        """Get database version."""
        if self._version is None:
            result = self.backend.fetch_one("SELECT VERSION()")
            # Parse version string
            self._version = self._parse_version(result['version'])
        return self._version
    
    def supports_returning(self) -> bool:
        """Check if RETURNING clause is supported."""
        # Example: MyDatabase supports RETURNING since v9.5
        return self.version >= (9, 5, 0)
    
    def supports_cte(self) -> bool:
        """Check if CTEs are supported."""
        return self.version >= (8, 4, 0)
    
    def supports_json(self) -> bool:
        """Check if JSON type is supported."""
        return self.version >= (9, 2, 0)
    
    def supports_window_functions(self) -> bool:
        """Check if window functions are supported."""
        return self.version >= (8, 4, 0)
    
    def _parse_version(self, version_string: str) -> Tuple[int, int, int]:
        """Parse version string into tuple."""
        # Implementation depends on database version format
        parts = version_string.split('.')
        return tuple(int(p) for p in parts[:3])
```

## Testing Requirements

### Current Testing Approach

While the testsuite package is under development, backend packages should:

1. **Create comprehensive backend-specific tests** covering all StorageBackend methods
2. **Follow the three-pillar structure** (feature/realworld/benchmark) in your own tests
3. **Prepare for future testsuite integration** by organizing tests and schemas appropriately

### Backend-Specific Tests

All backends must provide their own tests for backend-specific functionality:

```python
# tests/test_backend.py
import pytest
from rhosocial.activerecord.backend.impl.mydb import MyDatabaseBackend
from rhosocial.activerecord.backend.impl.mydb.config import MyDatabaseConfig

class TestMyDatabaseBackend:
    """Test MyDatabase backend implementation."""
    
    @pytest.fixture
    def backend(self):
        """Create backend instance."""
        config = MyDatabaseConfig(
            database="test_db",
            user="test",
            password="test"
        )
        backend = MyDatabaseBackend(config)
        backend.connect()
        yield backend
        backend.disconnect()
    
    def test_connection(self, backend):
        """Test database connection."""
        assert backend.is_connected()
        assert backend.ping()
    
    def test_execute_query(self, backend):
        """Test query execution."""
        result = backend.execute("SELECT 1 as value")
        assert result.affected == 1
    
    def test_parameterized_query(self, backend):
        """Test parameterized queries."""
        result = backend.fetch_one(
            "SELECT ? as value",
            {"value": "test"}
        )
        assert result['value'] == "test"
    
    def test_transaction(self, backend):
        """Test transaction management."""
        backend.begin()
        assert backend.in_transaction
        
        backend.commit()
        assert not backend.in_transaction
```

### Testsuite Integration (Future)

When the testsuite package is released, backends will need to integrate with it:

```python
# tests/conftest.py
import pytest
from pathlib import Path

def pytest_addoption(parser):
    """Add testsuite execution option."""
    parser.addoption(
        "--run-testsuite",
        action="store_true",
        default=False,
        help="Run standardized testsuite tests"
    )

def pytest_collection_modifyitems(config, items):
    """Control testsuite execution."""
    if not config.getoption("--run-testsuite"):
        skip_testsuite = pytest.mark.skip(
            reason="Need --run-testsuite option to run"
        )
        for item in items:
            if "testsuite" in str(item.fspath):
                item.add_marker(skip_testsuite)

# Schema fixtures for testsuite
@pytest.fixture(scope="module")
def feature_basic_schema(db_connection):
    """Setup basic feature test schema."""
    schema_path = Path("tests/schemas/feature/basic.sql")
    with open(schema_path) as f:
        db_connection.execute(f.read())
    yield
    db_connection.execute("DROP TABLE IF EXISTS users, posts")

@pytest.fixture(scope="module")
def ecommerce_schema(db_connection):
    """Setup e-commerce scenario schema."""
    schema_path = Path("tests/schemas/realworld/ecommerce.sql")
    with open(schema_path) as f:
        db_connection.execute(f.read())
    yield
    db_connection.execute("""
        DROP TABLE IF EXISTS orders, products, customers
    """)
```

Note: Until the testsuite package is released, backends should focus on comprehensive backend-specific testing.

### Running Tests

```bash
# Run backend-specific tests only
pytest

# Run with testsuite for compatibility verification
pytest --run-testsuite

# Generate compatibility report
pytest --run-testsuite --compat-report=html
```

## Performance Optimization

### Connection Pooling

```python
from queue import Queue
import threading

class ConnectionPool:
    """Database connection pool."""
    
    def __init__(self, config, min_size=1, max_size=10):
        self.config = config
        self.min_size = min_size
        self.max_size = max_size
        self._pool = Queue(maxsize=max_size)
        self._size = 0
        self._lock = threading.Lock()
        
        # Pre-create minimum connections
        for _ in range(min_size):
            self._create_connection()
    
    def acquire(self):
        """Acquire connection from pool."""
        try:
            return self._pool.get_nowait()
        except:
            with self._lock:
                if self._size < self.max_size:
                    return self._create_connection()
                else:
                    return self._pool.get()  # Wait for available
    
    def release(self, connection):
        """Return connection to pool."""
        if connection.is_valid():
            self._pool.put(connection)
        else:
            with self._lock:
                self._size -= 1
                if self._size < self.min_size:
                    self._create_connection()
    
    def _create_connection(self):
        """Create new connection."""
        # Implementation specific to database
        pass
```

### Query Optimization

```python
class QueryOptimizer:
    """Optimize SQL queries for specific database."""
    
    def optimize_bulk_insert(self, table: str, records: List[Dict]) -> str:
        """Optimize bulk insert queries."""
        # Use database-specific bulk insert syntax
        # e.g., PostgreSQL COPY, MySQL LOAD DATA INFILE
        pass
    
    def optimize_join(self, query: str) -> str:
        """Optimize JOIN queries."""
        # Add hints or reorder joins based on database
        pass
    
    def add_index_hints(self, query: str, hints: Dict) -> str:
        """Add index hints to query."""
        # Database-specific index hints
        pass
```

## Error Handling

### Database-Specific Errors

```python
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    ConnectionError,
    IntegrityError,
    OperationalError
)

class MyDatabaseErrorHandler:
    """Handle database-specific errors."""
    
    ERROR_CODES = {
        "23505": IntegrityError,  # Unique violation
        "23503": IntegrityError,  # Foreign key violation
        "08006": ConnectionError,  # Connection failure
        "42P01": OperationalError, # Table doesn't exist
    }
    
    def handle_error(self, error):
        """Convert database error to appropriate exception."""
        error_code = getattr(error, 'pgcode', None)  # PostgreSQL example
        
        exception_class = self.ERROR_CODES.get(
            error_code,
            DatabaseError
        )
        
        raise exception_class(str(error)) from error
```

## Package Configuration

### pyproject.toml Setup

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rhosocial-activerecord-mydb"
version = "0.1.0"
description = "MyDatabase backend for rhosocial-activerecord"
readme = "README.md"
requires-python = ">=3.8"
license = "MIT"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
dependencies = [
    "rhosocial-activerecord>=1.0.0,<2.0.0",
    "mydb-driver>=2.0.0",  # Only the native database driver, no ORMs
]

[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    # "rhosocial-activerecord-testsuite>=1.0",  # Add when available
]
dev = [
    "black>=23.0.0",
    "isort>=5.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/rhosocial-activerecord-mydb"
Repository = "https://github.com/yourusername/rhosocial-activerecord-mydb.git"
Issues = "https://github.com/yourusername/rhosocial-activerecord-mydb/issues"

[tool.hatch.build]
include = [
    "src/rhosocial/**/*.py",
    "tests/schemas/**/*.sql",  # Include schema files
    "LICENSE",
    "README.md",
]
```

### README Template

```markdown
# rhosocial-activerecord-mydb

MyDatabase backend for rhosocial-activerecord.

## Installation

```bash
pip install rhosocial-activerecord-mydb
```

## Requirements

- Python 3.8+
- rhosocial-activerecord >= 1.0.0
- mydb-driver >= 2.0.0

## Testing

```bash
# Install test dependencies
pip install -e .[test]

# Run backend-specific tests
pytest

# Future: Run testsuite compatibility tests (when available)
# pytest --run-testsuite

# Future: Generate compatibility report
# pytest --run-testsuite --compat-report=html
```

## Testsuite Compatibility (Future)

Once the testsuite package is released, this backend will target:
- rhosocial-activerecord-testsuite >= 1.0
- Feature Tests compatibility
- Real-world Scenarios support
- Performance Benchmarks

## Usage

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mydb import (
    MyDatabaseBackend,
    MyDatabaseConfig
)

# Configure
config = MyDatabaseConfig(
    host="localhost",
    database="myapp",
    user="user",
    password="password"
)

class User(ActiveRecord):
    __table_name__ = "users"
    name: str

User.configure(config, MyDatabaseBackend)
```

## Features

- ✅ Full CRUD operations
- ✅ Transaction support
- ✅ RETURNING clause
- ✅ CTEs
- ✅ JSON support
- ⚠️ Window functions (v8.4+)
- ❌ Full-text search (planned)

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| host | str | localhost | Database host |
| port | int | 5432 | Database port |
| database | str | - | Database name |
| pool_size | int | 5 | Connection pool size |

## Development

```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with testsuite
pytest --run-testsuite

# Format code
black src tests

# Type checking
mypy src
```
```

## Checklist for New Backends

### Design Principles

- [ ] No ORM dependencies (no SQLAlchemy, Django ORM, etc.)
- [ ] Use native database driver only
- [ ] Direct SQL execution through driver
- [ ] Minimal external dependencies

### Required Implementation

- [ ] StorageBackend abstract methods
- [ ] Connection configuration class
- [ ] SQL dialect with type mappings
- [ ] Type converters for all basic types
- [ ] Transaction management
- [ ] Error handling and mapping
- [ ] Connection pooling (optional but recommended)

### Required Tests

- [ ] Backend-specific unit tests
- [ ] Connection and disconnection
- [ ] Basic CRUD operations
- [ ] Parameterized queries
- [ ] Transaction commit/rollback
- [ ] Type conversion (all types)
- [ ] Error handling
- [ ] Concurrent operations

### Testsuite Integration (Future)

- [ ] Schema fixtures for feature tests
- [ ] Schema fixtures for real-world scenarios
- [ ] Schema fixtures for benchmarks (optional)
- [ ] Testsuite dependency in pyproject.toml (when available)
- [ ] pytest configuration for --run-testsuite
- [ ] Compatibility report generation

### Documentation

- [ ] README with installation and usage
- [ ] Configuration options
- [ ] Feature compatibility matrix
- [ ] Testsuite version compatibility
- [ ] Known limitations
- [ ] Performance considerations

### Package Setup

- [ ] pyproject.toml with dependencies
- [ ] Testsuite version specification
- [ ] Namespace package structure
- [ ] LICENSE file
- [ ] GitHub Actions CI/CD
- [ ] PyPI publication setup