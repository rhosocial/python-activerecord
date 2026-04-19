# Named Query

> **Important**: This is a **backend feature**, independent of the ActiveRecord pattern and ActiveQuery.

## Overview

Named query is a mechanism for organizing and executing reusable queries defined as Python callables. It provides a CLI interface for executing queries without writing SQL strings directly.

## Key Concepts

- **Backend Feature**: This module is part of the backend system, not the ActiveRecord ORM.
- **Callable-based**: Queries are defined as Python functions or classes with `dialect` as the first parameter.
- **Type-safe**: Returns `BaseExpression` objects that implement the `Executable` protocol.
- **CLI-friendly**: Provides command-line interface for query execution.

## Not ActiveRecord

Named query is **not related** to:

- ActiveRecord pattern
- ActiveQuery
- Model-based queries
- Relation queries

It is specifically designed for:
- CLI tools
- Script-based query execution
- Reusable query organization in Python modules

## Installation

Named query is included in the core `rhosocial-activerecord` package. No additional installation required.

## Quick Start

### Define a Named Query

A named query is a function or class with `dialect` as the first parameter:

```python
# myapp/queries.py
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import Select


def active_users(dialect, limit: int = 100):
    """Get active users with optional limit.

    Args:
        limit: Maximum number of users to return (default: 100)

    Returns:
        Select expression for active users
    """
    return Select(
        targets=[Column("id"), Column("name"), Column("email")],
        from_=Literal("users"),
        where=Column("status").eq("active"),
        limit=limit,
    )
```

Or as a class:

```python
# myapp/queries.py
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import Select


class UserQueries:
    """User query collection."""

    def __call__(self, dialect, status: str = "active"):
        """Get users by status.

        Args:
            status: User status to filter by (default: "active")

        Returns:
            Select expression
        """
        return Select(
            targets=[Column("id"), Column("name")],
            from_=Literal("users"),
            where=Column("status").eq(status),
        )
```

### Execute from CLI

```bash
# Execute named query
python -m rhosocial.activerecord.backend.impl.sqlite run \
    myapp.queries.active_users \
    --db-file mydb.sqlite

# List all queries in a module
python -m rhosocial.activerecord.backend.impl.sqlite run \
    myapp.queries --list

# Show query details
python -m rhosocial.activerecord.backend.impl.sqlite run \
    myapp.queries --example active_users

# Dry run to preview SQL
python -m rhosocial.activerecord.backend.impl.sqlite run \
    myapp.queries.active_users \
    --db-file mydb.sqlite \
    --param limit=50 \
    --dry-run
```

### Execute Programmatically

```python
from rhosocial.activerecord.backend.named_query import NamedQueryResolver


resolver = NamedQueryResolver("myapp.queries.active_users").load()
expression = resolver.execute(dialect, {"limit": 50})
sql, params = expression.to_sql()
print(f"SQL: {sql}, Params: {params}")
```

## CLI Options

| Option | Description |
|--------|-------------|
| `qualified_name` | Fully qualified Python name (module.path.callable) |
| `-e, --example` | Show detailed info for a specific query |
| `--param KEY=VALUE` | Query parameter (can be repeated) |
| `--describe` | Show signature without executing |
| `--dry-run` | Print SQL without executing |
| `--list` | List all queries in the module |
| `--force` | Force non-SELECT execution (DML/DDL) |
| `--explain` | Execute EXPLAIN and show plan |

## Discovery Rules

A callable is considered a named query if:
1. It is a function, method, or class (with `__call__`)
2. Its first parameter (after `self` for classes) is named `dialect`
3. It returns a `BaseExpression` object

Functions without `dialect` as the first parameter are ignored.

## Security

Named queries are type-safe:
- Only `BaseExpression` objects implementing `Executable` are allowed
- Direct SQL strings are not permitted
- This prevents SQL injection vulnerabilities

## API Reference

### Exceptions

- `NamedQueryError` - Base exception
- `NamedQueryNotFoundError` - Query not found
- `NamedQueryModuleNotFoundError` - Module not found
- `NamedQueryInvalidReturnTypeError` - Invalid return type
- `NamedQueryInvalidParameterError` - Invalid parameter
- `NamedQueryMissingParameterError` - Missing required parameter
- `NamedQueryNotCallableError` - Not callable
- `NamedQueryExplainNotAllowedError` - EXPLAIN not allowed

### Functions

- `NamedQueryResolver` - Main resolver class
- `resolve_named_query()` - Resolve and execute in one step
- `list_named_queries_in_module()` - List queries in module
- `validate_expression()` - Validate expression type
- `create_named_query_parser()` - Create CLI parser
- `handle_named_query()` - Handle CLI execution
- `parse_params()` - Parse CLI parameters

## Limitations

- This is a **backend feature**, not part of ActiveRecord
- Cannot be used with ActiveRecord models
- Cannot be used with ActiveQuery
- Designed for CLI and script use cases only