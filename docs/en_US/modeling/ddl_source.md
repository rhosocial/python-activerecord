# DDLSource: Collecting DDL Declarations from Models

`DDLSource` is the structural protocol through which ActiveRecord exposes DDL declarations. `DDLSourceMixin` is its default model implementation. The mixin collects DDL expressions and declarations from a model class and presents them through the protocol. It does not select a backend, generate SQL, create statement plans, or execute database operations.

> For the complete capability matrix and design boundaries, see [The ActiveRecord Definition](definition.md).

```python
from rhosocial.activerecord.base import DDLSource
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: int
    name: str

assert isinstance(User, DDLSource)
```

Both `ActiveRecord` and `AsyncActiveRecord` use the same `DDLSourceMixin`, so their DDL declaration interfaces stay equivalent.

## Boundary: Collect, Do Not Generate

Reading DDL declarations follows this path:

```text
model class definition
  → ActiveRecordMetaclass
  → DDLAnnotationHandler.handle()
  → DDLFieldMetadata in __table_ddl_fields__
  → DDLSourceMixin methods
  → caller receives dialect-independent declarations
```

Returned values may be `UseSqlType`, `ColumnConstraint`, `IndexDefinition`, `TableConstraint`, or backend-owned expression instances. They are normally unbound while they are being collected. Candidate selection, dialect binding, capability checks, and expression construction belong to an external DDL consumer and the backend dialect.

The current implementation does not infer a `DataType` from a plain Python annotation. Without `UseSqlType`, `column_data_type()` returns `None`. With `UseSqlType`, it returns the complete marker; ordered candidates are available in `marker.data_types`.

## How Declarations Enter the Collector

### Model-level declarations

| Declaration | Reading method | Notes |
|-------------|----------------|-------|
| `table_name()` (classmethod override) | `table_name()` | Declared by overriding the classmethod, which returns the table name. No dunder attribute is read; without an override the call raises `NotImplementedError`. |
| `__schema_name__` | `schema_name()` | Returned unchanged; `None` when unset. |
| `__primary_key__` | `primary_key_columns()` | A string becomes a one-item tuple; a tuple is returned unchanged. |
| `__primary_key__` | `is_composite_pk()` | Only a tuple denotes a composite primary key. |
| `__table_indexes__` | `table_indexes()` | Returns a shallow list copy; index objects are not copied. |
| `__table_constraints__` | `table_constraints()` | Returns a shallow list copy; a composite primary key is added when no matching explicit constraint exists. |

`table_options()`, `table_storage_options()`, `table_partition()`, `table_inherits()`, and `table_tablespace()` return `None` by default. A model may override them; the mixin returns the override unchanged.

### Field-level declarations

Field declarations use `typing.Annotated`. The collector reads both `Annotated` metadata and Pydantic `FieldInfo.metadata`.

| Marker | Collected result | Ordering rule |
|--------|------------------|---------------|
| `UseSqlType(*types)` | `column_data_type()` returns the `UseSqlType` marker | Candidates keep declaration order and are deduplicated; only the first marker is used. |
| `UseConstraint(...)` | `column_constraints()` returns `ColumnConstraint` objects | All markers are expanded in declaration order. |
| `UseIndex(...)` | `column_indexes()` returns newly built `IndexDefinition` objects | One definition is built per marker, using the physical column name. |
| `UseColumnAttributes(...)` | `column_attributes()` returns `ColumnAttribute` objects | Markers are expanded in order; each marker is internally deduplicated. |
| `UseComment(text)` | `column_comment()` returns the text | Only the first marker is used. |
| `UseGeneratedColumn(expr)` | `generated_column()` returns the expression or factory | Only the first marker is used; factories are not called during collection. |

`UseColumn` maps a Python field name to a physical database column name. It is not a DDL marker itself, but it affects `column_name()`, primary-key detection, and the column names produced by `UseIndex`.

### Backend annotation handlers

A backend-specific annotation must inherit from `DDLAnnotation` and have an explicitly registered handler. The core handler collects core markers; it does not guess how a backend annotation should be converted.

```python
from rhosocial.activerecord.base import DDLAnnotation, DDLAnnotationHandler

class BackendSetting(DDLAnnotation):
    def __init__(self, option):
        self.option = option

class BackendSettingHandler(DDLAnnotationHandler):
    annotation_types = (BackendSetting,)

    @classmethod
    def apply(cls, new_class, field_name, annotation, metadata):
        metadata.add_column_options(annotation.option)

class Report(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "reports"

    _feature_handlers = [BackendSettingHandler]

    id: int
```

When field-level DDL declarations are read, the mixin checks that every `DDLAnnotation` has been consumed. An unhandled annotation raises `TypeError`; it is never silently discarded.

## Protocol Reference

The table below describes the default `DDLSourceMixin` implementation. A custom source may provide the same structured interface.

