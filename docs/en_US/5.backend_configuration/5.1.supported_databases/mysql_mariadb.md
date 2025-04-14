# MySQL/MariaDB Support

Python ActiveRecord provides robust support for MySQL and MariaDB databases, offering a seamless integration with these popular relational database management systems. This document covers the specific features, configuration options, and considerations when using Python ActiveRecord with MySQL or MariaDB.

## Overview

MySQL is one of the world's most popular open-source relational database management systems. MariaDB is a community-developed fork of MySQL, designed to remain free and open-source. Python ActiveRecord supports both systems with dedicated backend implementations that leverage their specific features while providing a consistent ActiveRecord API.

## Features

- Full CRUD operations support
- Transaction management with various isolation levels
- Connection pooling for improved performance
- Support for MySQL/MariaDB-specific data types
- JSON operations support (for MySQL 5.7+ and MariaDB 10.2+)
- Advanced query capabilities including window functions (for supported versions)
- Optimized batch operations

## Configuration

To use MySQL or MariaDB with Python ActiveRecord, you need to configure your model with the appropriate backend:

### MySQL Configuration

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class User(ActiveRecord):
    pass

# Configure the model to use MySQL backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='my_database',
        user='username',
        password='password',
        # Optional parameters
        charset='utf8mb4',
        pool_size=5,
        pool_name='mysql_pool',
        pool_timeout=30,
        ssl_mode='REQUIRED',  # For SSL connections
        ssl_ca='/path/to/ca.pem',  # SSL Certificate Authority
        ssl_cert='/path/to/client-cert.pem',  # SSL client certificate
        ssl_key='/path/to/client-key.pem'  # SSL client key
    ),
    MySQLBackend
)
```

### MariaDB Configuration

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

class User(ActiveRecord):
    pass

# Configure the model to use MariaDB backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='my_database',
        user='username',
        password='password',
        # Optional parameters
        charset='utf8mb4',
        pool_size=5,
        pool_timeout=30
    ),
    MariaDBBackend
)
```

## Connection Pooling

Both MySQL and MariaDB backends support connection pooling, which helps manage database connections efficiently. Connection pooling reduces the overhead of establishing new connections by reusing existing ones from a pool.

You can configure the connection pool size using the `pool_size` parameter in the `ConnectionConfig`. For MySQL, you can also specify a `pool_name` to identify the connection pool.

## Transactions

Python ActiveRecord provides comprehensive transaction support for MySQL and MariaDB, including different isolation levels:

```python
# Start a transaction with a specific isolation level
with User.transaction(isolation_level='READ COMMITTED'):
    user = User.find(1)
    user.name = 'New Name'
    user.save()
```

Supported isolation levels:
- `READ UNCOMMITTED`
- `READ COMMITTED`
- `REPEATABLE READ` (default for MySQL/MariaDB)
- `SERIALIZABLE`

## Version-Specific Features

Python ActiveRecord adapts to different versions of MySQL and MariaDB, enabling or disabling features based on the database version:

### MySQL Version Features

- **MySQL 5.7+**: JSON operations, improved spatial functions
- **MySQL 8.0+**: Window functions, common table expressions (CTEs), descending indexes

### MariaDB Version Features

- **MariaDB 10.2+**: JSON operations, window functions
- **MariaDB 10.3+**: System versioning, sequences
- **MariaDB 10.5+**: Additional window functions, improved CTE support

## Data Type Mapping

Python ActiveRecord maps Python types to MySQL/MariaDB data types automatically. Here are some common mappings:

| Python Type | MySQL/MariaDB Type |
|-------------|--------------------|
| int         | INT                |
| float       | DOUBLE             |
| str         | VARCHAR            |
| bytes       | BLOB               |
| bool        | TINYINT(1)         |
| datetime    | DATETIME           |
| date        | DATE               |
| time        | TIME               |
| Decimal     | DECIMAL            |
| dict/list   | JSON (if supported)|

## Performance Considerations

- Use connection pooling for applications with frequent database operations
- Consider using batch operations for inserting or updating multiple records
- For large result sets, use cursors or pagination to avoid loading all data into memory
- Use appropriate indexes for frequently queried columns
- Consider the impact of transaction isolation levels on concurrency and performance

## Requirements

### MySQL Backend

- Python 3.7+
- mysql-connector-python package

### MariaDB Backend

- Python 3.7+
- mariadb package

## Limitations

- Some advanced MySQL 8.0+ features may not be available in older versions
- MariaDB-specific extensions might not be fully supported
- Performance may vary based on connection settings and server configuration

## Best Practices

1. **Use connection pooling**: Enable connection pooling for better performance in multi-user applications
2. **Set appropriate timeouts**: Configure connection and query timeouts to prevent hanging connections
3. **Use transactions**: Wrap related operations in transactions for data consistency
4. **Consider character sets**: Use utf8mb4 for full Unicode support
5. **Monitor connection usage**: Ensure your application doesn't exhaust the connection pool