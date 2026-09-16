# Data Types

Data types (`DataType`) are an important part of the expression system, used to describe database column types in DDL, model field declarations, and migrations.

Data types follow the same **generic / backend-specific** layering as the expression system, and the two cooperate closely through "generic base classes + backend subclasses".

## Overview

`DataType` inherits from `BaseExpression` and follows the **same binding rules as every other expression**:

> **Dialect binding is per-node**: the dialect is the conventional **first constructor argument — optional, default `None`**. It can be supplied at construction, or deferred and set later through the `dialect` property. The setter affects **only the node it is set on** — there is no propagation to child nodes.

A data type therefore has a **declare → bind → render** lifecycle:

1. **declare**: a type may be constructed without a dialect — for model field declarations, migrations, and `UseSqlType` annotations. When the dialect is omitted, the remaining arguments must be passed **by keyword** (e.g. `VarCharType(length=255)`); a positional value would land in the dialect slot and be rejected by construction-time validation
2. **bind**: a dialect is attached per node — either at construction (`VarCharType(dialect, length=255)`) or later via the `dialect` property setter; a dialect's `parse_type()` factory (introspection) also returns bound instances
3. **render**: `to_sql()` takes **no arguments**; it reads the node's own bound dialect and delegates to its `format_data_type()`. Rendering a type with no bound dialect raises `ValueError` ("... has no dialect bound ...") — a deliberate fail-fast guard

```python
from rhosocial.activerecord.backend.expression.types import VarCharType

# declare: no dialect — remaining arguments must be keyword arguments
t = VarCharType(length=255)

# bind later (this node only), then render — to_sql() takes no arguments
t.dialect = dialect
sql, params = t.to_sql()
```

### Why Is the Dialect Argument Optional?

Data types follow the **same constructor convention as every expression**: the dialect is the conventional first argument, optional with a default of `None` (deferred binding is legal). The difference is only in *when* each kind of expression is typically built.

Ordinary query expressions (e.g. `Column`, `ComparisonPredicate`) are constructed at **query execution time**, when a dialect context necessarily already exists, so they almost always pass the dialect immediately:

```python
# Ordinary expression: the first argument is the dialect instance
Column(dialect, "name")          # ✅
Literal(dialect, 18)             # ✅
```

Data types, by contrast, are often created at a moment when **the dialect is not yet determined**. The most typical scenario is **`ActiveRecord` model field declaration**:

```python
from rhosocial.activerecord.base.fields import UseSqlType

class Product(ActiveRecord):
    size: Annotated[str, UseSqlType(MySQLEnumType(values=['S', 'M', 'L']))]
```

Model classes define their field type annotations at **import time**, when the model has **not yet been configured with any backend** — the dialect is only determined later, at `configure(config, backend)`. This is exactly what deferred binding is for: construct without a dialect, bind later.

When `ActiveRecord` builds DDL, the framework walks the collected definitions, **copies the declaration-time instances and injects the dialect node-by-node at build time** — producing a self-sufficient tree in which every node is bound. Each node then renders through its own argument-less `to_sql()`:

```
Model field declaration (unbound type)              DDL construction (build time)
Annotated[str, UseSqlType(MySQLEnumType(...))]  ──►  copy + inject dialect node-by-node ──► node.to_sql()
int (auto-inferred IntegerType)                 ──►  copy + inject dialect node-by-node ──► node.to_sql()
```

This "types defer dialect binding, DDL construction binds each node" design means:

- The same model class can be reused across backends without changing field declarations
- The dialect is injected at the moment DDL is generated; users never bind manually
- Types stay decoupled from dialects, matching the schema-time vs query-time role split
- Rendering stays stateless: `to_sql()` simply reads the node's own bound dialect — no reconstruction, no propagation, no copies at render time

## Value-Object Semantics

`DataType` instances are **value objects**: two instances of the same class with the same logical parameters are **equal and hash-equal**, regardless of whether they carry a dialect reference. Equality compares the type's logical parameters (`_type_params()`) plus its `dialect_options`; the hash covers type identity and type params only. The bound dialect is ignored by both — binding (or re-binding) a dialect never affects `==` or `hash`.

```python
a = IntegerType()
b = IntegerType()
assert a == b          # value object: equal (dialect ignored)
assert hash(a) == hash(b)
```

`dialect_options` is the dict of **backend-specific exotic parameters** (e.g. `{'unsigned': True}`, charset, length semantics) that travels with the type instance and is consumed by the backend's formatters. It participates in **equality** but deliberately **not** in the hash, so mutable option mappings cannot break hashing.

## Core Types

Core types are defined in `rhosocial.activerecord.backend.expression.types` and cover the SQL types shared by most databases:

| Category | Type classes |
|----------|--------------|
| Integer | `TinyIntType`, `SmallIntType`, `IntType`, `IntegerType`, `BigIntType` |
| Numeric | `FloatType`, `RealType`, `DoubleType`, `DecimalType` |
| String | `CharType`, `VarCharType`, `TextType` |
| Boolean | `BooleanType` |
| Binary | `BlobType`, `BinaryType`, `VarBinaryType` |
| Enum | `EnumType` (values required) |
| Date/time | `DateType`, `TimeType`, `TimeTzType`, `DateTimeType`, `TimestampType`, `TimestampTzType`, `IntervalType` |
| JSON | `JsonType`, `JsonBType` |
| Network | `InetType`, `CidrType`, `MacAddrType` |
| UUID | `UUIDType` |
| Array | `ArrayType` |
| Custom | `CustomType` |

