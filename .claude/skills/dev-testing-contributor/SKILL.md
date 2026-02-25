---
name: dev-testing-contributor
description: Testing architecture for rhosocial-activerecord framework contributors - Provider pattern, Testsuite architecture, sync/async parity, and protocol-based feature detection
license: MIT
compatibility: opencode
metadata:
  category: testing
  level: intermediate
  audience: developers
  order: 6
  prerequisites:
    - dev-sync-async-parity
    - dev-backend-development
---

# Testing Architecture for Contributors

This guide covers the testing architecture for rhosocial-activerecord framework development, including the Provider pattern, Testsuite architecture, and protocol-based feature detection.

## Testsuite Architecture

The testsuite follows a structured architecture that ensures consistency, maintainability, and proper sync/async parity.

```
tests/
├── rhosocial/
│   └── activerecord_test/
│       ├── feature/
│       │   ├── basic/
│       │   │   ├── schema/
│       │   │   │   └── users.sql
│       │   │   └── test_*.py
│       │   ├── query/
│       │   │   ├── schema/
│       │   │   └── test_*.py
│       │   └── ...
│       └── unit/
└── conftest.py
```

## Provider Pattern

Tests use the Provider pattern to abstract backend setup. This allows tests to run against different backends without modification.

### Backend Provider Interface

```python
# tests/providers/base.py
from typing import Protocol, Type, Tuple, Dict, Any


class BackendProvider(Protocol):
    """Protocol for backend test providers."""
    
    @property
    def sync_backend_class(self) -> Type[StorageBackend]:
        """Synchronous backend class."""
        ...
    
    @property
    def async_backend_class(self) -> Type[AsyncStorageBackend]:
        """Asynchronous backend class."""
        ...
    
    def get_connection_config(self) -> Any:
        """Get connection configuration."""
        ...
    
    def setup_models(self, scenario: str) -> Tuple[Type, ...]:
        """Setup models for given scenario."""
        ...
```

### SQLite Provider Implementation

```python
# tests/providers/sqlite.py
import pytest
from typing import Tuple, Type

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from tests.providers.base import BackendProvider


class SQLiteProvider:
    """SQLite backend provider for testing."""
    
    @property
    def sync_backend_class(self) -> Type[SQLiteBackend]:
        return SQLiteBackend
    
    @property
    def async_backend_class(self) -> Type[SQLiteBackend]:
        return SQLiteBackend
    
    def get_connection_config(self, test_db: str = ":memory:"):
        return SQLiteConnectionConfig(database=test_db)
    
    def setup_models(
        self,
        scenario: str,
        backend: SQLiteBackend
    ) -> Tuple[Type, ...]:
        """Setup models based on scenario."""
        if scenario == "basic":
            return self._setup_basic_models(backend)
        elif scenario == "query":
            return self._setup_query_models(backend)
        elif scenario == "relation":
            return self._setup_relation_models(backend)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
    
    def _setup_basic_models(
        self,
        backend: SQLiteBackend
    ) -> Tuple[Type[ActiveRecord], ...]:
        """Setup basic CRUD models."""
        
        class User(ActiveRecord):
            __table_name__ = 'users'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            name: str = Field(max_length=100)
            email: str = Field(max_length=255)
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'name': 'VARCHAR(100) NOT NULL',
                'email': 'VARCHAR(255) NOT NULL',
            }
        
        class Profile(ActiveRecord):
            __table_name__ = 'profiles'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            user_id: int = Field()
            bio: Optional[str] = Field(default=None)
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'user_id': 'INTEGER NOT NULL',
                'bio': 'TEXT',
            }
        
        return (User, Profile)
    
    def _setup_query_models(
        self,
        backend: SQLiteBackend
    ) -> Tuple[Type[ActiveRecord], ...]:
        """Setup query testing models."""
        
        class Order(ActiveRecord):
            __table_name__ = 'orders'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            user_id: int = Field()
            total: float = Field()
            status: str = Field(default='pending')
            created_at: datetime = Field(default_factory=datetime.utcnow)
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'user_id': 'INTEGER NOT NULL',
                'total': 'REAL NOT NULL',
                'status': 'TEXT DEFAULT "pending"',
                'created_at': 'TEXT',
            }
        
        class OrderItem(ActiveRecord):
            __table_name__ = 'order_items'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            order_id: int = Field()
            product_name: str = Field()
            quantity: int = Field()
            price: float = Field()
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'order_id': 'INTEGER NOT NULL',
                'product_name': 'TEXT NOT NULL',
                'quantity': 'INTEGER NOT NULL',
                'price': 'REAL NOT NULL',
            }
        
        return (Order, OrderItem)
    
    def _setup_relation_models(
        self,
        backend: SQLiteBackend
    ) -> Tuple[Type[ActiveRecord], ...]:
        """Setup relation testing models."""
        
        class Author(ActiveRecord):
            __table_name__ = 'authors'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            name: str = Field()
            bio: Optional[str] = Field(default=None)
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'name': 'TEXT NOT NULL',
                'bio': 'TEXT',
            }
        
        class Book(ActiveRecord):
            __table_name__ = 'books'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            author_id: int = Field()
            title: str = Field()
            published_year: int = Field()
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'author_id': 'INTEGER NOT NULL',
                'title': 'TEXT NOT NULL',
                'published_year': 'INTEGER',
            }
        
        class BookCategory(ActiveRecord):
            __table_name__ = 'book_categories'
            __backend__ = backend
            
            id: int = Field(primary_key=True)
            book_id: int = Field()
            category: str = Field()
            
            __mapping__ = {
                'id': 'INTEGER PRIMARY KEY',
                'book_id': 'INTEGER NOT NULL',
                'category': 'TEXT NOT NULL',
            }
        
        return (Author, Book, BookCategory)
```