| Method | Return value | Collection behavior |
|--------|---------------|---------------------|
| `table_name()` | `str` | Declared by the model's classmethod override; no dunder attribute is read. |
| `schema_name()` | `Optional[str]` | Reads `__schema_name__`. |
| `primary_key_columns()` | `Tuple[str, ...]` | Normalizes `__primary_key__`. |
| `is_composite_pk()` | `bool` | Tests whether the primary-key declaration is a tuple. |
| `ddl_field_names()` | `Tuple[str, ...]` | Returns `model_fields` in order, excluding `__derived_fields__`; validates annotations first. |
| `is_derived_field(field)` | `bool` | Checks membership in `__derived_fields__`. |
| `field_python_type(field)` | `type` | Reads field metadata and unwraps `Optional[T]` to `T`; unknown fields raise `KeyError`. |
| `field_is_optional(field)` | `bool` | True for `Optional[T]` or a default of `None`. |
| `column_name(field)` | `str` | Uses `ColumnNameMixin`; returns the physical name for `UseColumn`, otherwise the field name. |
| `column_data_type(field)` | `Optional[UseSqlType]` | Returns the first `UseSqlType` marker, or `None`; candidate selection does not happen here. |
| `column_type(field)` | `Optional[UseColumnType, class, or class sequence]` | Presents the column-type declaration as written — a `UseColumnType` marker (candidates included), a `ColumnBase` subclass, or a sequence — or `None`; dialect-free, so the backend that selects the class is the field accessor's concern. |
| `column_constraints(field)` | `Sequence[ColumnConstraint]` | Starts with explicit constraints, then applies primary-key and nullability rules. |
| `column_attributes(field)` | `Sequence[ColumnAttribute]` | Expands markers in order without dialect filtering. |
| `column_indexes(field)` | `Sequence[IndexDefinition]` | Builds one definition per `UseIndex` and substitutes the physical column name. |
| `column_comment(field)` | `Optional[str]` | Returns the first `UseComment` text. |
| `generated_column(field)` | `Optional[ColumnGeneratedConstraint or factory]` | Returns the first `UseGeneratedColumn` value without calling a factory. |
| `column_options(field)` | `None`, `ColumnOptions`, or a sequence | Returns values written by a handler to `DDLFieldMetadata.column_options`; one value is returned directly, multiple values as a list. |
| `table_options()` | `None`, expression, or sequence | `None` by default; an override is returned unchanged. |
| `table_storage_options()` | `None`, expression, or sequence | `None` by default; an override is returned unchanged. |
| `table_partition()` | `None`, `PartitionClause`, or sequence | `None` by default; an override is returned unchanged. |
| `table_indexes()` | `Sequence[IndexDefinition]` | Shallow copy of `__table_indexes__`. |
| `create_table_statement_classes()` | `None`, class, or class sequence | `None` by default; returns candidates without instantiating them. |
| `table_constraints()` | `Sequence[TableConstraint]` | Shallow copy of explicit constraints; a composite primary key is reused or completed according to the source rules. |
| `table_inherits()` | `Optional[List[str]]` | `None` by default; an override is returned unchanged. |
| `table_tablespace()` | `Optional[str]` | `None` by default; an override is returned unchanged. |

`column_type()` and `column_data_type()` are **dialect-free** declaration accessors: neither infers nor falls back. Selecting the column class a backend answers happens in the field accessor (`Model.c.<field>`), never in the source.

Every accessor that takes a field name refuses a name the model does not have with `KeyError`; `None` (or an empty collection) always means "the field exists and declares nothing". The batch accessors (`columns_*`) raise the same way when an explicitly named field is unknown. `column_name()` is a name mapping rather than a declaration reader, so it keeps returning the given name when no `UseColumn` applies.

### `column_constraints()` composition

The collector does not store one final constraint list at class creation time. It composes the list when the method is called:

1. Copy every `UseConstraint` object in declaration order.
2. Add a column-level `PRIMARY_KEY` for a single-column primary key.
3. Ensure `NOT_NULL` for single-column and composite primary-key members.
4. Remove an explicit `NULL` from a primary-key column.
5. Add `NOT_NULL` to a non-primary, non-Optional field that has no explicit nullability constraint.
6. Preserve other explicit constraints. If both `NULL` and `NOT_NULL` are declared, both remain and should be treated as a declaration requiring further validation.

`UseConstraint(PRIMARY_KEY)` is rejected at declaration time because `__primary_key__` is the single primary-key source. Composite primary-key members receive only `NOT_NULL` at column level; the table-level primary key is provided by `table_constraints()`. If a matching composite primary key is already declared, the mixin does not append another one. A mismatched explicit primary key raises `ValueError`.

### Batch helpers

These methods are convenience wrappers, not additional DDL source interfaces:

