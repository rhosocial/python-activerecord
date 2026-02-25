---
name: dev-backend-development
description: Guidelines for implementing new database backends for rhosocial-activerecord - dialect, type adapter, config, and storage backend
license: MIT
compatibility: opencode
metadata:
  category: backend
  level: advanced
  audience: developers
---

## What I do

Guide developers through creating new database backends for rhosocial-activerecord:
- Structure backend implementation (4 required files)
- Implement SQL dialect with proper formatting
- Create type adapters for Python <-> DB conversion
- Handle backend-specific features and protocols
- Maintain sync/async parity

## When to use me

Use this skill when:
- Adding support for a new database (MySQL, PostgreSQL, etc.)
- Implementing custom backends
- Understanding backend architecture
- Debugging backend-specific issues
- Adding new SQL dialect features

## Backend Structure

Create 4 files in `backend/impl/{name}/`:

1. **config.py** - Connection configuration
2. **dialect.py** - SQL generation
3. **type_adapter.py** - Type conversion
4. **backend.py** - Storage implementation (sync + async)

## Critical Rules

### Expression-Dialect Separation
**NEVER** generate SQL in Expression classes:
```python
# WRONG - in Expression class
return f'"{table}"."{column}"'

# CORRECT - delegate to dialect
return self.dialect.format_column_reference(table, column)
```

### Protocol-Based Features
Use protocols for feature detection:
```python
class WindowFunctionSupport(Protocol):
    def supports_window_functions(self) -> bool: ...
```

### Required Methods
- `format_identifier()` - Quote identifiers
- `format_column_reference()` - Format table.column
- `format_string_literal()` - Escape strings
- `supports_*` methods - Feature detection

## Reference
Study `backend/impl/sqlite/` for complete example.
