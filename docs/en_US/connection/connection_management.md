# Connection Management

In [Database Configuration](configuration.md), we covered how to configure database connections for individual models or all models. However, in real-world applications, you may need to manage multiple models sharing the same connection, or connect to multiple different databases. The `rhosocial.activerecord.connection` module provides `BackendGroup` and `BackendManager` to simplify these scenarios.

> 💡 **AI Prompt Example**: "I have an application that needs to connect to multiple databases (main database and statistics database), how can I elegantly manage these connections?"

## Table of Contents

1. [BackendGroup - Connection Group](#1-backendgroup---connection-group)
2. [BackendManager - Multi-Database Management](#2-backendmanager---multi-database-management)
3. [Async Support](#3-async-support)
4. [Practical Examples](#4-practical-examples)

## 1. BackendGroup - Connection Group

`BackendGroup` manages database connections for a group of models. It provides a context manager that automatically handles connection establishment and teardown.

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.connection import BackendGroup

# Define models
class User(ActiveRecord):
    name: str
    email: str

class Post(ActiveRecord):
    title: str
    content: str
    user_id: int

# Create connection group
with BackendGroup(
    name="main",
    models=[User, Post],
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=SQLiteBackend,
) as group:
    # Within the context, all models are configured with connections
    user = User(name="John Doe", email="john@example.com")
    user.save()

    post = Post(title="First Post", content="Hello World!", user_id=user.id)
    post.save()

# Connections are automatically closed when exiting the context
```

### Manual Management

For finer-grained control, you can manually call `configure()` and `disconnect()`:

```python
# Create connection group
group = BackendGroup(
    name="main",
    models=[User, Post],
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=SQLiteBackend,
)

# Manually configure connection
group.configure()

# Check connection status
print(group.is_configured())  # True
print(group.is_connected())   # True

# Use models for operations
user = User.find_one(1)

# Manually disconnect
group.disconnect()
```

### Adding Models Dynamically

```python
group = BackendGroup(
    name="main",
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=SQLiteBackend,
)

# Add models dynamically (must be before configure)
group.add_model(User).add_model(Post)

group.configure()
```

### Connection Health Check

```python
with BackendGroup(...) as group:
    # Check overall connection status
    if group.is_connected():
        print("All connections are healthy")

    # Check connection status for each model
    status = group.ping()
    for model, is_connected in status.items():
        print(f"{model.__name__}: {'OK' if is_connected else 'Disconnected'}")
```

## 2. BackendManager - Multi-Database Management

When you need to connect to multiple databases (e.g., main database + statistics database, or master-slave architecture), you can use `BackendManager`.

### Basic Usage

```python
from rhosocial.activerecord.connection import BackendManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# Create manager
manager = BackendManager()

# Create main database connection group
manager.create_group(
    name="main",
    config=SQLiteConnectionConfig(database="main.db"),
    backend_class=SQLiteBackend,
    models=[User, Post],
)

# Create statistics database connection group
manager.create_group(
    name="stats",
    config=SQLiteConnectionConfig(database="stats.db"),
    backend_class=SQLiteBackend,
    models=[Log, Metric],
)

# Configure all connections
manager.configure_all()

# Use models
user = User.find_one(1)
log = Log.create(action="login", user_id=user.id)

# Disconnect all connections
manager.disconnect_all()
```

### As Context Manager

```python
with BackendManager() as manager:
    manager.create_group(
        name="main",
        config=SQLiteConnectionConfig(database="main.db"),
        backend_class=SQLiteBackend,
        models=[User, Post],
    )

    manager.create_group(
        name="stats",
        config=SQLiteConnectionConfig(database="stats.db"),
        backend_class=SQLiteBackend,
        models=[Log, Metric],
    )

    # Within the context, all connections are configured
    user = User.find_one(1)
    log = Log.create(action="login", user_id=user.id)

# All connections are automatically closed on exit
```

### Managing Connection Groups

```python
manager = BackendManager()

# Create connection group
manager.create_group("main", config=config, backend_class=SQLiteBackend, models=[User])

# Check if exists
print(manager.has_group("main"))  # True

# Get connection group
group = manager.get_group("main")

# Get all group names
print(manager.get_group_names())  # ['main']

# Remove connection group (will automatically disconnect)
manager.remove_group("main")

# Check all connection status
print(manager.is_connected())  # True/False
```

## 3. Async Support

`rhosocial.activerecord.connection` provides full async support, following the project's sync-async parity principle.

### AsyncBackendGroup

```python
from rhosocial.activerecord.connection import AsyncBackendGroup
from rhosocial.activerecord.model import AsyncActiveRecord

class User(AsyncActiveRecord):
    name: str
    email: str

# Use async connection group
async with AsyncBackendGroup(
    name="main",
    models=[User],
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=AsyncSQLiteBackend,  # Requires async backend
) as group:
    user = await User.find_one(1)
    user.name = "New Name"
    await user.save()
```

### AsyncBackendManager

```python
from rhosocial.activerecord.connection import AsyncBackendManager

async with AsyncBackendManager() as manager:
    manager.create_group(
        name="main",
        config=SQLiteConnectionConfig(database="main.db"),
        backend_class=AsyncSQLiteBackend,
        models=[User, Post],
    )

    manager.create_group(
        name="stats",
        config=SQLiteConnectionConfig(database="stats.db"),
        backend_class=AsyncSQLiteBackend,
        models=[Log, Metric],
    )

    # Use models
    user = await User.find_one(1)
    log = await Log.create(action="login", user_id=user.id)
```

## 4. Practical Examples

### CLI Tool Scenario

In CLI tools, using `BackendGroup` ensures connections are properly closed when the script ends:

```python
# scripts/migrate_users.py
from rhosocial.activerecord.connection import BackendGroup
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from app.models import User, Post

def migrate_users():
    """Script to migrate user data."""
    with BackendGroup(
        name="migration",
        models=[User, Post],
        config=SQLiteConnectionConfig(database="production.db"),
        backend_class=SQLiteBackend,
    ):
        for user in User.query().all():
            # Execute migration logic
            user.migrated = True
            user.save()
            print(f"Migrated user: {user.name}")

if __name__ == "__main__":
    migrate_users()
```

### Scheduled Task Scenario

```python
# tasks/daily_report.py
from rhosocial.activerecord.connection import BackendManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from app.models import User, Order, Report

def generate_daily_report():
    """Scheduled task to generate daily reports."""
    with BackendManager() as manager:
        # Main database: read user and order data
        manager.create_group(
            name="main",
            config=SQLiteConnectionConfig(database="main.db"),
            backend_class=SQLiteBackend,
            models=[User, Order],
        )

        # Statistics database: write reports
        manager.create_group(
            name="stats",
            config=SQLiteConnectionConfig(database="stats.db"),
            backend_class=SQLiteBackend,
            models=[Report],
        )

        # Calculate today's orders
        today_orders = Order.query().where(
            Order.c.created_at >= today_start()
        ).all()

        # Generate report
        report = Report(
            date=today(),
            order_count=len(today_orders),
            total_amount=sum(o.amount for o in today_orders),
        )
        report.save()
```

### Web Application Scenario

In web frameworks like FastAPI, you can manage connections in the application lifecycle:

```python
# app/database.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from rhosocial.activerecord.connection import AsyncBackendManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteConnectionConfig

manager = AsyncBackendManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Configure connections on startup
    manager.create_group(
        name="main",
        config=SQLiteConnectionConfig(database="app.db"),
        backend_class=AsyncSQLiteBackend,
        models=[User, Post],
    )
    await manager.configure_all()

    yield

    # Disconnect on shutdown
    await manager.disconnect_all()

app = FastAPI(lifespan=lifespan)
```

### Multi-Tenant Scenario

```python
from rhosocial.activerecord.connection import BackendManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

class TenantManager:
    """Multi-tenant connection manager."""

    def __init__(self):
        self.manager = BackendManager()

    def setup_tenant(self, tenant_id: str, models: list):
        """Create independent database connection for tenant."""
        db_path = f"tenants/{tenant_id}.db"
        self.manager.create_group(
            name=tenant_id,
            config=SQLiteConnectionConfig(database=db_path),
            backend_class=SQLiteBackend,
            models=models,
        )
        self.manager.configure_all()

    def get_tenant_backend(self, tenant_id: str, model):
        """Get backend instance for tenant."""
        group = self.manager.get_group(tenant_id)
        return group.get_backend(model) if group else None

    def remove_tenant(self, tenant_id: str):
        """Remove tenant connection."""
        self.manager.remove_group(tenant_id)

# Usage example
tenant_manager = TenantManager()
tenant_manager.setup_tenant("company_a", [User, Post])
tenant_manager.setup_tenant("company_b", [User, Post])
```

## API Quick Reference

### BackendGroup

| Method | Description |
|--------|-------------|
| `configure()` | Configure connection (supports callable config) |
| `disconnect()` | Disconnect |
| `is_configured()` | Check if configured |
| `is_connected()` | Check if connection is healthy |
| `ping()` | Check connection status for each model |
| `add_model(model)` | Add model (must call before configure) |
| `get_backend(model)` | Get backend instance for model |

### BackendManager

| Method | Description |
|--------|-------------|
| `create_group(name, ...)` | Create connection group |
| `get_group(name)` | Get connection group |
| `has_group(name)` | Check if connection group exists |
| `remove_group(name)` | Remove connection group |
| `configure_all()` | Configure all connections |
| `disconnect_all()` | Disconnect all connections |
| `is_connected()` | Check if all connections are healthy |
| `get_group_names()` | Get all group names |

---

## Next Steps

You've mastered the basics of connection management! You can now explore:

- **[FastAPI Integration](../scenarios/fastapi.md)**: Using connection management in web applications
- **[Testing Strategies](../testing/strategies.md)**: How to manage connections in tests
- **[Custom Backend](../backend/custom_backend.md)**: Implementing backends for other databases
