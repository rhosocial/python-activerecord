# PostgreSQL Support

rhosocial ActiveRecord provides comprehensive support for PostgreSQL, a powerful open-source object-relational database system. This document covers the specific features, configuration options, and considerations when using rhosocial ActiveRecord with PostgreSQL.

## Overview

PostgreSQL is an advanced, enterprise-class open-source relational database that supports both SQL (relational) and JSON (non-relational) querying. rhosocial ActiveRecord's PostgreSQL backend leverages PostgreSQL's rich feature set while providing a consistent ActiveRecord API.

## Features

- Full CRUD operations support
- Transaction management with all PostgreSQL isolation levels
- Connection pooling for improved performance
- Support for PostgreSQL-specific data types (including arrays, JSON, JSONB, UUID, etc.)
- Advanced query capabilities including window functions and common table expressions
- Support for PostgreSQL-specific operators and functions
- JSON/JSONB operations with full query support
- Schema search path configuration

## Configuration

To use PostgreSQL with rhosocial ActiveRecord, you need to configure your model with the PostgreSQL backend:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLBackend

class User(ActiveRecord):
    pass

# Configure the model to use PostgreSQL backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=5432,
        database='my_database',
        user='username',
        password='password',
        # Optional parameters
        pool_size=10,  # Total connections in pool
        pool_timeout=30,  # Connection timeout in seconds
        search_path='public,custom_schema',  # Schema search path
        statement_timeout=30000,  # Statement timeout in milliseconds
        # SSL options
        ssl_mode='verify-full',  # SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
        ssl_ca='/path/to/ca.pem',  # SSL Certificate Authority
        ssl_cert='/path/to/client-cert.pem',  # SSL client certificate
        ssl_key='/path/to/client-key.pem'  # SSL client key
    ),
    PostgreSQLBackend
)
```

## Connection Pooling

The PostgreSQL backend uses the `psycopg_pool` library to provide efficient connection pooling. Connection pooling reduces the overhead of establishing new connections by reusing existing ones from a pool.

You can configure the connection pool with these parameters:

- `pool_size`: Maximum number of connections in the pool (default is 5)
- `pool_timeout`: Maximum time to wait for a connection from the pool (in seconds)

The actual pool size is managed with min_size (approximately half of pool_size) and max_size (equal to pool_size) settings internally.

## Transactions

rhosocial ActiveRecord provides comprehensive transaction support for PostgreSQL, including all standard isolation levels:

```python
# Start a transaction with a specific isolation level
with User.transaction(isolation_level='REPEATABLE READ'):
    user = User.find(1)
    user.name = 'New Name'
    user.save()
```

Supported isolation levels:
- `READ UNCOMMITTED` (treated as READ COMMITTED in PostgreSQL)
- `READ COMMITTED` (default for PostgreSQL)
- `REPEATABLE READ`
- `SERIALIZABLE`

PostgreSQL also supports savepoints, which allow you to create checkpoints within a transaction:

```python
with User.transaction() as tx:
    user = User.find(1)
    user.name = 'New Name'
    user.save()
    
    # Create a savepoint
    tx.savepoint('my_savepoint')
    
    # Make more changes
    user.email = 'new_email@example.com'
    user.save()
    
    # Rollback to savepoint if needed
    tx.rollback_to('my_savepoint')
```

## Schema Support

PostgreSQL supports multiple schemas within a database. You can configure the schema search path using the `search_path` parameter in the connection configuration:

```python
ConnectionConfig(
    # ... other parameters
    search_path='public,custom_schema'
)
```

You can also specify the schema in your model definition:

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    __schema_name__ = 'custom_schema'
```

## Data Type Mapping

rhosocial ActiveRecord maps Python types to PostgreSQL data types automatically. Here are some common mappings:

| Python Type | PostgreSQL Type |
|-------------|----------------|
| int         | INTEGER        |
| float       | DOUBLE PRECISION |
| str         | VARCHAR/TEXT   |
| bytes       | BYTEA          |
| bool        | BOOLEAN        |
| datetime    | TIMESTAMP      |
| date        | DATE           |
| time        | TIME           |
| Decimal     | NUMERIC        |
| dict        | JSONB          |
| list        | JSONB or ARRAY |
| UUID        | UUID           |

## JSON/JSONB Support

PostgreSQL offers robust support for JSON data through its JSON and JSONB data types. rhosocial ActiveRecord provides a convenient API for working with JSON data:

```python
# Query with JSON conditions
users = User.where(User.profile['preferences']['theme'].eq('dark')).all()

# Update JSON field
user = User.find(1)
user.profile = {'name': 'John', 'preferences': {'theme': 'light'}}
user.save()
```

## Performance Considerations

- Use connection pooling for applications with frequent database operations
- Consider using JSONB instead of JSON for better query performance
- Use appropriate indexes, including GIN indexes for JSONB fields
- For large result sets, use cursors or pagination to avoid loading all data into memory
- Consider the impact of transaction isolation levels on concurrency and performance

## Requirements

- Python 3.7+
- psycopg package (PostgreSQL Python driver)
- psycopg_pool package (for connection pooling)

## Limitations

- Some advanced PostgreSQL features may require raw SQL queries
- Performance may vary based on connection settings and server configuration

## Best Practices

1. **Use connection pooling**: Enable connection pooling for better performance in multi-user applications
2. **Set appropriate timeouts**: Configure connection and statement timeouts to prevent hanging connections
3. **Use transactions**: Wrap related operations in transactions for data consistency
4. **Consider schema design**: Use PostgreSQL schemas for better organization of database objects
5. **Monitor connection usage**: Ensure your application doesn't exhaust the connection pool