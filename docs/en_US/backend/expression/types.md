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

`DDLSourceMixin` only collects and preserves the candidates in `UseSqlType`; it does not copy candidates, select one, or inject a dialect. After obtaining a dialect, the backend DDL consumer is responsible for copying/binding candidates and constructing renderable expressions. See [DDLSource Declarations](../../modeling/ddl_source.md).

## Value-Object Semantics

`DataType` instances are **value objects**: two instances of the same class with the same logical parameters are **equal and hash-equal**, regardless of whether they carry a dialect reference. Equality compares the type's **declared identity** — the attributes listed in the class constant `PARAMETERS` — and the hash covers the type's class plus those same attributes. The bound dialect is ignored by both — binding (or re-binding) a dialect never affects `==` or `hash`.

```python
a = IntegerType()
b = IntegerType()
assert a == b          # value object: equal (dialect ignored)
assert hash(a) == hash(b)
```

There is no separate bag of "backend-specific options" hanging off a data type. Anything a backend needs beyond the concept's own parameters is a **declared field** on the class — `CharType.length`, `DecimalType.precision`/`scale`, `EnumType.values`, `ArrayType.element_type`/`dimensions`, and `unsigned: bool` on the four integer classes — and it is listed in the class's `PARAMETERS`, hence in both `==` and `hash`.

## Spellings

Several concepts have more than one legitimate written form. Those are **spellings of one class**, not separate classes: the class carries a closed `SPELLINGS` tuple and a `spelling` keyword, and the *first* entry is the default.

```python
IntegerType()                          # spelling "integer"
IntegerType(spelling="int")            # the same class, the other word
assert IntegerType() == IntegerType(spelling="int")   # the same value
```

Why one class rather than two: `INT` and `INTEGER` are the same type, so code that has to ask "is this an integer column?" must not have to enumerate the spellings.

**Why the spelling is *not* part of `==`.** The tempting argument is that it was part of what was declared, so a difference in it is a difference worth reporting. But the schema differ does not compare two DDL scripts — it compares **what the database reports now** against **what was declared**, and a database reports its own house spelling no matter which word was typed. PostgreSQL reports `character varying(30)` for every `varchar(30)` column that exists, and SQL Server reports `DECIMAL` for a column declared as `NUMERIC`. Counting the spelling would therefore report a change on every such column that was never touched: a false positive on the one comparison that has to be right.

Nothing is lost. The spelling still reaches the rendered SQL — that is where the difference is real and visible:

```python
IntegerType()                        # renders INTEGER
IntegerType(spelling="int")          # renders INT
```

and it still round-trips through `get_params()` for serialization, because serialization asks a different question — not "what is this value" but "what is needed to rebuild this object" — and that answer is the constructor signature. `get_params()` is the single serialization path for all expressions and is not overridden on any of them.

Which spellings a *particular backend* renders is the backend's business, and it is checked in the backend's formatter: a dialect that does not write `CLOB` raises rather than silently emitting `TEXT` for a caller who asked for `CLOB`. The default spelling always renders — a backend may normalise it to its own word, never refuse it.

## Core Types

Core types are defined in `rhosocial.activerecord.backend.expression.types` and cover the SQL types shared by most databases. A concept with several spellings lists them; a concept with one has no `spelling` argument at all.

| Category | Type classes | Spellings |
|----------|--------------|-----------|
| Integer | `TinyIntType`, `SmallIntType`, `IntegerType`, `BigIntType` | `tinyint`/`int1`, `smallint`/`int2`, `integer`/`int`, `bigint`/`int8` |
| Numeric | `FloatType`, `RealType`, `DoubleType`, `DecimalType` | `double`/`double precision`, —, —, `decimal`/`numeric`/`dec` |
| String | `CharType`, `VarCharType`, `TextType` | `char`/`character`, `varchar`/`character varying`, `text`/`clob` |
| Boolean | `BooleanType` | `boolean`/`bool` |
| Binary | `BlobType`, `BinaryType`, `VarBinaryType` | `blob`/`bytea`, —, — |
| Enum | `EnumType` (values required) | — |
| Date/time | `DateType`, `TimeType`, `TimeTzType`, `DateTimeType`, `TimestampType`, `TimestampTzType`, `IntervalType` | — |
| JSON | `JsonType`, `JsonBType`, `XmlType` | — |
| UUID | `UUIDType` | — |
| Array | `ArrayType` | — |
| Custom | `CustomType` | — |

`TinyIntType`, `SmallIntType`, `IntegerType` and `BigIntType` each take `unsigned: bool`. Signed and unsigned are the *same class* — the range is what the parameter carries — because a linear inheritance chain cannot hold a (width × signedness) grid, and because a backend that has no unsigned integers widens rather than inventing a class.

