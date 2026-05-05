# Extending Guide: Implementing Serializable Expressions

This document is for backend developers, explaining how to implement serialization for custom expressions.

## Basic Requirements

Expression classes must meet the following requirements to be correctly handled by the serialization framework:

1. Inherit from `BaseExpression`
2. `__init__` parameter names must correspond to attribute names (using `_` prefix for private attributes or same-named attributes)
3. Use `get_params()` to return serializable parameters

## get_params() Convention

The default `get_params()` implementation automatically infers using `inspect.signature`:

- Parameter `foo` → attribute `self._foo` or `self.foo`
- `VAR_POSITIONAL (*args)` → list
- `VAR_KEYWORD (**kwargs)` → skipped (requires manual override)

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, name, value):
        super().__init__(dialect)
        self._name = name
        self._value = value
    # No need to manually implement get_params(), default implementation auto-extracts
```

### Custom get_params()

Override this method when default inference doesn't apply:

```python
def get_params(self) -> dict:
    params = super().get_params()
    # Add or modify parameters
    params["custom_key"] = self._custom_value
    return params
```

## Registration Mechanism

### Auto-Registration

Built-in expressions are auto-registered to `ExpressionRegistry` via `_auto_register_builtins()`.

### Manual Registration

Custom expressions need manual registration:

```python
from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry

ExpressionRegistry.register(MyExpression)
```

## Four Special Cases

### 1. Dialect-Specific Enum Parameters

Some dialects have specific enum values (e.g., PostgreSQL's `IsolationLevel`):

```python
class MyTransactionExpression(BaseExpression):
    def __init__(self, dialect, isolation_level: str = "READ COMMITTED"):
        super().__init__(dialect)
        self._isolation_level = isolation_level  # Accept string, not enum

# get_params() returns string, dialect-independent
```

### 2. State Set via Fluent API

State modified via fluent API must be synced to `__init__` parameters:

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, hint: str = None):
        super().__init__(dialect)
        self._hint = hint  # Both __init__ parameter and fluent API target

    def with_hint(self, hint: str):
        self._hint = hint
        return self
```

### 3. set Type Parameters

`set` type cannot be directly JSON serialized; convert to list in `get_params()`:

```python
def get_params(self) -> dict:
    params = super().get_params()
    params["columns"] = list(self._columns)  # set -> list
    return params
```

### 4. Circular References

The current framework doesn't detect circular references. If self-reference is possible, truncate in `get_params()`:

```python
def get_params(self) -> dict:
    params = {"id": self._id, "name": self._name}
    if self._parent is not None:
        params["parent_id"] = self._parent._id  # Only store ID, not object
    return params
```

## IntrospectionExpression Convention

`IntrospectionExpression` subclasses (like `TableListExpression`) have a `None` filtering rule:

- Optional parameters with value `None` should not appear in `params`

```python
class TableListExpression(IntrospectionExpression):
    def get_params(self) -> dict:
        params = {}
        if self._schema is not None:
            params["schema"] = self._schema
        # include_views defaults to True, always included
        params["include_views"] = self._include_views
        return params
```

## Error Contract

All paths through `_reconstruct()`, `TypeError` is wrapped as `ExpressionDeserializationError`. This ensures callers only need to catch one exception type.

## Related Documents

- [Core Documentation](./serialization.md): Serialization mechanism
- [Format Reference](./format-reference.md): Complete ExpressionSpec specification