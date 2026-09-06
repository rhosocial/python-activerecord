# Data Types

Data types (`DataType`) are an important part of the expression system, used to describe database column types in DDL, model field declarations, and migrations.

Data types follow the same **generic / backend-specific** layering as the expression system, and the two cooperate closely through "generic base classes + backend subclasses".

## Overview

`DataType` inherits from `BaseExpression`, but has one key difference from other expressions:

> **Expressions are query-time objects** (usually constructed with a dialect); **types are schema-time objects** (declarable before a connection exists; the dialect is optional).

Therefore `DataType` follows a **declare → bind → render** three-stage lifecycle:

1. **declare**: types can be constructed without a dialect — for model field declarations, migrations, and `UseSqlType` annotations
2. **bind**: a dialect is attached via the constructor (`dialect=...`), the `bind()` method, or a dialect's `parse_type()` factory (introspection)
3. **render**: `to_sql()` delegates to the bound dialect's `format_data_type()`; a dialect may also be supplied per call

```python
from rhosocial.activerecord.backend.expression.types import IntegerType

# declare: no dialect needed
t = IntegerType()

# bind: renderable after binding a dialect
sql, params = t.bind(dialect).to_sql()
# or
sql, params = t.to_sql(dialect=dialect)
```

Calling `to_sql()` on a generic type without a bound dialect raises `ValueError` — a type must be attached to a dialect to produce a concrete SQL type name.

### Why Don't Data Types Take a Dialect Instance Directly?

Data types deliberately have a **different constructor signature** from other expressions. Ordinary expressions (e.g. `Column`, `ComparisonPredicate`) require a dialect instance as their first positional argument, because they are built at **query execution time**, when a dialect context necessarily already exists:

```python
# Ordinary expression: the first argument must be a dialect instance
Column(dialect, "name")          # ✅
Literal(dialect, 18)             # ✅
```

Data types are different — they are often created at a moment when **the dialect is not yet determined**. The most typical scenario is **`ActiveRecord` model field declaration**:

```python
from rhosocial.activerecord.base.fields import UseSqlType

class Product(ActiveRecord):
    size: Annotated[str, UseSqlType(MySQLEnumType(values=['S', 'M', 'L']))]
```

Model classes define their field type annotations at **import time**, when the model has **not yet been configured with any backend** — the dialect is only determined later, at `configure(config, backend)`. If constructing a type required a dialect, field declarations would have to wait for configuration, which would:

- Break the **declarative** nature of fields: field types should be decoupled from configuration, allowing the same model class to be reused across environments (tests, production, different backends)
- Cause a **circular dependency**: `ActiveRecord` needs types to generate DDL, while types would need a dialect to exist

Therefore, field declarations hold **unbound type instances**. When `ActiveRecord` builds DDL, the framework automatically injects the **currently configured dialect** — this is the `col_def.data_type.to_sql(dialect)` call in `format_column_definition()`:

```
Model field declaration (unbound type)              DDL construction (dialect injected)
Annotated[str, UseSqlType(MySQLEnumType(...))]  ──►  col_def.data_type.to_sql(dialect)
int (auto-inferred IntegerType)                 ──►  render after binding the current dialect
```

This "types defer dialect binding, DDL construction injects it automatically" design means:

- The same model class can be reused across backends without changing field declarations
- The dialect is naturally injected at the moment DDL is generated; users never bind manually
- Types stay decoupled from dialects, matching the schema-time vs query-time role split

This is why data types are treated **specially**: although they inherit `BaseExpression`, they support deferred binding via the optional dialect parameter, `bind()`, and `to_sql(dialect=...)`, distinguishing them from query expressions that always carry a dialect.

## Value-Object Semantics

`DataType` instances are **value objects**: two instances with the same logical parameters are **equal and hash-equal**, regardless of whether they carry a dialect reference. `bind()` returns a copy of the original instance and does not modify it, so binding never affects `==` or `hash`.

```python
a = IntegerType()
b = IntegerType()
assert a == b          # value object: equal
assert hash(a) == hash(b)
```

## Core Types

Core types are defined in `rhosocial.activerecord.backend.expression.types` and cover the SQL types shared by most databases:

| Category | Type classes |
|----------|--------------|
| Integer | `TinyIntType`, `SmallIntType`, `IntType`, `IntegerType`, `BigIntType` |
| Numeric | `FloatType`, `RealType`, `DoubleType`, `DecimalType` |
| String | `CharType`, `VarCharType`, `TextType` |
| Boolean | `BooleanType` |
| Binary | `BlobType`, `BinaryType`, `VarBinaryType` |
| Date/time | `DateType`, `TimeType`, `TimeTzType`, `DateTimeType`, `TimestampType`, `TimestampTzType`, `IntervalType` |
| JSON | `JsonType`, `JsonBType` |
| Network | `InetType`, `CidrType`, `MacAddrType` |
| UUID | `UUIDType` |
| Array | `ArrayType` |
| Custom | `CustomType` |

