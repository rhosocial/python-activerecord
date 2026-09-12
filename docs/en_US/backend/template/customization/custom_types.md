# Custom Data Types

## Overview

rhosocial-activerecord's type system is extensible. You can create custom DataType subclasses for database-specific column types that aren't covered by the core type hierarchy.

**Key principle**: DataTypes are expressions. They inherit from `BaseExpression` and follow the same delegation pattern — `to_sql()` delegates to the dialect's `format_data_type()` method. This means DataTypes benefit from the same extensibility, serialization support, and dialect delegation as other expressions.

## DataType Base Class

All data types inherit from `DataType` in `rhosocial.activerecord.backend.expression.types._base`. DataType instances are **value objects** — two instances of the same type compare equal regardless of dialect binding.

Lifecycle: **declare → bind → render** (binding is per-node, like every expression)

1. **Declare** — Construct without a dialect (model field declarations, migrations). When the dialect is omitted, the remaining arguments must be passed **by keyword** (a positional value would land in the dialect slot)
2. **Bind** — Attach a dialect per node: pass it as the conventional first constructor argument, or set it later via the `dialect` property (the setter affects **only this node** — no propagation). The dialect's `parse_type()` factory also returns bound instances
3. **Render** — `to_sql()` takes **no arguments**; it reads the node's own bound dialect and delegates to `dialect.format_data_type(self)`. Rendering unbound raises `ValueError` ("... has no dialect bound ...")

## Creating a Simple DataType

For types with no parameters:

```python
from rhosocial.activerecord.backend.expression.types._base import DataType


class MyCustomGeoType(DataType):
    """Custom geographic type."""
    name = "my_geo"  # generic name — the dispatch key (backend-prefixed, see below)
    pass
```

## Creating a DataType with Parameters

For types that accept parameters (like precision, length, etc.):

```python
from rhosocial.activerecord.backend.expression.types._base import DataType
from typing import Optional


class MySQLVectorType(DataType):
    """MySQL VECTOR(n) -- MySQL 9.0+."""
    name = "mysql_vector"

    dim: int

    def __init__(self, dialect=None, *, dim: int):
        super().__init__(dialect)
        self.dim = dim

    def _type_params(self) -> tuple:
        return (self.dim,)
```

**Important**: Do **not** hand-write `__eq__`/`__hash__`. The `DataType` base provides unified value-object semantics: equality compares the logical parameters returned by `_type_params()` plus `dialect_options`; the hash covers type identity and `_type_params()` only. The bound dialect is ignored by both. Override `_type_params()` so the base comparisons see your logical content.

Backend-defined types must also declare a **backend-prefixed** generic `name` (e.g. `mysql_vector`) — the prefix is enforced at class-definition time, keeping dispatch keys isolated per backend.

## Extending a Core Type

To create a backend-specific variant of an existing type:

```python
from rhosocial.activerecord.backend.expression.types import IntegerType


class MySQLUnsignedIntType(IntegerType):
    """MySQL INTEGER UNSIGNED."""
    name = "mysql_int_unsigned"

    def __init__(self, dialect=None, *, unsigned: bool = True,
                 dialect_options=None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned

    def _type_params(self) -> tuple:
        return (self.unsigned,)

    @classmethod
    def synonyms(cls) -> set:
        """Mark as equivalent to IntegerType for schema comparison."""
        return {'IntegerType'}
```

The `synonyms()` method marks types as structurally equivalent for schema comparison purposes.

Backend-specific exotic parameters can also travel in `dialect_options` (e.g. `{'unsigned': True}`) — a dict consumed by the backend formatters; it participates in equality but not in the hash.

## Registering a Type Formatter

There is **no type registry**. A dialect's supported-type surface **is** its set of naming-family methods, with a strict 1:1 correspondence:

- `format_data_type_<name>(data_type)` — renders the type whose generic `name` is `<name>`
- `supports_data_type_<name>() -> bool` — truthfully declares whether `<name>` is supported

`format_data_type(data_type)` dispatches by the instance's `name` to the corresponding family member and raises `TypeError` when no member exists (the honest "unsupported" signal):

```python
class MyTypeSupportMixin:
    """Adds type formatting for custom types (compose into your dialect)."""

    def format_data_type_mysql_vector(self, data_type: MySQLVectorType):
        return f"VECTOR({data_type.dim})", ()

    def supports_data_type_mysql_vector(self) -> bool:
        return True

    def format_data_type_mysql_int_unsigned(self, data_type: MySQLUnsignedIntType):
        return "INT UNSIGNED", ()

    def supports_data_type_mysql_int_unsigned(self) -> bool:
        return True
```

Then compose this mixin into your dialect:

```python
class MyCustomDialect(PostgresDialect, MyTypeSupportMixin):
    pass
```

The naming-family methods **are** the registration: `dialect.format_data_type()` routes to `format_data_type_<name>` by the type's generic name, and `supports_data_types()` discovers the supported map from these members (fold your namespaced entries into it when overriding).

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
