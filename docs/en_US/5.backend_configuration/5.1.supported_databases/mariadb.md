# MariaDB Support

rhosocial ActiveRecord provides robust support for MariaDB database, offering a seamless integration with this popular open-source relational database management system. This document covers the specific features, configuration options, and considerations when using rhosocial ActiveRecord with MariaDB.

> **Important Note**: MariaDB backend is being developed as a separate package and will be released in the future. This documentation is provided as a reference for upcoming features.

## Overview

MariaDB is a community-developed fork of MySQL, designed to remain free and open-source. rhosocial ActiveRecord supports MariaDB with a dedicated backend implementation that leverages its specific features while providing a consistent ActiveRecord API.

## Features

- Full CRUD operations support
- Transaction management with various isolation levels
- Connection pooling for improved performance
- Support for MariaDB-specific data types
- JSON operations support (for MariaDB 10.2+)
- Advanced query capabilities including window functions (for supported versions)
- Optimized batch operations

## Configuration

To configure a model to use the MariaDB backend, you'll need to provide the appropriate connection parameters:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

# Configure a model to use MariaDB backend
MyModel.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='my_database',
        user='username',
        password='password',
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci'
    ),
    MariaDBBackend
)
```

### Configuration Options

The MariaDB backend supports the following configuration options:

| Option | Description | Default |
|--------|-------------|--------|
| `host` | Database server hostname or IP address | `'localhost'` |
| `port` | Database server port | `3306` |
| `database` | Database name | Required |
| `user` | Username for authentication | Required |
| `password` | Password for authentication | Required |
| `charset` | Character set for the connection | `'utf8mb4'` |
| `collation` | Collation for the connection | `'utf8mb4_unicode_ci'` |
| `ssl` | SSL configuration dictionary | `None` |
| `connect_timeout` | Connection timeout in seconds | `10` |
| `read_timeout` | Read timeout in seconds | `30` |
| `write_timeout` | Write timeout in seconds | `30` |
| `pool_size` | Maximum number of connections in the pool | `5` |
| `pool_recycle` | Seconds after which a connection is recycled | `3600` |

## Data Types

The MariaDB backend supports the following data types:

| ActiveRecord Type | MariaDB Type |
|------------------|------------|
| `Integer` | `INT` |
| `BigInteger` | `BIGINT` |
| `Float` | `DOUBLE` |
| `Decimal` | `DECIMAL` |
| `String` | `VARCHAR` |
| `Text` | `TEXT` |
| `Boolean` | `TINYINT(1)` |
| `Date` | `DATE` |
| `DateTime` | `DATETIME` |
| `Time` | `TIME` |
| `Binary` | `BLOB` |
| `JSON` | `JSON` (MariaDB 10.2+) |

## MariaDB-Specific Features

### JSON Support

For MariaDB 10.2 and above, rhosocial ActiveRecord provides support for JSON data type and operations:

```python
from rhosocial.activerecord import ActiveRecord, fields

class Product(ActiveRecord):
    attributes = {
        'id': fields.Integer(primary_key=True),
        'name': fields.String(max_length=100),
        'properties': fields.JSON()
    }

# Using JSON fields
product = Product(name='Laptop', properties={'color': 'silver', 'weight': 1.5})
product.save()

# JSON path operations (MariaDB 10.2+)
products = Product.where("JSON_EXTRACT(properties, '$.color') = ?", ['silver'])
```

### Dynamic Columns

MariaDB's dynamic columns feature provides a flexible way to store schema-less data:

```python
from rhosocial.activerecord import ActiveRecord, fields
from rhosocial.activerecord.backend.impl.mariadb import dynamic_columns

class Product(ActiveRecord):
    attributes = {
        'id': fields.Integer(primary_key=True),
        'name': fields.String(max_length=100),
        'attributes': fields.Binary()  # For dynamic columns
    }
    
    def set_attribute(self, name, value):
        if self.attributes is None:
            self.attributes = dynamic_columns.create()
        self.attributes = dynamic_columns.set(self.attributes, name, value)
    
    def get_attribute(self, name):
        if self.attributes is None:
            return None
        return dynamic_columns.get(self.attributes, name)
```

### Full-Text Search

MariaDB's full-text search capabilities are accessible through rhosocial ActiveRecord:

```python
from rhosocial.activerecord import ActiveRecord, fields

class Article(ActiveRecord):
    attributes = {
        'id': fields.Integer(primary_key=True),
        'title': fields.String(max_length=200),
        'content': fields.Text()
    }
    
    @classmethod
    def search(cls, query):
        return cls.where("MATCH(title, content) AGAINST(? IN BOOLEAN MODE)", [query])

# Note: You need to create a FULLTEXT index on the columns first
```

## Performance Optimization

### Indexing

Proper indexing is crucial for MariaDB performance. rhosocial ActiveRecord provides methods to define indexes in your models:

```python
from rhosocial.activerecord import ActiveRecord, fields, indexes

class User(ActiveRecord):
    attributes = {
        'id': fields.Integer(primary_key=True),
        'email': fields.String(max_length=100),
        'username': fields.String(max_length=50),
        'created_at': fields.DateTime()
    }
    
    indexes = [
        indexes.Index(['email'], unique=True),
        indexes.Index(['username'], unique=True),
        indexes.Index(['created_at'])
    ]
```

### Batch Operations

For bulk inserts or updates, use batch operations to improve performance:

```python
# Batch insert
users = [User(username=f'user{i}', email=f'user{i}@example.com') for i in range(1000)]
User.batch_insert(users)

# Batch update
User.where('created_at < ?', [one_year_ago]).batch_update(active=False)
```

## Transaction Management

MariaDB supports various transaction isolation levels, which you can specify when starting a transaction:

```python
from rhosocial.activerecord.transaction import IsolationLevel

# Using a specific isolation level
with User.transaction(isolation_level=IsolationLevel.REPEATABLE_READ):
    user = User.find(1)
    user.balance -= 100
    user.save()
    
    recipient = User.find(2)
    recipient.balance += 100
    recipient.save()
```

## Connection Pooling

The MariaDB backend includes connection pooling to efficiently manage database connections:

```python
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

# Configure connection pooling
config = ConnectionConfig(
    host='localhost',
    database='my_database',
    user='username',
    password='password',
    pool_size=10,        # Maximum number of connections in the pool
    pool_recycle=3600    # Recycle connections after 1 hour
)

MyModel.configure(config, MariaDBBackend)
```

## Version-Specific Features

rhosocial ActiveRecord adapts to different MariaDB versions, enabling you to use version-specific features when available:

| Feature | Minimum MariaDB Version |
|---------|------------------------|
| JSON data type | 10.2 |
| Window functions | 10.2 |
| Common Table Expressions (CTE) | 10.2 |
| Sequences | 10.3 |
| CHECK constraints | 10.2 |
| Invisible columns | 10.3 |

## Limitations

- Some advanced MariaDB features may require direct SQL execution using `execute_raw()`
- For complex geospatial operations, consider using MariaDB-specific methods

## Best Practices

1. Use appropriate indexes for your query patterns
2. Consider using connection pooling for applications with many concurrent users
3. Choose appropriate transaction isolation levels based on your application needs
4. Use batch operations for bulk data manipulation
5. Set appropriate character set and collation (utf8mb4 recommended)
6. Monitor connection usage and adjust pool size accordingly

## Further Reading

- [MariaDB Documentation](https://mariadb.com/kb/en/documentation/)
- [rhosocial ActiveRecord Transaction Management](../../../3.active_record_and_active_query/3.4.transaction_management.md)
- [Performance Optimization](../../../4.performance_optimization/README.md)