`RealType`, `DoubleType` and `FloatType` are three classes on purpose. They have different ranges and different storage, and a schema diff must see the difference; `DateTimeType` and `TimestampType` likewise. `JsonType` and `XmlType` are separate because SQL/JSON and SQL/XML have different operations and different standards, and the backends that implement one do not reliably implement the other.

Core types can be instantiated without a dialect (deferred binding), but cannot render until one is bound.

## Backend-Specific Types

Each backend defines its own subtypes on top of the core types, **named with the backend name as a prefix**:

| Backend | Examples |
|---------|----------|
| SQLite | `SQLiteIntegerType(IntegerType)`, `SQLiteTextType(TextType)`, `SQLiteBlobType(BlobType)`, `SQLiteNumericType(DataType)` |
| MySQL | `MySQLIntType(IntegerType)`, `MySQLTinyIntType(TinyIntType)`, `MySQLEnumType(EnumType)`, `MySQLSetType(DataType)`, `MySQLGeometryType(DataType)` |
| PostgreSQL | `PostgresSerialType(IntegerType)`, `PostgresUUIDType(UUIDType)`, `PostgresXMLType(XmlType)`, `PostgresTSVectorType(DataType)`, `PostgresJsonPathType(DataType)` |

A backend type **derives from the core type of the concept it is**, whenever there is one — that is what makes `isinstance(col.data_type, IntegerType)` true for a PostgreSQL `SERIAL` column instead of forcing every caller to know each backend's private class list. It inherits `DataType` directly only when the concept is genuinely backend-exclusive, and then its docstring must say *why* there is no core concept.

Inheritance means **identity** — "this class *is* that SQL type". It is not used to group types into families: SQL's data-type categories (numeric, string, date/time) are membership, not subtyping, and nothing in this framework asks "is this numeric". The chain is linear: no multiple inheritance, no diamond edges.

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

### Integration with Model Fields

A plain Python annotation is not converted into a `DataType` by `DDLSourceMixin`. Without `UseSqlType`, `column_type()` returns `None`. Use `UseSqlType` for an explicit declaration; it preserves candidates in declaration order:

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLEnumType

class Product(ActiveRecord):
    size: Annotated[str, UseSqlType(MySQLEnumType(values=["S", "M", "L"]), TextType())]
```

`DDLSourceMixin` does not select candidates or perform backend fallback; those steps belong to the later dialect consumer.

### Introspection and Sync (parse_type)

When a dialect implements `parse_type(raw)` (the `DataTypeSupport` protocol), it can parse a raw type string returned by the database back into a `DataType` object for schema introspection and comparison. Dialects without this interface fall back to `CustomType(raw=raw)`. The former names `DDLTypeSupport` and `DDLTypeMixin` remain deprecated compatibility aliases for `DataTypeSupport` and `DataTypeMixin`.

A `parse_type` answer has to be **canonical**, and both halves of that are enforced by `tests/.../dummy2/test_type_spelling_parse.py`:

- **Coverage** — every entry of every core `SPELLINGS` tuple reaches a type. `CustomType` is the honest answer only for a name the framework has no concept for; used on `INT1`, `CHARACTER`, `DEC` or `BOOL` it would report a type the framework itself declares as a vendor-specific one, and write the raw text back.
- **One concept in, one class out** — all spellings of one concept reach the same class, and `character varying` (variable length) never reaches the fixed-length `CharType`. Two classes per synonym is what the `spelling` parameter exists to prevent, and a parser that conflated the two would report a schema change that is not there.

Which class is the dialect's answer, not the spelling's: a backend whose storage cannot tell two concepts apart may answer with the class that stands for that shared storage. SQLite is the case in core — `TINYINT` and `BIGINT` are one INTEGER-affinity cell, and reporting them apart would report a distinction the database does not make.

## Comparing Two Declared Types

`==` is the whole comparison. Two declarations are the same type when they are the same class with the same logical content, which is what a value object's `==` already means.

```python
if old_type != new_type:
    ...   # the schema really did change
```

There is no looser "are these equivalent" question to ask, and that is deliberate. The old `synonyms()`/`is_equivalent()` pair existed to paper over synonym *classes*, which is what this design removes: with synonyms expressed as a `spelling` parameter, two spellings are one class, so there is nothing left for an equivalence table to reconcile. Measured across 9 dialects × 11 synonym pairs (99 comparisons), `is_equivalent()` and `==` never disagreed — it was a mechanism with no remaining work to do.

One question `==` genuinely cannot answer is "does this array column store the same kind of thing as that one", where the answer should ignore how many axes the array has. That is a different question, it has its own name, and it is spelled `is_element_type_equivalent`:

```python
two_d.is_element_type_equivalent(one_d)   # True — both hold integers
```

## Related Documentation

- [Expression System Overview](README.md): generic / backend-specific design philosophy and serialization
- [Custom Backend](../custom_backend.md): dialect protocols, connection configuration, and backend integration