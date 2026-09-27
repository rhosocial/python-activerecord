# DDLSource: Collecting DDL Declarations from Models

`DDLSource` is the structural protocol through which ActiveRecord exposes DDL declarations. `DDLSourceMixin` is its default model implementation. The mixin collects DDL expressions and declarations from a model class and presents them through the protocol. It does not select a backend, generate SQL, create statement plans, or execute database operations.

```python
from rhosocial.activerecord.base import DDLSource
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"

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

The current implementation does not infer a `DataType` from a plain Python annotation. Without `UseSqlType`, `column_type()` returns `None`. With `UseSqlType`, it returns the complete marker; ordered candidates are available in `marker.data_types`.

## How Declarations Enter the Collector

### Model-level declarations

| Declaration | Reading method | Notes |
|-------------|----------------|-------|
| `__table_name__` | `table_name()` | Must be a string; missing or invalid values raise `ValueError`. |
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
| `UseSqlType(*types)` | `column_type()` returns the `UseSqlType` marker | Candidates keep declaration order and are deduplicated; only the first marker is used. |
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
    __table_name__ = "reports"
    _feature_handlers = [BackendSettingHandler]

    id: int
```

When field-level DDL declarations are read, the mixin checks that every `DDLAnnotation` has been consumed. An unhandled annotation raises `TypeError`; it is never silently discarded.

## Protocol Reference

The table below describes the default `DDLSourceMixin` implementation. A custom source may provide the same structured interface.

| Method | Return value | Collection behavior |
|--------|---------------|---------------------|
| `table_name()` | `str` | Reads and validates `__table_name__`. |
| `schema_name()` | `Optional[str]` | Reads `__schema_name__`. |
| `primary_key_columns()` | `Tuple[str, ...]` | Normalizes `__primary_key__`. |
| `is_composite_pk()` | `bool` | Tests whether the primary-key declaration is a tuple. |
| `ddl_field_names()` | `Tuple[str, ...]` | Returns `model_fields` in order, excluding `__derived_fields__`; validates annotations first. |
| `is_derived_field(field)` | `bool` | Checks membership in `__derived_fields__`. |
| `field_python_type(field)` | `type` | Reads field metadata and unwraps `Optional[T]` to `T`; unknown fields raise `KeyError`. |
| `field_is_optional(field)` | `bool` | True for `Optional[T]` or a default of `None`. |
| `column_name(field)` | `str` | Uses `ColumnNameMixin`; returns the physical name for `UseColumn`, otherwise the field name. |
| `column_type(field)` | `Optional[UseSqlType]` | Returns the first `UseSqlType` marker, or `None`; candidate selection does not happen here. |
| `column_constraints(field)` | `Sequence[ColumnConstraint]` | Starts with explicit constraints, then applies primary-key and nullability rules. |
| `column_attributes(field)` | `Sequence[ColumnAttribute]` | Expands markers in order without dialect filtering. |
| `column_indexes(field)` | `Sequence[IndexDefinition]` | Builds one definition per `UseIndex` and substitutes the physical column name. |
| `column_comment(field)` | `Optional[str]` | Returns the first `UseComment` text. |
| `generated_column(field)` | `Optional[GeneratedColumnExpression or factory]` | Returns the first `UseGeneratedColumn` value without calling a factory. |
| `column_options(field)` | `None`, `ColumnOptions`, or a sequence | Returns values written by a handler to `DDLFieldMetadata.column_options`; one value is returned directly, multiple values as a list. |
| `table_options()` | `None`, expression, or sequence | `None` by default; an override is returned unchanged. |
| `table_storage_options()` | `None`, expression, or sequence | `None` by default; an override is returned unchanged. |
| `table_partition()` | `None`, `PartitionClause`, or sequence | `None` by default; an override is returned unchanged. |
| `table_indexes()` | `Sequence[IndexDefinition]` | Shallow copy of `__table_indexes__`. |
| `create_table_statement_classes()` | `None`, class, or class sequence | `None` by default; returns candidates without instantiating them. |
| `table_constraints()` | `Sequence[TableConstraint]` | Shallow copy of explicit constraints; a composite primary key is reused or completed according to the source rules. |
| `table_inherits()` | `Optional[List[str]]` | `None` by default; an override is returned unchanged. |
| `table_tablespace()` | `Optional[str]` | `None` by default; an override is returned unchanged. |

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
- `columns_type()`
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