## Sync/Async Test Parity

Each synchronous test must have a corresponding asynchronous test with identical method names.

### Test Fixture Structure

```python
# tests/conftest.py
import pytest
from typing import Generator


@pytest.fixture
def sqlite_provider() -> SQLiteProvider:
    """Provide SQLite test backend."""
    return SQLiteProvider()


@pytest.fixture
def backend(sqlite_provider) -> Generator[SQLiteBackend, None, None]:
    """Create test backend with in-memory database."""
    config = sqlite_provider.get_connection_config(":memory:")
    backend = sqlite_provider.sync_backend_class(config)
    backend.connect()
    
    # Create tables
    yield backend
    
    backend.disconnect()


@pytest.fixture
def async_backend(sqlite_provider) -> Generator[AsyncSQLiteBackend, None, None]:
    """Create async test backend with in-memory database."""
    config = sqlite_provider.get_connection_config(":memory:")
    backend = sqlite_provider.async_backend_class(config)
    
    import asyncio
    asyncio.run(backend.connect())
    
    yield backend
    
    asyncio.run(backend.disconnect())


@pytest.fixture
def basic_fixtures(
    backend: SQLiteBackend,
    sqlite_provider: SQLiteProvider
) -> Tuple[Type[ActiveRecord], Type[ActiveRecord]]:
    """Setup basic test fixtures."""
    User, Profile = sqlite_provider.setup_models("basic", backend)
    
    # Create tables
    backend.execute(User.__ddl_create_table__)
    backend.execute(Profile.__ddl_create_table__)
    
    return (User, Profile)


@pytest.fixture
async def async_basic_fixtures(
    async_backend: AsyncSQLiteBackend,
    sqlite_provider: SQLiteProvider
) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
    """Setup async basic test fixtures."""
    AsyncUser, AsyncProfile = sqlite_provider.setup_async_models(
        "basic", async_backend
    )
    
    # Create tables asynchronously
    await async_backend.execute(AsyncUser.__ddl_create_table__)
    await async_backend.execute(AsyncProfile.__ddl_create_table__)
    
    return (AsyncUser, AsyncProfile)
```

### Synchronous Test Class

