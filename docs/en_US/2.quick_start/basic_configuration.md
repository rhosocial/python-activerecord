# Basic Configuration

This guide covers how to configure rhosocial ActiveRecord with SQLite for your first project.

## Setting Up a SQLite Connection

rhosocial ActiveRecord uses a connection configuration object to establish database connections. For SQLite, this is straightforward as it only requires a file path.

### Basic SQLite Configuration

```python
from rhosocial.activerecord.backend.typing import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord import ActiveRecord

# Configure with a file-based SQLite database
config = ConnectionConfig(database='database.sqlite3')

# Configure ActiveRecord to use this connection
ActiveRecord.configure(config, backend_class=SQLiteBackend)
```

This configuration will:
1. Create a SQLite database file named `database.sqlite3` in your current directory (if it doesn't exist)
2. Configure all ActiveRecord models to use this connection by default

### In-Memory SQLite Database

For testing or temporary data, you can use an in-memory SQLite database:

```python
# In-memory database configuration
config = ConnectionConfig(database=':memory:')
ActiveRecord.configure(config, backend_class=SQLiteBackend)
```

> **Note**: In-memory databases exist only for the duration of the connection and are deleted when the connection is closed.

## Configuration Options

The `ConnectionConfig` class accepts several parameters to customize your connection:

```python
config = ConnectionConfig(
    database='database.sqlite3',  # Database file path
    pragmas={                     # SQLite-specific pragmas
        'journal_mode': 'WAL',    # Write-Ahead Logging for better concurrency
        'foreign_keys': 'ON',     # Enable foreign key constraints
    },
    timeout=30.0,                # Connection timeout in seconds
    isolation_level=None,        # Use SQLite's autocommit mode
)
```

### Common SQLite Pragmas

SQLite pragmas are configuration options that control the operation of the SQLite library. Some useful pragmas include:

- `journal_mode`: Controls how the journal file is managed (`DELETE`, `TRUNCATE`, `PERSIST`, `MEMORY`, `WAL`, `OFF`)
- `foreign_keys`: Enables or disables foreign key constraint enforcement (`ON`, `OFF`)
- `synchronous`: Controls how aggressively SQLite writes to disk (`OFF`, `NORMAL`, `FULL`, `EXTRA`)
- `cache_size`: Sets the number of pages to use in the in-memory cache

## Global vs. Model-Specific Configuration

You can configure all ActiveRecord models to use the same connection, or configure specific models to use different connections.

### Global Configuration

```python
# Configure all models to use this connection by default
ActiveRecord.configure(config, backend_class=SQLiteBackend)
```

### Model-Specific Configuration

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int
    name: str
    email: str

# Configure only the User model to use this connection
User.configure(config, backend_class=SQLiteBackend)
```

## Next Steps

Now that you have configured your database connection, proceed to [First Model Example](first_model_example.md) to learn how to create and use your first ActiveRecord model.

## Next Steps

Now that you have configured your database connection, proceed to [First Model Example](first_model_example.md) to learn how to create and use your first ActiveRecord model.