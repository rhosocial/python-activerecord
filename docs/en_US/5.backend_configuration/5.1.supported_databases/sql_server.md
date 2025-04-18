# SQL Server Support

rhosocial ActiveRecord provides support for Microsoft SQL Server, a robust enterprise-grade relational database management system. This document covers the specific features, configuration options, and considerations when using rhosocial ActiveRecord with SQL Server.

## Overview

Microsoft SQL Server is a relational database management system developed by Microsoft. It is widely used in enterprise environments and offers a comprehensive set of features for data management, business intelligence, and analytics. rhosocial ActiveRecord's SQL Server backend provides a consistent interface to SQL Server databases while leveraging SQL Server-specific features.

## Features

- Full CRUD operations support
- Transaction management with various isolation levels
- Connection pooling for improved performance
- Support for SQL Server-specific data types and functions
- Stored procedure integration
- Advanced query capabilities including window functions
- Optimized batch operations
- Support for SQL Server's identity columns and sequences

## Configuration

To use SQL Server with rhosocial ActiveRecord, you need to configure your model with the SQL Server backend:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlserver import SQLServerBackend

class User(ActiveRecord):
    pass

# Configure the model to use SQL Server backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=1433,
        database='my_database',
        user='username',
        password='password',
        # Optional parameters
        driver='ODBC Driver 17 for SQL Server',  # ODBC driver name
        trust_server_certificate=False,  # Trust server certificate without validation
        encrypt=True,  # Encrypt connection
        connection_timeout=30,  # Connection timeout in seconds
        pool_size=5,  # Maximum connections in pool
        app_name='MyApp',  # Application name for monitoring
        schema='dbo'  # Default schema
    ),
    SQLServerBackend
)
```

## Connection Methods

SQL Server supports multiple connection methods, which can be specified in the ConnectionConfig:

1. **SQL Server Authentication** (user, password)
2. **Windows Authentication** (trusted_connection=True)
3. **Azure Active Directory** (authentication='ActiveDirectoryPassword', user, password)

## Connection Pooling

The SQL Server backend supports connection pooling, which helps manage database connections efficiently. Connection pooling reduces the overhead of establishing new connections by reusing existing ones from a pool.

You can configure the connection pool with the `pool_size` parameter in the `ConnectionConfig`.

## Transactions

rhosocial ActiveRecord provides comprehensive transaction support for SQL Server, including different isolation levels:

```python
# Start a transaction with a specific isolation level
with User.transaction(isolation_level='READ COMMITTED'):
    user = User.find(1)
    user.name = 'New Name'
    user.save()
```

Supported isolation levels:
- `READ UNCOMMITTED`
- `READ COMMITTED` (default for SQL Server)
- `REPEATABLE READ`
- `SERIALIZABLE`
- `SNAPSHOT` (if enabled on the database)

SQL Server also supports savepoints, which allow you to create checkpoints within a transaction:

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

SQL Server organizes database objects into schemas. You can configure the default schema using the `schema` parameter in the connection configuration:

```python
ConnectionConfig(
    # ... other parameters
    schema='custom_schema'
)
```

You can also specify the schema in your model definition:

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    __schema_name__ = 'custom_schema'
```

## Identity Columns and Sequences

SQL Server supports both identity columns and sequences for generating auto-incrementing values. rhosocial ActiveRecord supports both mechanisms for primary key generation:

```python
# Using identity column (default)
class User(ActiveRecord):
    __table_name__ = 'users'
    # SQL Server will use identity column by default

# Using sequence
class Product(ActiveRecord):
    __table_name__ = 'products'
    __sequence_name__ = 'products_seq'  # SQL Server sequence for ID generation
```

## Data Type Mapping

rhosocial ActiveRecord maps Python types to SQL Server data types automatically. Here are some common mappings:

| Python Type | SQL Server Type |
|-------------|----------------|
| int         | INT            |
| float       | FLOAT          |
| str         | NVARCHAR/VARCHAR |
| bytes       | VARBINARY      |
| bool        | BIT            |
| datetime    | DATETIME2      |
| date        | DATE           |
| time        | TIME           |
| Decimal     | DECIMAL        |
| dict/list   | NVARCHAR(MAX) (JSON) |
| UUID        | UNIQUEIDENTIFIER |

## JSON Support

SQL Server 2016 and later versions support JSON functions. rhosocial ActiveRecord provides a convenient API for working with JSON data:

```python
# Query with JSON conditions (SQL Server 2016+)
users = User.where(User.profile.json_value('$.preferences.theme').eq('dark')).all()

# Update JSON field
user = User.find(1)
user.profile = '{"name": "John", "preferences": {"theme": "light"}}'
user.save()
```

## Performance Considerations

- Use connection pooling for applications with frequent database operations
- Consider using batch operations for inserting or updating multiple records
- For large result sets, use cursors or pagination to avoid loading all data into memory
- Use appropriate indexes for frequently queried columns
- Consider the impact of transaction isolation levels on concurrency and performance

## Requirements

- Python 3.7+
- pyodbc package
- ODBC Driver for SQL Server installed on the system

## Limitations

- Some SQL Server-specific features may require raw SQL queries
- Performance may vary based on connection settings and server configuration
- ODBC Driver for SQL Server must be installed separately

## Best Practices

1. **Use connection pooling**: Enable connection pooling for better performance in multi-user applications
2. **Set appropriate timeouts**: Configure connection and query timeouts to prevent hanging connections
3. **Use transactions**: Wrap related operations in transactions for data consistency
4. **Consider schema design**: Use SQL Server schemas for better organization of database objects
5. **Monitor connection usage**: Ensure your application doesn't exhaust the connection pool
6. **Use parameterized queries**: Always use parameterized queries to prevent SQL injection