```python
# tests/rhosocial/activerecord_test/feature/basic/test_crud.py
import pytest
from typing import Tuple, Type

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import IntegerField, StringField


class TestBasicCRUD:
    """Test basic CRUD operations (Synchronous)."""
    
    def test_create_record(self, basic_fixtures):
        """Test creating a new record."""
        User, Profile = basic_fixtures
        
        # Create user
        user = User(name="John Doe", email="john@example.com")
        user.save()
        
        assert user.id is not None
        assert user.id > 0
        
        # Retrieve
        found = User.find_one(User.c.id == user.id)
        assert found is not None
        assert found.name == "John Doe"
        assert found.email == "john@example.com"
    
    def test_update_record(self, basic_fixtures):
        """Test updating a record."""
        User, Profile = basic_fixtures
        
        user = User(name="John Doe", email="john@example.com")
        user.save()
        
        # Update
        user.name = "Jane Doe"
        user.save()
        
        # Verify
        found = User.find_one(User.c.id == user.id)
        assert found.name == "Jane Doe"
    
    def test_delete_record(self, basic_fixtures):
        """Test deleting a record."""
        User, Profile = basic_fixtures
        
        user = User(name="To Delete", email="delete@example.com")
        user.save()
        user_id = user.id
        
        # Delete
        user.delete()
        
        # Verify
        found = User.find_one(User.c.id == user_id)
        assert found is None
    
    def test_query_with_where(self, basic_fixtures):
        """Test query with WHERE clause."""
        User, Profile = basic_fixtures
        
        # Create multiple users
        User(name="Alice", email="alice@example.com").save()
        User(name="Bob", email="bob@example.com").save()
        User(name="Charlie", email="charlie@example.com").save()
        
        # Query with WHERE
        users = User.query().where(
            User.c.name.like("B%")
        ).all()
        
        assert len(users) == 1
        assert users[0].name == "Bob"
```

### Asynchronous Test Class

```python
# tests/rhosocial/activerecord_test/feature/basic/test_async_crud.py
import pytest
from typing import Tuple, Type


class TestAsyncBasicCRUD:
    """Test basic CRUD operations (Asynchronous) - method names identical to sync."""
    
    @pytest.mark.asyncio
    async def test_create_record(self, async_basic_fixtures):
        """Test creating a new record asynchronously."""
        AsyncUser, AsyncProfile = async_basic_fixtures
        
        # Create user
        user = AsyncUser(name="John Doe", email="john@example.com")
        await user.save()
        
        assert user.id is not None
        assert user.id > 0
        
        # Retrieve asynchronously
        found = await AsyncUser.find_one(AsyncUser.c.id == user.id)
        assert found is not None
        assert found.name == "John Doe"
        assert found.email == "john@example.com"
    
    @pytest.mark.asyncio
    async def test_update_record(self, async_basic_fixtures):
        """Test updating a record asynchronously."""
        AsyncUser, AsyncProfile = async_basic_fixtures
        
        user = AsyncUser(name="John Doe", email="john@example.com")
        await user.save()
        
        # Update
        user.name = "Jane Doe"
        await user.save()
        
        # Verify
        found = await AsyncUser.find_one(AsyncUser.c.id == user.id)
        assert found.name == "Jane Doe"
    
    @pytest.mark.asyncio
    async def test_delete_record(self, async_basic_fixtures):
        """Test deleting a record asynchronously."""
        AsyncUser, AsyncProfile = async_basic_fixtures
        
        user = AsyncUser(name="To Delete", email="delete@example.com")
        await user.save()
        user_id = user.id
        
        # Delete
        await user.delete()
        
        # Verify
        found = await AsyncUser.find_one(AsyncUser.c.id == user_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_query_with_where(self, async_basic_fixtures):
        """Test query with WHERE clause asynchronously."""
        AsyncUser, AsyncProfile = async_basic_fixtures
        
        # Create multiple users
        await AsyncUser(name="Alice", email="alice@example.com").save()
        await AsyncUser(name="Bob", email="bob@example.com").save()
        await AsyncUser(name="Charlie", email="charlie@example.com").save()
        
        # Query with WHERE
        users = await AsyncUser.query().where(
            AsyncUser.c.name.like("B%")
        ).all()
        
        assert len(users) == 1
        assert users[0].name == "Bob"
```

## Protocol-Based Feature Detection

Tests use protocols to declare backend feature requirements and skip tests when features are not supported.

### Feature Protocol Definition

