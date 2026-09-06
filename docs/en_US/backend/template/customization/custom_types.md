# Custom Data Types

## Overview

rhosocial-activerecord's type system is extensible. You can create custom DataType subclasses for database-specific column types that aren't covered by the core type hierarchy.

**Key principle**: DataTypes are expressions. They inherit from `BaseExpression` and follow the same delegation pattern — `to_sql()` delegates to the dialect's `format_data_type()` method. This means DataTypes benefit from the same extensibility, serialization support, and dialect delegation as other expressions.

## DataType Base Class

All data types inherit from `DataType` in `rhosocial.activerecord.backend.expression.types._base`. DataType instances are **value objects** — two instances of the same type compare equal regardless of dialect binding.

Lifecycle: **declare → bind → render**

1. **Declare** — Construct without a dialect (model field declarations, migrations)
2. **Bind** — Attach a dialect via constructor, `bind()`, or `parse_type()` factory
3. **Render** — `to_sql()` delegates to `dialect.format_data_type(self)`

## Creating a Simple DataType

For types with no parameters:

```python
from rhosocial.activerecord.backend.expression.types._base import DataType


class MyCustomGeoType(DataType):
    """Custom geographic type."""
    pass
```

## Creating a DataType with Parameters

For types that accept parameters (like precision, length, etc.):

```python
from rhosocial.activerecord.backend.expression.types._base import DataType
from typing import Optional


class MySQLVectorType(DataType):
    """MySQL VECTOR(n) -- MySQL 9.0+."""
    dim: int

    def __init__(self, dialect=None, *, dim: int):
        super().__init__(dialect)
        self.dim = dim

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.dim == other.dim

    def __hash__(self) -> int:
        return hash((type(self), self.dim))
```

**Important**: You must implement `__eq__` and `__hash__` for types with parameters. The comparison is based on the type's logical parameters, not the dialect binding.

## Extending a Core Type

To create a backend-specific variant of an existing type:

```python
from rhosocial.activerecord.backend.expression.types import IntegerType


class MySQLUnsignedIntType(IntegerType):
    """MySQL INTEGER UNSIGNED."""
    unsigned: bool = True

    def __init__(self, dialect=None, *, unsigned: bool = True):
        super().__init__(dialect)
        self.unsigned = unsigned

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.unsigned == other.unsigned

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned))

    @classmethod
    def synonyms(cls) -> set:
        """Mark as equivalent to IntegerType for schema comparison."""
        return {'IntegerType'}
```

The `synonyms()` method marks types as structurally equivalent for schema comparison purposes.

## Registering a Type Formatter

To render your custom type to SQL, register a formatter using the `@handles()` decorator:

```python
from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin


class MyTypeSupportMixin(DDLTypeMixin):
    """Mixin that adds type formatting for custom types."""

    @DDLTypeMixin.handles(MySQLVectorType)
    def format_data_type_vector(self, data_type: MySQLVectorType):
        return f"VECTOR({data_type.dim})", ()

    @DDLTypeMixin.handles(MySQLUnsignedIntType)
    def format_data_type_unsigned_int(self, data_type: MySQLUnsignedIntType):
        sql = "INT UNSIGNED"
        return sql, ()
```

Then compose this mixin into your dialect:

```python
class MyCustomDialect(PostgresDialect, MyTypeSupportMixin):
    pass
```

The `@handles()` decorator ensures your formatter is called when `dialect.format_data_type()` encounters your custom type.

## Using Custom Types in Models

### Direct Field Declaration

```python
class Product(ActiveRecord):
    embedding: list  # Will use the backend's array/VECTOR type

    @classmethod
    def table_name(cls) -> str:
        return 'products'
```

### Explicit Type Annotation with UseSqlType

For more control, use `UseSqlType` to specify the exact SQL type:

```python
from rhosocial.activerecord.base.fields import UseSqlType

class Product(ActiveRecord):
    embedding: UseSqlType[MySQLVectorType] = UseSqlType(dim=128)

    @classmethod
    def table_name(cls) -> str:
        return 'products'
```

## Checking Type Support at Runtime

Use the protocol system to check if a type is supported:

```python
from rhosocial.activerecord.backend.dialect.protocols import JSONSupport, ArraySupport

dialect = backend.dialect

if isinstance(dialect, JSONSupport) and dialect.supports_json_type():
    # JSON type is available
    ...

if isinstance(dialect, ArraySupport) and dialect.supports_array_type():
    # Array type is available
    ...
```

## See Also

- [Field Types](../backend_specific_features/field_types.md) — core DataType hierarchy
- [Custom Type Adapters](custom_adapters.md) — Python-to-database value conversion
- [Type Adapters](../type_adapters/README.md) — type conversion system
- [Core: Custom Types](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI Prompt:* "How do I add support for a database-specific column type?"
