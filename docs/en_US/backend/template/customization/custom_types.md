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

    #: The attributes that make two of these different columns. Read by
    #: ``__eq__``, ``__hash__`` and ``repr`` -- declare it, do not override a
    #: method to compute it.
    PARAMETERS = ("dim",)
```

**Important**: Do **not** hand-write `__eq__`/`__hash__`, and do not override a method to compute identity. The `DataType` base provides unified value-object semantics: equality compares the attributes named in the class constant `PARAMETERS`, and the hash covers the type's class plus those same attributes. The bound dialect is ignored by both. Declare `PARAMETERS` so the base comparisons see your logical content — and make sure it names *everything* that distinguishes two instances, because whatever it omits is invisible to `==`.

One field is deliberately **not** identity: `spelling`. It is how the instance is written, not what it is. The same column introspects as `character varying(30)` whichever word created it, so counting the spelling would make every introspected type unequal to its own declaration. The spelling still reaches the rendered SQL, and still round-trips through `get_params()`.

There is no bag of "backend-specific options" on a data type. Anything your type needs beyond the concept's own parameters is a **declared field** on the class, named in its `PARAMETERS`.

Backend-defined types must also declare a **backend-prefixed** generic `name` (e.g. `mysql_vector`) — the prefix is enforced at class-definition time, keeping dispatch keys isolated per backend.

## Extending a Core Type

Deriving from a core type is how a backend says "this is that concept, stored my way", and it is what makes `isinstance(col.data_type, IntegerType)` hold for the backend's own integer column. Inherit the core class **whenever there is one**; sit on `DataType` only when the concept is genuinely backend-exclusive, and then say why in the docstring.

Inheritance means identity only — "this class *is* that SQL type" — not membership in a family, and the chain stays linear (no multiple inheritance, no diamond edges).

Often you need no subclass at all. For a signedness variant of an existing concept, use the parameter the concept already has:

```python
from rhosocial.activerecord.backend.expression.types import IntegerType

IntegerType(unsigned=True)    # UNSIGNED INTEGER — same class, one flag
```

The four core integer classes take `unsigned: bool` precisely so that "signed vs unsigned" does not become a class per backend. Width, by contrast, *is* a class (`TinyIntType` … `BigIntType`), because a linear chain cannot hold a (width × signedness) grid.

If you genuinely need a subclass — the backend's storage differs, not just its spelling:

```python
from rhosocial.activerecord.backend.expression.types import IntegerType


class MySQLUnsignedIntType(IntegerType):
    """MySQL ``INT UNSIGNED``.

    The same concept as ``INTEGER`` with a different range, so it derives from
    the core class rather than sitting on ``DataType``. It re-declares
    ``PARAMETERS`` so ``unsigned`` still participates in ``==`` and ``hash`` —
    inheriting the base's declaration without naming the field would make two
    different ranges compare equal.
    """
    name = "mysql_int_unsigned"

    def __init__(self, dialect=None, *, unsigned: bool = True):
        super().__init__(dialect, unsigned=unsigned)

    PARAMETERS = ("unsigned",)
```

There is no `synonyms()` classmethod and no `is_equivalent()` method any more. A synonym of a concept is a *spelling* on the concept's own class, so there is never a second class for `==` to disagree with — see [Types](../expression/types.md) for the spelling mechanism.

If your concept has several legitimate written forms, extend that class's `SPELLINGS` rather than adding a class, and check the spelling in your formatter: a dialect that does not write `CLOB` should raise, not silently emit something else. The concept's default spelling (the first entry) must always render.

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