```python
# tests/protocols.py
from typing import Protocol, runtime_checkable


@runtime_checkable
class CTESupport(Protocol):
    """Protocol indicating CTE support."""
    
    def supports_cte(self) -> bool: ...
    
    def supports_recursive_cte(self) -> bool: ...


@runtime_checkable
class WindowFunctionSupport(Protocol):
    """Protocol indicating window function support."""
    
    def supports_window_functions(self) -> bool: ...


@runtime_checkable
class TransactionSupport(Protocol):
    """Protocol indicating transaction support."""
    
    def supports_transactions(self) -> bool: ...
    
    def begin_transaction(self) -> None: ...
    
    def commit(self) -> None: ...
    
    def rollback(self) -> None: ...
```

### Using Protocols in Tests

```python
# tests/rhosocial/activerecord_test/feature/query/test_cte.py
import pytest
from typing import Tuple


class TestCTEQueries:
    """Test CTE (Common Table Expression) queries."""
    
    def test_basic_cte(self, query_fixtures):
        """Test basic CTE query."""
        Order, OrderItem = query_fixtures
        
        # Skip if backend doesn't support CTEs
        backend = Order.__backend__
        if not isinstance(backend, CTESupport):
            pytest.skip(f"Backend {type(backend).__name__} doesn't support CTEs")
        
        # CTE query
        query = Order.query().with_cte(
            "high_value_orders",
            Order.query().where(Order.c.total > 1000)
        ).join(
            "high_value_orders",
            Order.c.user_id == Order.c.id
        )
        
        results = query.all()
        assert results is not None
    
    def test_recursive_cte(self, query_fixtures):
        """Test recursive CTE for hierarchical data."""
        Category = query_fixtures
        
        # Skip if backend doesn't support recursive CTEs
        backend = Category.__backend__
        if not isinstance(backend, CTESupport):
            pytest.skip(
                f"Backend {type(backend).__name__} doesn't support CTEs"
            )
        if not backend.supports_recursive_cte():
            pytest.skip("Backend doesn't support recursive CTEs")
        
        # Recursive CTE for tree structure
        query = Category.query().with_recursive_cte(
            "category_tree",
            Category.query().where(Category.c.parent_id.is_null()),
            Category.query().join(
                "category_tree",
                Category.c.parent_id == Category.c.id
            )
        )
        
        results = query.all()
        assert results is not None


class TestAsyncCTEQueries:
    """Test CTE queries (Asynchronous) - method names identical to sync."""
    
    @pytest.mark.asyncio
    async def test_basic_cte(self, async_query_fixtures):
        """Test basic CTE query asynchronously."""
        AsyncOrder, AsyncOrderItem = async_query_fixtures
        
        # Skip if backend doesn't support CTEs
        backend = AsyncOrder.__backend__
        if not isinstance(backend, CTESupport):
            pytest.skip(f"Backend {type(backend).__name__} doesn't support CTEs")
        
        # CTE query
        query = AsyncOrder.query().with_cte(
            "high_value_orders",
            AsyncOrder.query().where(AsyncOrder.c.total > 1000)
        ).join(
            "high_value_orders",
            AsyncOrder.c.user_id == AsyncOrder.c.id
        )
        
        results = await query.all()
        assert results is not None
    
    @pytest.mark.asyncio
    async def test_recursive_cte(self, async_query_fixtures):
        """Test recursive CTE for hierarchical data asynchronously."""
        AsyncCategory = async_query_fixtures
        
        # Skip if backend doesn't support recursive CTEs
        backend = AsyncCategory.__backend__
        if not isinstance(backend, CTESupport):
            pytest.skip(
                f"Backend {type(backend).__name__} doesn't support CTEs"
            )
        if not backend.supports_recursive_cte():
            pytest.skip("Backend doesn't support recursive CTEs")
        
        # Recursive CTE for tree structure
        query = AsyncCategory.query().with_recursive_cte(
            "category_tree",
            AsyncCategory.query().where(
                AsyncCategory.c.parent_id.is_null()
            ),
            AsyncCategory.query().join(
                "category_tree",
                AsyncCategory.c.parent_id == AsyncCategory.c.id
            )
        )
        
        results = await query.all()
        assert results is not None
```

