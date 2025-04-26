# SQLite Support

rhosocial ActiveRecord provides excellent support for SQLite, a self-contained, serverless, zero-configuration, transactional SQL database engine. This document covers the specific features, configuration options, and considerations when using rhosocial ActiveRecord with SQLite.

## Overview

SQLite is a C library that provides a lightweight disk-based database that doesn't require a separate server process. It's ideal for development, testing, and small to medium-sized applications. rhosocial ActiveRecord's SQLite backend provides a consistent interface to SQLite databases while respecting SQLite's unique characteristics.

## Features

- Full CRUD operations support
- Transaction management with SQLite's isolation levels
- Support for SQLite-specific pragmas and configurations
- In-memory database support for testing
- File-based database with simple configuration
- Support for SQLite's JSON functions (for SQLite 3.9+)
- Automatic handling of SQLite's type affinity system

## Configuration

To use SQLite with rhosocial ActiveRecord, you need to configure your model with the SQLite backend:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class User(ActiveRecord):
    pass

# Configure the model to use SQLite backend with a file database
User.configure(
    ConnectionConfig(
        database='database.sqlite3',  # Path to SQLite database file
        # Optional parameters
        pragmas={  # SQLite PRAGMA settings
            'journal_mode': 'WAL',  # Write-Ahead Logging for better concurrency
            'foreign_keys': 'ON',   # Enable foreign key constraints
            'synchronous': 'NORMAL',  # Synchronous setting (OFF, NORMAL, FULL, EXTRA)
            'cache_size': 10000,    # Cache size in pages
            'temp_store': 'MEMORY'  # Store temporary tables and indices in memory
        }
    ),
    SQLiteBackend
)

# Or use an in-memory database for testing
User.configure(
    ConnectionConfig(
        database=':memory:',  # In-memory database
        pragmas={'foreign_keys': 'ON'}
    ),
    SQLiteBackend
)
```

## SQLite Pragmas

SQLite uses PRAGMA statements to modify the operation of the SQLite library. rhosocial ActiveRecord allows you to configure these pragmas through the `pragmas` parameter in the `ConnectionConfig`.

Common pragmas include:

- `journal_mode`: Controls how the journal file is managed (DELETE, TRUNCATE, PERSIST, MEMORY, WAL, OFF)
- `foreign_keys`: Enables or disables foreign key constraints (ON, OFF)
- `synchronous`: Controls how aggressively SQLite writes data to disk (OFF, NORMAL, FULL, EXTRA)
- `cache_size`: Number of pages to use for the database cache
- `temp_store`: Controls where temporary tables and indices are stored (DEFAULT, FILE, MEMORY)
- `busy_timeout`: Maximum time to wait when the database is locked, in milliseconds

## Transactions

rhosocial ActiveRecord provides transaction support for SQLite, with some limitations due to SQLite's transaction model:

```python
# Start a transaction
with User.transaction():
    user = User.find(1)
    user.name = 'New Name'
    user.save()
```

SQLite supports the following isolation levels:

- `DEFERRED` (default): Defers locking the database until the first read/write operation
- `IMMEDIATE`: Locks the database immediately, preventing other connections from writing
- `EXCLUSIVE`: Locks the database immediately, preventing other connections from reading or writing

You can specify the isolation level when starting a transaction:

```python
with User.transaction(isolation_level='IMMEDIATE'):
    # Operations that require immediate locking
    pass
```

## In-Memory Databases

SQLite supports in-memory databases, which are perfect for testing or temporary data processing. To use an in-memory database, set the `database` parameter to `:memory:`:

```python
User.configure(
    ConnectionConfig(database=':memory:'),
    SQLiteBackend
)
```

Note that in-memory databases exist only for the duration of the connection. When the connection is closed, the database is deleted.

## Data Type Mapping

SQLite uses a dynamic type system called "type affinity." rhosocial ActiveRecord maps Python types to SQLite storage classes as follows:

| Python Type | SQLite Storage Class |
|-------------|---------------------|
| int         | INTEGER             |
| float       | REAL                |
| str         | TEXT                |
| bytes       | BLOB                |
| bool        | INTEGER (0 or 1)    |
| datetime    | TEXT (ISO format)   |
| date        | TEXT (ISO format)   |
| time        | TEXT (ISO format)   |
| Decimal     | TEXT                |
| dict/list   | TEXT (JSON)         |
| None        | NULL                |

## Performance Considerations

- Use WAL (Write-Ahead Logging) journal mode for better concurrency
- Adjust cache_size pragma for better performance with larger databases
- Use transactions for multiple operations to improve performance
- Consider using MEMORY journal mode for read-only databases
- For better write performance, consider reducing the synchronous pragma level (with caution)

## Limitations

- Limited concurrency compared to client-server databases
- No built-in user authentication or access control
- Limited to 2GB file size on some file systems
- Some SQL features not supported (e.g., RIGHT OUTER JOIN, FULL OUTER JOIN)
- No native support for some data types (e.g., UUID, network addresses)

## Requirements

- Python 3.7+
- sqlite3 module (included in Python standard library)

## Best Practices

1. **Enable foreign keys**: Always enable foreign key constraints for data integrity
2. **Use WAL mode**: For applications with concurrent access, use WAL journal mode
3. **Set busy timeout**: Configure a reasonable busy timeout to handle concurrent access
4. **Use transactions**: Group related operations in transactions for better performance and consistency
5. **Regular maintenance**: Consider running VACUUM periodically to optimize database size
6. **Backup strategy**: Implement a backup strategy for file-based databases

## Example: Complete Configuration

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class User(ActiveRecord):
    pass

# Comprehensive SQLite configuration
User.configure(
    ConnectionConfig(
        database='app_data.sqlite3',
        pragmas={
            'journal_mode': 'WAL',
            'foreign_keys': 'ON',
            'synchronous': 'NORMAL',
            'cache_size': 10000,
            'temp_store': 'MEMORY',
            'busy_timeout': 5000,  # 5 seconds
            'mmap_size': 30000000,  # 30MB memory mapping
            'secure_delete': 'OFF',
            'auto_vacuum': 'INCREMENTAL'
        }
    ),
    SQLiteBackend
)
```