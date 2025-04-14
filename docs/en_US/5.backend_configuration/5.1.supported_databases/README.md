# Supported Databases

Python ActiveRecord provides support for multiple database systems, allowing you to use the same ActiveRecord API regardless of the underlying database. This section provides detailed information about each supported database system, including configuration options, specific features, and optimization techniques.

## Contents

- [MySQL/MariaDB](mysql_mariadb.md) - Configuration and features for MySQL and MariaDB
- [PostgreSQL](postgresql.md) - Working with PostgreSQL databases
- [Oracle](oracle.md) - Oracle database integration
- [SQL Server](sql_server.md) - Microsoft SQL Server support
- [SQLite](sqlite.md) - Lightweight file-based database support

## Common Configuration

All database backends in Python ActiveRecord are configured using the `ConnectionConfig` class, which provides a consistent interface for specifying connection parameters. While each database system has its own specific parameters, the basic configuration pattern remains the same:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

# Configure a model to use a specific database backend
MyModel.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='my_database',
        user='username',
        password='password'
    ),
    MySQLBackend
)
```

## Choosing a Database

When selecting a database for your application, consider the following factors:

1. **Application requirements**: Different databases excel at different types of workloads
2. **Scalability needs**: Some databases are better suited for horizontal scaling
3. **Feature requirements**: Specific features like JSON support, full-text search, or geospatial capabilities
4. **Operational considerations**: Backup, replication, and high availability options
5. **Team expertise**: Familiarity with administration and optimization

## Database-Specific Features

While Python ActiveRecord provides a unified API across all supported databases, it also allows you to leverage database-specific features when needed. Each database backend implements the core ActiveRecord functionality while also exposing unique capabilities of the underlying database system.

Refer to the specific database documentation for detailed information about:

- Connection configuration options
- Supported data types
- Transaction isolation levels
- Performance optimization techniques
- Database-specific query capabilities

## Multiple Database Support

Python ActiveRecord allows you to work with multiple databases simultaneously, even of different types. This is particularly useful for applications that need to integrate data from various sources or that use different databases for different parts of the application.

See the [Cross-database Queries](../5.2.cross_database_queries/README.md) section for more information on working with multiple databases.