# Custom Backends

This section covers how to implement custom database backends and extend existing ones in Python ActiveRecord.

## Overview

Python ActiveRecord is designed with extensibility in mind, allowing developers to create custom database backends beyond the built-in ones (SQLite, MySQL/MariaDB, PostgreSQL, etc.). This capability is useful when:

- You need to support a database system not included in the standard distribution
- You want to add specialized functionality to an existing backend
- You're integrating with a custom data storage solution that should work with ActiveRecord models

The following pages provide detailed guidance on implementing and extending database backends:

- [Implementing Custom Database Backends](implementing_custom_backends.md): A step-by-step guide to creating a new database backend from scratch
- [Extending Existing Backends](extending_existing_backends.md): How to extend or modify the behavior of existing database backends

## Architecture

The backend system in Python ActiveRecord follows a modular architecture with clear separation of concerns:

1. **Abstract Base Classes**: The `StorageBackend` abstract base class defines the interface that all backends must implement
2. **Dialect System**: SQL dialect differences are handled through the dialect system
3. **Implementation Directory**: Each backend implementation is stored in its own subdirectory under `rhosocial.activerecord.backend.impl`

```
backend/
  base.py                # Abstract base classes and interfaces
  dialect.py             # SQL dialect system
  impl/                  # Implementation directory
    sqlite/              # SQLite implementation
      __init__.py
      backend.py         # SQLiteBackend class
      dialect.py         # SQLite dialect implementation
    mysql/               # MySQL implementation
      ...
    pgsql/               # PostgreSQL implementation
      ...
    your_custom_backend/ # Your custom implementation
      ...
```

This architecture makes it straightforward to add new backends while ensuring they integrate properly with the rest of the framework.