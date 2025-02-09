# Storage Backends

This chapter covers the storage backend system of RhoSocial ActiveRecord, including both built-in SQLite support and optional database backends.

## Overview

RhoSocial ActiveRecord uses a modular backend system that:
- Provides built-in SQLite support
- Allows additional database backends
- Ensures consistent API across backends
- Supports backend-specific features

## Available Backends

### Built-in SQLite Backend

SQLite is included by default:

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Configure with SQLite
User.configure(
    ConnectionConfig(database='app.db'),
    backend_class=SQLiteBackend
)
```

### Optional Backends

Additional backends available through optional packages:

```python
# MySQL Backend
pip install rhosocial-activerecord[mysql]

# PostgreSQL Backend
pip install rhosocial-activerecord[pgsql]

# Oracle Backend
pip install rhosocial-activerecord[oracle]

# SQL Server Backend
pip install rhosocial-activerecord[mssql]
```

## Backend Features

Each backend supports core features plus database-specific capabilities:

### Common Features
- CRUD operations
- Transaction support
- Query building
- Type mapping
- Connection pooling

### Backend-Specific Features
- SQLite: In-memory databases, WAL mode
- MySQL: Full-text search, spatial types
- PostgreSQL: JSON operations, arrays
- Oracle: PL/SQL support
- SQL Server: Window functions

## Example Usage

### Social Media Application

```python
# SQLite Configuration
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str

# Development (SQLite)
User.configure(
    ConnectionConfig(
        database='social_media.db',
        options={'journal_mode': 'WAL'}
    ),
    backend_class=SQLiteBackend
)

# Production (MySQL)
User.configure(
    ConnectionConfig(
        database='social_media',
        host='db.example.com',
        username='app_user',
        password='secret',
        pool_size=10
    ),
    backend_class=MySQLBackend
)
```

### E-commerce System

```python
# SQLite for Testing
class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    total: Decimal
    status: str

# Testing Configuration
Order.configure(
    ConnectionConfig(database=':memory:'),
    backend_class=SQLiteBackend
)

# Production Configuration
Order.configure(
    ConnectionConfig(
        database='ecommerce',
        host='db.example.com',
        username='app_user',
        password='secret',
        pool_size=20,
        ssl_ca='ca.pem'
    ),
    backend_class=PostgreSQLBackend
)
```

## Backend Architecture

The backend system is built on several key components:

1. **Storage Backend**
   - Connection management
   - Query execution
   - Transaction handling

2. **Type System**
   - Type mapping
   - Value conversion
   - Custom type support

3. **SQL Dialect**
   - SQL generation
   - Query building
   - Expression handling

4. **Transaction Manager**
   - Transaction control
   - Savepoint support
   - Isolation levels

## In This Chapter

1. [Architecture](architecture.md)
   - Backend system design
   - Component interaction
   - Extension points

2. [SQLite Usage](sqlite_usage.md)
   - Built-in SQLite features
   - Configuration options
   - Best practices

3. [SQLite Implementation](sqlite_impl.md)
   - Implementation details
   - Type handling
   - SQLite specifics

4. [Custom Backend](custom_backend.md)
   - Creating new backends
   - Required components
   - Integration guide

## Best Practices

1. **Development vs Production**
   - Use SQLite for development/testing
   - Use production-grade backends in production
   - Keep configurations separate

2. **Backend Selection**
   - Choose based on requirements
   - Consider scaling needs
   - Evaluate feature requirements

3. **Configuration Management**
   - Use environment variables
   - Secure credential handling
   - Configure connection pools

4. **Testing**
   - Use in-memory SQLite for tests
   - Test with target backend
   - Verify backend-specific features

## Next Steps

1. Understand the [Architecture](architecture.md)
2. Learn [SQLite Usage](sqlite_usage.md)
3. Study [SQLite Implementation](sqlite_impl.md)
4. Create [Custom Backends](custom_backend.md)