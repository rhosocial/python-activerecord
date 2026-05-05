# ExpressionSpec Format Reference

This document defines the complete specification for the serialization format.

## ExpressionSpec Structure

The target format for expression serialization:

```python
{
    "type": str,           # Required: class name
    "module": str,         # Required: full module path
    "params": dict         # Required: constructor parameters
}
```

### Field Constraints

| Field | Type | Constraint |
|-------|------|------------|
| `type` | str | Non-empty, valid Python identifier |
| `module` | str | Importable module path, class must be importable from that module |
| `params` | dict | Keys must match target class `__init__` parameter names |

## Marker Types

### __expr__ Marker (Reserved Key)

Nested expressions use `__expr__` wrapping:

```python
{
    "type": "WhereClause",
    "params": {
        "condition": {
            "__expr__": {
                "type": "ComparisonPredicate",
                "module": "...",
                "params": {...}
            }
        }
    }
}
```

**Semantics**: During deserialization, the value of `__expr__` is recursively deserialized as an expression object.

**Important**: `__expr__` is a framework reserved key. Custom expressions' `get_params()` return values must NOT use this key.

### __tuple__ Marker (Reserved Key)

Tuples use `__tuple__` marker:

```python
{
    "type": "OrderByClause",
    "params": {
        "order_by_items": [
            {"__tuple__": [Column(...), "DESC"]}
        ]
    }
}
```

**Semantics**: During deserialization, the `__tuple__` array is restored as a Python tuple.

**Important**: `__tuple__` is a framework reserved key. Custom expressions' `get_params()` return values must NOT use this key.

## Scalar Type Rules

| Python Type | JSON Representation | Notes |
|-------------|---------------------|-------|
| `str` | string | |
| `int` | number | |
| `float` | number | |
| `bool` | boolean | |
| `None` | null | |
| `list` | array | Recursively serialize elements |
| `dict` | object | Recursively serialize values |
| `tuple` | object | Use `__tuple__` marker |
| `BaseExpression` | object | Use `__expr__` marker |
| `set` | - | Not supported, convert to list |
| Other custom objects | - | Must handle in `get_params()` |

## Serialization Flow

1. Call `expression.get_params()` to get parameter dictionary
2. Recursively process values in `params`:
   - `BaseExpression` → `{"__expr__": serialize(expr)}`
   - `tuple` → `{"__tuple__": [...]}`
   - `list` → recursively process elements
   - `dict` → recursively process values
   - others → pass through directly
3. Add `type` (class name) and `module` (module path)

## Deserialization Flow

1. Validate `type` and `module` exist
2. Find class via `ExpressionRegistry.lookup()`
3. Call `_reconstruct(cls, dialect, params)` to rebuild instance
4. Recursively process nested structures in `params`:
   - `__expr__` → `deserialize(value, dialect)`
   - `__tuple__` → tuple(recursively process elements)
   - others → recursively process

## Related Documents

- [Core Documentation](./serialization.md)
- [Extending Guide](./extending.md)
- [Migration Guide](./migration.md)