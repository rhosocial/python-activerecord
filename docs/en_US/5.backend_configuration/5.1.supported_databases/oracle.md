# Oracle Support

rhosocial ActiveRecord provides support for Oracle Database, a robust enterprise-grade relational database management system. This document covers the specific features, configuration options, and considerations when using rhosocial ActiveRecord with Oracle.

## Overview

Oracle Database is a multi-model database management system produced and marketed by Oracle Corporation. It is one of the most trusted and widely-used relational database systems for enterprise applications. rhosocial ActiveRecord's Oracle backend provides a consistent interface to Oracle databases while leveraging Oracle-specific features.

## Features

- Full CRUD operations support
- Transaction management with various isolation levels
- Connection pooling for improved performance
- Support for Oracle-specific data types and functions
- PL/SQL procedure and function integration
- Advanced query capabilities including window functions
- Optimized batch operations
- Support for Oracle's ROWID and sequence features

## Configuration

To use Oracle with rhosocial ActiveRecord, you need to configure your model with the Oracle backend:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.oracle import OracleBackend

class User(ActiveRecord):
    pass

# Configure the model to use Oracle backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=1521,
        service_name='ORCL',  # Oracle service name
        user='username',
        password='password',
        # Optional parameters
        sid=None,  # Oracle SID (alternative to service_name)
        tns_name=None,  # TNS name from tnsnames.ora (alternative to host/port)
        pool_size=5,
        pool_timeout=30,
        encoding='UTF-8',
        nencoding='UTF-8',  # National character set encoding
        mode=None,  # Connection mode (SYSDBA, SYSOPER, etc.)
        events=False,  # Enable Oracle events
        purity='DEFAULT'  # Connection purity (NEW, SELF, DEFAULT)
    ),
    OracleBackend
)
```

## Connection Methods

Oracle supports multiple connection methods, which can be specified in the ConnectionConfig:

1. **Basic connection** (host, port, service_name)
2. **SID connection** (host, port, sid)
3. **TNS connection** (tns_name)
4. **Easy Connect** (host, port, service_name)

## Connection Pooling

The Oracle backend supports connection pooling through Oracle's built-in connection pooling mechanism. Connection pooling reduces the overhead of establishing new connections by reusing existing ones from a pool.

You can configure the connection pool with these parameters:

- `pool_size`: Maximum number of connections in the pool
- `pool_timeout`: Maximum time to wait for a connection from the pool (in seconds)

## Transactions

rhosocial ActiveRecord provides comprehensive transaction support for Oracle, including different isolation levels:

```python
# Start a transaction with a specific isolation level
with User.transaction(isolation_level='READ COMMITTED'):
    user = User.find(1)
    user.name = 'New Name'
    user.save()
```

Supported isolation levels:
- `READ COMMITTED` (default for Oracle)
- `SERIALIZABLE`

Oracle also supports savepoints, which allow you to create checkpoints within a transaction:

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

## Sequences and Auto-incrementing IDs

Oracle uses sequences for generating auto-incrementing values. rhosocial ActiveRecord supports Oracle sequences for primary key generation:

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    __sequence_name__ = 'users_seq'  # Oracle sequence for ID generation
```

## Data Type Mapping

rhosocial ActiveRecord maps Python types to Oracle data types automatically. Here are some common mappings:

| Python Type | Oracle Type     |
|-------------|----------------|
| int         | NUMBER         |
| float       | NUMBER         |
| str         | VARCHAR2/CLOB  |
| bytes       | BLOB           |
| bool        | NUMBER(1)      |
| datetime    | TIMESTAMP      |
| date        | DATE           |
| time        | TIMESTAMP      |
| Decimal     | NUMBER         |
| dict/list   | CLOB (JSON)    |

## Performance Considerations

- Use connection pooling for applications with frequent database operations
- Consider using batch operations for inserting or updating multiple records
- For large result sets, use cursors or pagination to avoid loading all data into memory
- Use appropriate indexes for frequently queried columns
- Consider the impact of transaction isolation levels on concurrency and performance

## Requirements

- Python 3.7+
- cx_Oracle package or python-oracledb package
- Oracle Client libraries installed and configured

## Limitations

- Some Oracle-specific features may require raw SQL queries
- Performance may vary based on connection settings and server configuration
- Oracle Client libraries must be installed separately

## Best Practices

1. **Use connection pooling**: Enable connection pooling for better performance in multi-user applications
2. **Set appropriate timeouts**: Configure connection and query timeouts to prevent hanging connections
3. **Use transactions**: Wrap related operations in transactions for data consistency
4. **Consider character sets**: Configure appropriate encoding settings for international data
5. **Monitor connection usage**: Ensure your application doesn't exhaust the connection pool