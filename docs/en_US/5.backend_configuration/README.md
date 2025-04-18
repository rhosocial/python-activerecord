# Backend Configuration

This section covers the configuration and usage of different database backends supported by rhosocial ActiveRecord. Understanding the backend configuration is essential for optimizing your application's database interactions.

## Contents

- [Supported Databases](5.1.supported_databases/README.md) - Detailed information about each supported database system
  - [MySQL/MariaDB](5.1.supported_databases/mysql_mariadb.md)
  - [PostgreSQL](5.1.supported_databases/postgresql.md)
  - [Oracle](5.1.supported_databases/oracle.md)
  - [SQL Server](5.1.supported_databases/sql_server.md)
  - [SQLite](5.1.supported_databases/sqlite.md)

- [Cross-database Queries](5.2.cross_database_queries/README.md)
  - [Cross-database Connection Configuration](5.2.cross_database_queries/connection_configuration.md)
  - [Heterogeneous Data Source Integration](5.2.cross_database_queries/heterogeneous_data_source_integration.md)
  - [Data Synchronization Strategies](5.2.cross_database_queries/data_synchronization_strategies.md)
  - [Cross-database Transaction Handling](5.2.cross_database_queries/cross_database_transaction_handling.md)

- [Database-specific Differences](5.3.database_specific_differences/README.md)
  - Data Type Mapping
  - SQL Dialect Differences
  - Performance Considerations

- [Custom Backends](5.4.custom_backends/README.md)
  - Implementing Custom Database Backends
  - Extending Existing Backends

## Introduction

rhosocial ActiveRecord is designed to work with multiple database systems through a unified interface. This architecture allows you to write database-agnostic code while still leveraging specific features of each database system when needed.

The backend configuration determines how rhosocial ActiveRecord connects to your database, manages connections, handles transactions, and translates ActiveRecord operations into database-specific SQL statements.

## Key Concepts

### Connection Configuration

Connection configuration is managed through the `ConnectionConfig` class, which provides a consistent way to specify connection parameters regardless of the database backend. Common parameters include:

- Database name, host, port
- Authentication credentials
- Connection pool settings
- Timeout configurations
- SSL/TLS options

### Backend Selection

You can select the appropriate backend for your database system when configuring your models:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class User(ActiveRecord):
    pass

# Configure the model to use MySQL backend
User.configure(
    ConnectionConfig(database='my_database', user='username', password='password'),
    MySQLBackend
)
```

### Connection Pooling

Most database backends in rhosocial ActiveRecord support connection pooling, which helps manage database connections efficiently. Connection pooling reduces the overhead of establishing new connections by reusing existing ones from a pool.

### Transactions

rhosocial ActiveRecord provides a consistent transaction API across all supported databases, while respecting the specific transaction capabilities and isolation levels of each database system.

Refer to the specific database documentation in this section for detailed information about configuration options, supported features, and optimization techniques for each database backend.