Core types can be instantiated without a dialect (deferred binding), but cannot render until one is bound.

## Backend-Specific Types

Each backend defines its own subtypes on top of the core types, **named with the backend name as a prefix**:

| Backend | Examples |
|---------|----------|
| SQLite | `SQLiteIntegerType(IntegerType)`, `SQLiteTextType(TextType)`, `SQLiteBlobType(BlobType)` |
| MySQL | `MySQLIntType(IntegerType)`, `MySQLTinyIntType(TinyIntType)`, `MySQLEnumType(DataType)`, `MySQLSetType(DataType)`, `MySQLGeometryType(DataType)` |
| PostgreSQL | `PostgresSerialType(DataType)`, `PostgresUUIDType(DataType)`, `PostgresTSVectorType(DataType)`, `PostgresJsonPathType(DataType)` |

Backend-specific types usually inherit the corresponding core type; they inherit `DataType` directly only when the type is backend-exclusive (e.g. MySQL `ENUM`, PostgreSQL `SERIAL`).

Each backend-defined type declares a **namespaced generic type name** — the backend slug as prefix (e.g. `SQLiteIntegerType.name == "sqlite_integer"`). This prefix is enforced at class-definition time (`__init_subclass__`): a type defined outside the core types package whose name lacks the backend prefix is rejected, keeping the dispatch keys of different backends isolated.

## How Generic and Backend-Specific Types Cooperate

### Rendering: Naming-Family Dispatch, No Registry

There is **no type registry**. A dialect's supported-type surface **is** the set of its naming-family methods — the two families have a strict 1:1 correspondence:

- `format_data_type_<name>(data_type)` — renders the type whose generic name is `<name>`
- `supports_data_type_<name>() -> bool` — truthfully declares whether `<name>` is supported

`format_data_type(data_type)` is the **total dispatcher**: it routes by the instance's generic `name` to the corresponding family member. A backend type with the namespaced name `sqlite_integer` is dispatched to `format_data_type_sqlite_integer`; each concrete (namespaced) type is dispatched by its own name, not by Python subclass relationship.

```python
class SQLiteIntegerType(IntegerType):
    name = "sqlite_integer"

# Dispatch is by generic name:
# SQLiteIntegerType instance -> dialect.format_data_type_sqlite_integer()
```

A dialect therefore declares per-type formatters for exactly the names it supports; there is no implicit "inherits the generic renderer" fallback for namespaced types.

### Strictly Faithful Rendering: No Silent Substitution

A dialect renders **only what it natively supports**. Dispatching a type the dialect does not support raises `TypeError` — there is no `format_data_type_<name>` member to route to, which is the honest "unsupported here" signal (unsupported types are simply **absent** from the naming family, never faked). `CustomType` passthrough additionally requires the backend to implement `format_data_type_custom` explicitly, so raw-string rendering is always a deliberate, auditable backend choice (a security-sensitive escape hatch).

Generic auto-increment is a typical example: declaring a generic auto-increment type on PostgreSQL raises an error pointing to `PostgresSerialType` — the framework never silently substitutes an approximate semantics.

### Capability Detection

Dialects expose their type surface through the same naming family plus two mapping queries:

```python
# Single-type check: supports_data_type_<name>() naming family
if dialect.supports_data_type_text():
    ...

# Full map: {<generic name>: concrete DataType class} of every supported type
for name, dt_cls in dialect.supports_data_types().items():
    print(name, dt_cls.__name__)
```

`supports_data_types()` is discovered from the dialect's own naming-family members (and backend dialects merge their namespaced entries into the inherited map). Its keys are exactly the dispatch keys of the `format_data_type_*` family.

### Cross-Backend Suggestions (suggested_data_types)

`suggested_data_types() -> Dict[str, type]` is the counterpart for **cross-backend type consistency**: for generic types the dialect does **not** natively support, it may suggest a replacement `DataType` class.

- Keys use the same generic-name namespace (`"uuid"`, `"enum"`, ...) and are **disjoint** from the keys of `supports_data_types()` — a type the dialect renders needs no suggestion
- Values are concrete `DataType` classes (e.g. SQLite suggests `uuid`/`enum` → `SQLiteTextType`, `binary`/`varbinary` → `SQLiteBlobType`)
- Suggestions only — how (and whether) the user layer adopts them is up to ActiveRecord/application code
- Empty dict by default; honesty principle applies here too: never fake a suggestion

### Integration with Model Fields

#### Automatic Inference

Fields declared with plain Python annotations are resolved to generic `DataType` instances by the ActiveRecord field layer, using a **backend-neutral** "reasonable lowest common denominator" mapping (e.g. `str` → a text type, `int` → an integer type). It deliberately avoids backend-exclusive types such as `UUID`/`JSONB`/`ENUM`. Dialects do not provide per-call inference hooks; instead they advertise their type surface (`supports_data_types()`) and cross-backend suggestions (`suggested_data_types()`), which the DDL generator consults when resolving portable field declarations.

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

Type resolution priority: `UseSqlType` annotation → backend-neutral default inference.

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