- `columns_name()`
- `columns_data_type()`
- `columns_constraints()`
- `columns_attributes()`
- `columns_indexes()`
- `columns_comment()`
- `columns_generated()`
- `columns_options()`

They return `{field_name: value}`. With no `fields` argument, they use the `model_fields` order. A supplied list is used as given, so dictionary order follows the request. Batch helpers do not filter backend candidates or perform capability checks.

## Mixin Extension Hooks

The following methods exist on `DDLSourceMixin` but are not part of the current `DDLSource` protocol:

- `drop_table_statement_classes()`
- `create_index_statement_classes()`
- `drop_index_statement_classes()`

Like `create_table_statement_classes()`, they return candidate classes and default to `None`. They remain mixin extension points so existing backends can provide their own statement classes. Adding them to the formal protocol should be a deliberate interface change, not an automatic consequence of runtime protocol checking.

## Backend Expression Integration

`UseSqlType` may contain several `DataType` candidates in priority order. The mechanism is a three-way split:

1. **Declaration** — the field carries the candidates as written; generic types and types owned by a backend may both appear.
2. **Collection** — `DDLSourceMixin` preserves every candidate and its order; it does not select, substitute, or drop one.
3. **Consumption** — a DDL consumer holding a concrete dialect selects the first candidate it can render for that backend ("first renderable wins").

The built-in SQLite backend shows the mechanism with generic types:

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType, VarCharType

identifier: Annotated[
    str,
    UseSqlType(TextType(), VarCharType(length=64)),
]
```

`column_data_type("identifier")` returns the whole marker with both candidates in order. When a SQLite DDL consumer renders the column, it picks the first candidate SQLite can render — here `TextType()` — while the source declaration stays untouched. A candidate a backend cannot render is skipped in favour of the next renderable one; the source never rewrites it.

> 💡 **AI Prompt**: "How does ActiveRecord cooperate with the built-in SQLite backend to turn a `UseSqlType` declaration with several candidates into one concrete column type, and why does the source keep all candidates instead of choosing one?"

A backend-specific `ColumnOptions` object is not a core `Use*` marker, so placing it on a field does not automatically collect it. A handler like `BackendSettingHandler` must write it to field metadata. The backend expression consumer can then use the option:

```python
option = SomeColumnOptions(...)
column_class = option.column_definition_class()
column = column_class(dialect, "name", data_type)
option.apply_to(column)
```

This code belongs to the backend expression consumer, not to `DDLSourceMixin`. Other backends are documented separately.

## Backend Differences at a Glance

The built-in SQLite backend renders the generic declarations `DDLSourceMixin` collects — generic `DataType`, `ColumnConstraint`, `IndexDefinition`, and `TableConstraint`. SQLite has a smaller capability set than ActiveRecord's declaration surface: when a declaration describes something SQLite does not support natively (for example certain table options, partitions, or storage settings), the source still preserves and returns it unchanged. That is a SQLite limitation, not a gap in ActiveRecord. Other backends provide capabilities beyond SQLite and are documented separately.

Backend tests should verify at least three things: the objects and order returned by the source, that backend-specific types/options are not rewritten early, and that collected values can be passed to an existing backend expression construction path. Collection tests do not need a live database; render assertions should use the backend dialect and minimal expressions separately.

## Reading Example

```python
from typing import Annotated, Optional

from rhosocial.activerecord.base import (
    CollationAttribute,
    UseColumn,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseIndex,
    UseSqlType,
)

from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.model import ActiveRecord


class Account(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "accounts"

    @classmethod
    def schema_name(cls):
        return "app"

    @classmethod
    def primary_key(cls):
        return "account_id"

    account_id: Annotated[int, UseColumn("id")]
    display_name: Annotated[
        str,
        UseSqlType(VarCharType(length=120)),
        UseIndex("idx_accounts_display_name"),
        UseColumnAttributes(CollationAttribute(name="und:ci")),
        UseComment("display name"),
    ]
    status: Annotated[
        str,
        UseConstraint(ColumnNotNullConstraint),
    ] = "active"
    note: Optional[str] = None


print(Account.table_name())
print(Account.ddl_field_names())
print(Account.column_name("account_id"))
print(Account.column_data_type("display_name").data_types)
print(Account.column_indexes("display_name"))
print(Account.column_comment("display_name"))
print(Account.table_indexes())
```

This code only reads declarations. `VarCharType`, `IndexDefinition`, and the comment do not become SQL merely because they were read. A caller can construct and render expressions after obtaining a dialect.

## Related Documentation

- [DDL Expressions](ddl.md): explicit expression construction and rendering
- [DDLSource Examples](ddl_source_examples.md): observed default, annotated, cross-backend, and incompatible examples
- [Data Types](../backend/expression/types.md): dialect binding and dispatch
- [Fields](fields.md): fields, column mapping, and declaration markers
