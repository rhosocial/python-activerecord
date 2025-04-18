# Custom Backends

This section covers how to implement custom database backends and extend existing ones in rhosocial ActiveRecord.

## Overview

rhosocial ActiveRecord is designed with extensibility in mind, allowing developers to create custom database backends beyond the built-in ones (SQLite, MySQL/MariaDB, PostgreSQL, etc.). This capability is useful when:

- You need to support a database system not included in the standard distribution
- You want to add specialized functionality to an existing backend
- You're integrating with a custom data storage solution that should work with ActiveRecord models

The following pages provide detailed guidance on implementing and extending database backends:

- [Implementing Custom Database Backends](implementing_custom_backends.md): A step-by-step guide to creating a new database backend from scratch
- [Extending Existing Backends](extending_existing_backends.md): How to extend or modify the behavior of existing database backends

## Architecture

The backend system in rhosocial ActiveRecord follows a modular architecture with clear separation of concerns:

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

## Implementation Location

When implementing your custom backend or extending an existing one, you have flexibility in where to place your code:

1. **Within the ActiveRecord Package**: You can place your implementation directly in the `rhosocial.activerecord.backend.impl` directory if you're modifying the core package.
2. **In a Separate Package**: You can create your own package structure outside the core ActiveRecord package, which is recommended if you plan to distribute your backend separately.

Both approaches are valid, with the separate package offering better isolation and easier distribution.

## Testing Your Backend

Thoroughly testing your backend implementation is crucial for ensuring reliability. You should:

1. **Mirror Existing Tests**: Study and mirror the test structure of existing backends (e.g., in the `tests/rhosocial/activerecord/backend` directory)
2. **Ensure Branch Coverage**: Write tests that cover all code branches and edge cases
3. **Simulate Real-World Scenarios**: Create tests that simulate various usage scenarios your backend will encounter
4. **Test Integration**: Verify that your backend works correctly with the rest of the ActiveRecord framework