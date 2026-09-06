# Customization

## Overview

rhosocial-activerecord is designed to be extensible. You can customize the framework at several levels:

1. **Custom Expressions** — Create new expression classes for SQLite-specific SQL syntax
2. **Custom Data Types** — Define new DataType subclasses for custom column types
3. **Custom Type Adapters** — Register converters between Python objects and database values

## Customization Architecture

The framework uses a **delegation + composition** pattern:

- **Expressions** produce SQL by delegating to their bound dialect's `format_*()` methods
- **DataTypes** produce DDL SQL by delegating to `dialect.format_data_type()`
- **Dialects** are composed from small, focused mixins
- **Type Adapters** convert between Python values and database values, registered in `TypeRegistry`

This means you can extend any layer without modifying the core library.

## When to Customize

| Need | Approach |
|------|----------|
| SQLite has a function not in the expression library | Custom Expression |
| SQLite has a column type not in the type system | Custom DataType |
| Python object needs custom serialization | Custom Type Adapter |

## Custom Expressions

The SQLite backend extends core expression classes with SQLite-specific SQL syntax. To add new expression types:

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class MyCustomExpression(BaseExpression):
    def to_sql(self, dialect):
        # Generate SQLite-specific SQL
        return "MY_CUSTOM_SQL(...)"
```

### Example: JSON Path Expression

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class JsonPathExpression(BaseExpression):
    def __init__(self, column, path):
        self.column = column
        self.path = path

    def to_sql(self, dialect):
        return f"json_extract({self.column}, ?)"

    @property
    def params(self):
        return [self.path]
```

See [Custom Expressions](../../../../backend/template/customization/custom_expressions.md) for detailed guidelines.

## Custom Data Types

SQLite uses a dynamic type system. To add support for new Python types:

```python
from rhosocial.activerecord.backend.impl.sqlite.types import SQLiteDataType

@SQLiteDataType.handles(MyClass)
class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        import json
        return json.dumps(value.__dict__)

    @staticmethod
    def from_sql(value, dialect):
        import json
        return MyClass(**json.loads(value))
```

See [Custom Data Types](../../../../backend/template/customization/custom_types.md) for detailed guidelines.

## Custom Type Adapters

To register custom type converters:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.type_registry.register(MyClass, MyAdapter)
```

### Adapter Interface

```python
class MyAdapter:
    @staticmethod
    def to_sql(value, dialect):
        """Convert Python value to SQLite value."""
        return serialized_value

    @staticmethod
    def from_sql(value, dialect):
        """Convert SQLite value to Python value."""
        return python_value
```

See [Custom Type Adapters](../../../../backend/template/customization/custom_adapters.md) for detailed guidelines.

## Related Topics

- [Type Adapters](../type_adapters/README.md) — type conversion system
- [Dialect Expressions](../backend_specific_features/README.md) — expression system architecture
- [Field Types](../backend_specific_features/README.md) — DataType hierarchy

💡 *AI Prompt:* "How do I add support for a SQLite-specific function that isn't in the expression library?"