`UseSqlType` may contain generic and backend-specific types:

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresUUIDType

identifier: Annotated[
    str,
    UseSqlType(PostgresUUIDType(), TextType()),
]
```

`DDLSourceMixin` preserves both candidates and their order. Whether PostgreSQL accepts the first candidate, or another backend accepts the second, is decided later by the dialect consumer. The source does not substitute or fall back.

A backend-specific `ColumnOptions` object is not a core `Use*` marker, so placing it on a field does not automatically collect it. A handler like `BackendSettingHandler` must write it to field metadata. The backend expression consumer can then use the option:

```python
option = SomeColumnOptions(...)
column_class = option.column_definition_class()
column = column_class(dialect, "name", data_type)
option.apply_to(column)
```

This code belongs to the backend expression consumer, not to `DDLSourceMixin`.

## Backend Differences at a Glance

| Backend | Representative declarations/expressions | Collector notes |
|---------|-----------------------------------------|-----------------|
| SQLite | Generic `DataType`, `ColumnConstraint`, `IndexDefinition` | The source collects generic declarations; SQLite capability checks happen later. |
| MySQL | `MySQL*Type`, `MySQLColumnOptions`, `MySQLCreateTableOptions`, MySQL partition expressions | A `UseIndex` definition may later be consumed as an inline index; the source does not choose that path. |
| MariaDB | `MariaDB*Type`, `MariaDBColumnOptions`, `MariaDBCreateTableOptions`, MariaDB partition expressions | Syntax and capabilities are decided by the MariaDB dialect. |
| PostgreSQL | `Postgres*Type`, `PostgresColumnOptions`, `PostgresCreateTableOptions`, PostgreSQL partition expressions | Schema, tablespace, and backend options remain declarations; capability gates run later. |
| SQL Server | `SQLServer*Type`, `SQLServerColumnOptions`, `SQLServerCreateTableOptions`, SQL Server partition expressions | SQL Graph or other specialized create-table classes are selected by a consumer through extension hooks. |
| Oracle | `Oracle*Type`, `OracleColumnOptions`, Oracle partition expressions | Unsupported comments, partitions, or types fail in the Oracle dialect rather than being silently accepted. |
| Snowflake | `Snowflake*Type`, `SnowflakeCreateTableOptions`, Snowflake partition/clone expressions | VARIANT, OBJECT, ARRAY, and other types remain candidates; the source does not perform Snowflake-specific selection. |
| ClickHouse | `ClickHouse*Type`, `ClickHouseColumnOptions`, `ClickHouseIndexDefinition`, ClickHouse partition expressions | Unsupported UNIQUE or foreign-key capabilities fail in the ClickHouse dialect; declarations can still be presented. |
| BigQuery | Currently mainly generic `DataType`, constraints, and `CreateTableOptions` | The package currently has no automatically registered BigQuery-specific `ColumnOptions`; generic declarations can still be collected. |
| Firebird | `Firebird*Type`, `FirebirdColumnOptions`, `FirebirdCreateTableExpression`, Firebird partition/computed-column expressions | Computed columns, tablespaces, and specialized create-table classes are handled by the Firebird consumer. |

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
from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.model import ActiveRecord


class Account(ActiveRecord):
    __table_name__ = "accounts"
    __schema_name__ = "app"
    __primary_key__ = "account_id"

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
        UseConstraint(ColumnConstraintType.NOT_NULL),
    ] = "active"
    note: Optional[str] = None


print(Account.table_name())
print(Account.ddl_field_names())
print(Account.column_name("account_id"))
print(Account.column_type("display_name").data_types)
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
