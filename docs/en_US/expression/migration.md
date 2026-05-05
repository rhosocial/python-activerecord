# Migration Guide

This document explains version changes in the serialization format and migration strategies.

## dev26 Change: Introducing `__expr__` Marker

### Change Content

Starting from dev26, nested expressions use `__expr__` explicit marker instead of the original three-key heuristic detection:

**Old format (deprecated)**:
```python
{
    "type": "WhereClause",
    "params": {
        "condition": {
            "type": "ComparisonPredicate",
            "module": "...",
            "params": {...}
        }
    }
}
```

**New format**:
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

### Impact Scope

- **Expressions in memory**: No migration needed; serialization automatically uses new format
- **Persisted ExpressionSpec** (e.g., cache, logs, database fields): Needs migration
- **JSON messages in transit**: Needs migration (depends on whether receiver has upgraded)

### Migration Strategies

#### Option 1: Version Field

Add `spec_version` field in ExpressionSpec:

```python
{
    "spec_version": "1.0",
    "type": "...",
    "module": "...",
    "params": {...}
}
```

At deserialization, select parsing method based on version.

#### Option 2: Auto-Conversion

Add compatibility logic at deserialization entry:

```python
def deserialize(spec: dict, dialect):
    # Detect old format (has three keys but no __expr__)
    if "type" in spec.get("params", {}) and "module" in spec.get("params", {}):
        # Wrap to new format
        for key, value in spec["params"].items():
            if isinstance(value, dict) and "type" in value and "module" in value:
                spec["params"][key] = {"__expr__": value}
    return _deserialize_impl(spec, dialect)
```

#### Option 3: Re-serialization

If old ExpressionSpec source is controllable (e.g., internal cache), auto-re-serialize at runtime:

```python
# Detect old format
expr = legacy_deserialize(spec, dialect)
new_spec = serialize(expr)  # Auto-convert to new format
```

## Recommended Practices

1. **New projects**: Directly use dev26+ version, no need to worry about migration
2. **Existing projects**: Plan cache cleanup or migration scripts
3. **Long-term compatibility**: Reserve `spec_version` field in ExpressionSpec

## Related Documents

- [Core Documentation](./serialization.md)
- [Format Reference](./format-reference.md)