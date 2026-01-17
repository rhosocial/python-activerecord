# Database Configuration

Before defining models, you need to configure the database connection. `rhosocial-activerecord` uses a flexible backend system.

## SQLite Configuration

Currently, SQLite is the primary supported backend for production usage.

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# 1. Create a configuration object
config = SQLiteConnectionConfig(
    database='my_database.db',  # Or ':memory:' for in-memory database
    timeout=5.0
)

# 2. Configure the base ActiveRecord class or a specific Model
# This sets the default backend for all models that inherit from ActiveRecord
ActiveRecord.configure(config, SQLiteBackend)
```

## Shared Backend Instance

In a real application, you want all your models to share the same database connection pool. The framework handles this automatically if you configure the base class or the first model.

If you have multiple databases, you can configure models individually:

```python
# Configure User model to use DB1
User.configure(config1, SQLiteBackend)

# Configure Post model to share the backend with User (Recommended)
# This ensures they use the same connection and transaction context
Post.__backend__ = User.__backend__
Post.__connection_config__ = User.__connection_config__
Post.__backend_class__ = User.__backend_class__
```

## Async Configuration (Preview)

While the core logic is async-ready, the current drivers are synchronous. Async driver support (e.g., `aiosqlite`) is planned for future releases.
