# Expression Serialization

This document describes the serialization and deserialization mechanism for SQL expression objects, which is essential for implementing expression caching, distributed queries, and task scheduling.

## Design Motivation

Why not serialize `dialect` directly? Here's why:

1. **Runtime Injection**: Dialect is tightly coupled with specific database backends; serialization should decouple expressions from dialects
2. **Multi-Dialect Support**: The same expression may generate different SQL under different dialects; serialization should not lock in a dialect
3. **Security Isolation**: Some dialect implementations depend on database connection state, which is not suitable for cross-process transmission

Therefore, the serialized `ExpressionSpec` does not contain dialect information. At deserialization time, the caller provides the target dialect.

## Core API

### serialize()

Serializes an expression object to a dictionary:

```python
from rhosocial.activerecord.backend.expression.serialization import serialize

spec = serialize(expression)
# Returns {"type": "Column", "module": "...", "params": {...}}
```

### deserialize()

Restores an expression object from a dictionary:

```python
from rhosocial.activerecord.backend.expression.serialization import deserialize

expr = deserialize(spec, dialect)
```

### ExpressionFactory

Provides factory methods to create expressions:

```python
from rhosocial.activerecord.backend.expression.serialization import ExpressionFactory

factory = ExpressionFactory(dialect)
expr = factory.create("Column", name="id", table="users")
```

## ExpressionSpec Format

The serialized dictionary contains three required fields:

| Field | Type | Description |
|-------|------|-------------|
| `type` | str | Expression class name (e.g., `Column`, `ComparisonPredicate`) |
| `module` | str | Full module path to the expression class |
| `params` | dict | Constructor parameters, keys must match `__init__` parameter names |

### Example

```python
# Column("users", "id")
{
    "type": "Column",
    "module": "rhosocial.activerecord.backend.expression.core",
    "params": {"name": "id", "table": "users", "alias": null, "schema_name": null}
}
```

## Nested Expressions

Expression parameters may contain other expression objects (e.g., predicates in WHERE clauses). Use the `__expr__` marker during serialization:

```python
# Serialization of WHERE status = 'active'
{
    "type": "WhereClause",
    "module": "rhosocial.activerecord.backend.expression.query_parts",
    "params": {
        "condition": {
            "__expr__": {
                "type": "ComparisonPredicate",
                "module": "rhosocial.activerecord.backend.expression.predicates",
                "params": {...}
            }
        }
    }
}
```

During deserialization, sub-dictionaries marked with `__expr__` are automatically restored as expression objects.

## Tuple Marker

Python `tuple` cannot be directly JSON serialized; use the `__tuple__` marker:

```python
# ORDER BY id DESC, name ASC
{
    "type": "OrderByClause",
    "params": {
        "order_by_items": [
            {"__tuple__": [Column(...), "DESC"]},
            {"__tuple__": [Column(...), "ASC"]}
        ]
    }
}
```

## Error Handling

During deserialization, the following exceptions may be raised:

- `ExpressionDeserializationError`: Type not registered, missing parameters, construction failed
- `TypeError`: Parameter type mismatch (wrapped as `ExpressionDeserializationError`)

Dialect compatibility errors (e.g., PostgreSQL-specific syntax not supported by MySQL) only surface at `to_sql()` time.

## Use Cases

### Cache Query Plans

```python
# Serialize
query = query.select(...).where(...)
spec = serialize(query)

# Deserialize
restored = deserialize(spec, new_dialect)
sql = restored.to_sql()
```

### Distributed Task Scheduling

Pass expressions as task parameters; at deserialization, inject the target environment's dialect.

## Related Documents

- [Extending Guide](./extending.md): How to implement serialization for custom expressions
- [Format Reference](./format-reference.md): Complete ExpressionSpec specification
- [Migration Guide](./migration.md): Version compatibility notes