## Schema File Management

Test schemas are defined in SQL files and shared between sync and async tests.

### Schema File Structure

```sql
-- tests/rhosocial/activerecord_test/feature/query/schema/query.sql
-- Shared schema for query tests

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total REAL NOT NULL DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
```

### Loading Schema in Fixtures

```python
# tests/providers/sqlite.py
class SQLiteProvider:
    """SQLite backend provider for testing."""
    
    SCHEMA_FILES = {
        "basic": "tests/rhosocial/activerecord_test/feature/basic/schema/basic.sql",
        "query": "tests/rhosocial/activerecord_test/feature/query/schema/query.sql",
        "relation": "tests/rhosocial/activerecord_test/feature/relation/schema/relation.sql",
    }
    
    def load_schema(self, backend: SQLiteBackend, scenario: str) -> None:
        """Load SQL schema for scenario."""
        schema_file = self.SCHEMA_FILES.get(scenario)
        if schema_file:
            with open(schema_file, 'r') as f:
                sql = f.read()
            backend.execute(sql)
    
    def setup_models(
        self,
        scenario: str,
        backend: SQLiteBackend
    ) -> Tuple[Type, ...]:
        """Setup models and load schema."""
        self.load_schema(backend, scenario)
        
        # Define models matching schema
        if scenario == "basic":
            return self._define_basic_models(backend)
        elif scenario == "query":
            return self._define_query_models(backend)
        elif scenario == "relation":
            return self._define_relation_models(backend)
        
        return ()
```

## Test Execution

### Running Tests

```bash
# Run all tests with PYTHONPATH set
PYTHONPATH=src pytest tests/ -v

# Run specific test category
PYTHONPATH=src pytest tests/rhosocial/activerecord_test/feature/basic/ -v

# Run with coverage
PYTHONPATH=src pytest tests/ --cov=rhosocial.activerecord --cov-report=html

# Run async tests only
PYTHONPATH=src pytest tests/ -k "async" -v
```

### Test Configuration

```python
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

## Best Practices

1. **Fixture Parity**: Each sync fixture must have a corresponding async fixture with `async_` prefix
2. **Schema Sharing**: Schema files are shared between sync and async tests
3. **Protocol Detection**: Use protocols to declare backend feature requirements
4. **Provider Pattern**: Tests get models from providers, not directly
5. **Method Naming**: Async test methods use identical names to sync versions
6. **Test Isolation**: Each test should work independently with fresh database state

## Common Issues

### Circular Imports

If encountering circular imports in tests:

```python
# Use TYPE_CHECKING for imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.providers.base import BackendProvider
```

### Backend Configuration

Ensure backend is properly configured before tests:

```python
@pytest.fixture(autouse=True)
def setup_backend(backend):
    """Automatically setup backend for all tests."""
    # Ensure tables exist
    backend.execute(User.__ddl_create_table__)
    yield
    # Cleanup if needed
```

### Async Fixtures

For async fixtures that need cleanup:

```python
@pytest.fixture
async def async_cleanup_fixture(async_backend):
    """Async fixture with cleanup."""
    yield async_backend
    # Cleanup after test
    await async_backend.execute("DROP TABLE IF EXISTS test_table")
```

## Writing New Tests

1. **Create schema file** in appropriate `schema/` directory
2. **Update provider** to load schema and define models
3. **Create sync test class** in `test_*.py`
4. **Create async test class** with `Async` prefix and `@pytest.mark.asyncio`
5. **Add fixtures** to `conftest.py`
6. **Verify protocol requirements** if using special features

Example:

```python
# tests/rhosocial/activerecord_test/feature/new_feature/test_new.py


class TestNewFeature:
    """Test new feature (Synchronous)."""
    
    def test_feature_x(self, fixtures):
        """Test feature X."""
        Model1, Model2 = fixtures
        # Test implementation
        pass


class TestAsyncNewFeature:
    """Test new feature (Asynchronous) - same method names."""
    
    @pytest.mark.asyncio
    async def test_feature_x(self, async_fixtures):
        """Test feature X asynchronously."""
        AsyncModel1, AsyncModel2 = async_fixtures
        # Async test implementation
        pass
```
