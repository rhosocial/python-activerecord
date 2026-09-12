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
from rhosocial.activerecord.backend.expression.bases import BaseExpression

class MyCustomExpression(BaseExpression):
    def __init__(self, dialect, *args):
        super().__init__(dialect)
        self.args = args

    @property
    def format_method(self) -> str:
        # Never override to_sql() — declare the dialect method that
        # renders this expression; the dialect implements
        # format_my_custom_sql(self, expression) generating SQLite-specific SQL.
        return "format_my_custom_sql"
```

### Example: JSON Path Expression

```python
from rhosocial.activerecord.backend.expression.bases import BaseExpression

class JsonPathExpression(BaseExpression):
    def __init__(self, dialect, column, path):
        super().__init__(dialect)
        self.column = column
        self.path = path

    @property
    def format_method(self) -> str:
        # Name of the dialect format_*() method that renders this expression.
        # Never override to_sql() — BaseExpression implements rendering;
        # your dialect implements format_json_path(self, expression).
        return "format_json_path"

    @property
    def params(self):
        return (self.path,)
```

See [Custom Expressions](../../template/customization/custom_expressions.md) for detailed guidelines.

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

See [Custom Data Types](../../template/customization/custom_types.md) for detailed guidelines.

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

See [Custom Type Adapters](../../template/customization/custom_adapters.md) for detailed guidelines.

## Related Topics

- [Type Adapters](../type_adapters/README.md) — type conversion system
- [Dialect Expressions](../backend_specific_features/README.md) — expression system architecture
- [Field Types](../backend_specific_features/README.md) — DataType hierarchy

💡 *AI Prompt:* "How do I add support for a SQLite-specific function that isn't in the expression library?"