Core types can be instantiated, but cannot render without a bound dialect.

## Backend-Specific Types

Each backend defines its own subtypes on top of the core types, **named with the backend name as a prefix**:

| Backend | Examples |
|---------|----------|
| SQLite | `SQLiteIntegerType(IntegerType)`, `SQLiteTextType(TextType)`, `SQLiteBlobType(BlobType)` |
| MySQL | `MySQLIntType(IntegerType)`, `MySQLTinyIntType(TinyIntType)`, `MySQLEnumType(DataType)`, `MySQLSetType(DataType)`, `MySQLGeometryType(DataType)` |
| PostgreSQL | `PostgresSerialType(DataType)`, `PostgresUUIDType(DataType)`, `PostgresTSVectorType(DataType)`, `PostgresJsonPathType(DataType)` |

Backend-specific types usually inherit the corresponding core type; they inherit `DataType` directly only when the type is backend-exclusive (e.g. MySQL `ENUM`, PostgreSQL `SERIAL`).

## How Generic and Backend-Specific Types Cooperate

### Render Inheritance: Backend Subtypes Automatically Get the Generic Renderer

Dialect type renderers are registered via the `@handles()` decorator (`DDLTypeMixin`). For core generic types, renderers are matched by **subclass relationship**:

```python
class SQLiteIntegerType(IntegerType):
    ...

# The dialect registered a renderer for IntegerType
# SQLiteIntegerType automatically uses that renderer,
# unless the backend explicitly registered a more specific one
```

This means a backend only needs to register renderers for types where it **differs**; everything else inherits the generic renderer, dramatically reducing backend work.

### Strictly Faithful Rendering: No Silent Substitution

A dialect renders **only what it natively supports**. `format_data_type()` raises `TypeError` (with guidance on how to register) for unregistered types; `CustomType` additionally requires the backend to explicitly `@handles(CustomType)` before raw-string passthrough is allowed (a security-sensitive escape hatch).

Generic auto-increment is a typical example: declaring a generic auto-increment type on PostgreSQL raises an error pointing to `PostgresSerialType` — the framework never silently substitutes an approximate semantics.

### Capability Detection

Dialects expose type capability query methods:

```python
if dialect.supports_data_type(MyType):
    # The dialect can render MyType
    ...

# List all (type class, SQL name) pairs registered by the dialect
for dt_cls, sql_name in dialect.supports_data_types():
    print(dt_cls.__name__, sql_name)
```

### Integration with Model Fields

#### Automatic Inference (suggest_column_type)

When declaring model fields, the dialect maps Python types to generic `DataType` instances via `suggest_column_type(python_type)`:

| Python type | Inferred core type |
|-------------|--------------------|
| `str` | `TextType` |
| `int` | `IntegerType` |
| `bool` | `BooleanType` |
| `float` | `DoubleType` |
| `bytes` | `BlobType` |
| `datetime` | `DateTimeType` |
| `date` | `DateType` |
| `Decimal` | `DecimalType` |
| `uuid.UUID` | `UUIDType` |
| `Enum` | `VarCharType(length=64)` |
| `ipaddress` address/network | `InetType` / `CidrType` |

This mapping is a **backend-neutral** "reasonable lowest common denominator" — it deliberately avoids backend-exclusive types such as `UUID`/`JSONB`/`ENUM`. Backends that want richer inference override `suggest_column_type`.

#### Explicit Specification (UseSqlType)

The field-level `UseSqlType` annotation takes precedence over automatic inference and is the standard way to use backend-specific types:

```python
from typing import Annotated
from rhosocial.activerecord.base.fields import UseSqlType
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLEnumType

class Product(ActiveRecord):
    # Explicitly specify a MySQL-specific type
    size: Annotated[str, UseSqlType(MySQLEnumType(values=['S', 'M', 'L']))]
```

Type resolution priority: `UseSqlType` annotation → `dialect.suggest_column_type()` → backend-neutral default.

### Introspection and Sync (parse_type)

When a dialect implements `parse_type(raw)` (the `DDLTypeSupport` protocol), it can parse a raw type string returned by the database back into a `DataType` object for schema introspection and comparison. Dialects without this interface fall back to `CustomType(raw=raw)`.

## Equivalence and Synonyms

`synonyms()` and `is_equivalent()` are used **only** for intra-dialect schema-comparison normalization (e.g. SQLite affinity collapse). **Never** register cross-dialect equivalences — rendering stays strictly faithful and dialect differences must remain explicit.

```python
# Only for schema-comparison scenarios within the same backend
if type_a.is_equivalent(type_b):
    ...
```

## Related Documentation

- [Expression System Overview](README.md): generic / backend-specific design philosophy and serialization
- [Custom Backend](../custom_backend.md): dialect protocols, connection configuration, and backend integration