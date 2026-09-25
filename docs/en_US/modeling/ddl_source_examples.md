# DDLSource Examples: Default, Annotated, Cross-Backend, and Incompatible Expressions

This companion to [`ddl_source.md`](ddl_source.md) shows how to read the declarations collected by `DDLSourceMixin` and how an external consumer binds those declarations to a dialect before rendering them.

These snippets are documentation examples, not modules to add under `src/` or `tests/`. The SQL shown below was produced by actual `to_sql()` probes against each backend dialect; no live database was used.

## Keep the Two Phases Separate

```text
model declaration
  → DDLSourceMixin collection
  → external consumer selects/binds candidates
  → ColumnDefinition / CreateTableExpression
  → dialect.to_sql()
```

`DDLSourceMixin` performs only the first phase. The helper below belongs to the external consumer. It copies a candidate before binding a dialect so that a shared model declaration is not mutated.

```python
from copy import copy

def bind(candidate, dialect):
    bound = copy(candidate)
    bound.dialect = dialect
    return bound


def render_column(dialect, marker, name="value", index=0):
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition

    return ColumnDefinition(
        dialect,
        name,
        bind(marker.data_types[index], dialect),
    ).to_sql()
```

## Scenario 1: Default Declarations

This model defines no additional DDL information.

```python
from typing import Optional

from rhosocial.activerecord.model import ActiveRecord


class PlainAccount(ActiveRecord):
    __table_name__ = "plain_accounts"

    id: int
    name: str
    note: Optional[str] = None
```

The source returns the model and primary-key metadata, but no `DataType`:

```python
PlainAccount.table_name()
# 'plain_accounts'

PlainAccount.schema_name()
# None

PlainAccount.primary_key_columns()
# ('id',)

PlainAccount.ddl_field_names()
# ('id', 'name', 'note')

PlainAccount.column_type("id")
# None

PlainAccount.column_options("id")
# None

PlainAccount.table_options()
# None

PlainAccount.table_storage_options()
# None

PlainAccount.table_partition()
# None

PlainAccount.table_indexes()
# []

PlainAccount.table_constraints()
# []

PlainAccount.column_constraints("id")
# ColumnConstraint(PRIMARY_KEY), ColumnConstraint(NOT_NULL)

PlainAccount.column_constraints("name")
# ColumnConstraint(NOT_NULL)

PlainAccount.column_constraints("note")
# []
```

The absence of `UseSqlType` means that `column_type()` is `None`. The source still composes the primary-key and non-null constraints for required fields.

A consumer cannot construct a typed column from `None`:

```python
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition

ColumnDefinition(dialect, "id", PlainAccount.column_type("id"))
# TypeError: data_type must be a DataType instance, got NoneType
```

The same source-level result applies to every backend:

| Backend | `column_type("name")` | Default table declarations | Consumer responsibility |
|---------|------------------------|----------------------------|-------------------------|
| SQLite | `None` | `None` / empty sequences | Choose an explicit core type such as `INTEGER` or `TEXT`. |
| MySQL | `None` | `None` / empty sequences | MySQL does not invent `INT` or `VARCHAR` for the source. |
| MariaDB | `None` | `None` / empty sequences | Same as MySQL. |
| PostgreSQL | `None` | `None` / empty sequences | Provide a PostgreSQL-renderable type. |
| SQL Server | `None` | `None` / empty sequences | Provide a SQL Server-renderable type. |
| Oracle | `None` | `None` / empty sequences | Provide an Oracle or core type. |
| Snowflake | `None` | `None` / empty sequences | `VARIANT` is not inferred automatically. |
| ClickHouse | `None` | `None` / empty sequences | Provide a ClickHouse or core type. |
| BigQuery | `None` | `None` / empty sequences | Use core types; BigQuery has no dedicated DDL `DataType` class today. |
| Firebird | `None` | `None` / empty sequences | Provide a Firebird or core type. |

## Scenario 2: Only Some Fields Have DDL Annotations

### 2.1 Core Expressions Only

```python
from typing import Annotated

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


class CoreDeclared(ActiveRecord):
    __table_name__ = "core_declared"

    id: Annotated[int, UseColumn("record_id")]
    name: Annotated[
        str,
        UseSqlType(VarCharType(length=64)),
        UseIndex("idx_core_declared_name", unique=True),
        UseColumnAttributes(CollationAttribute(name="und:ci")),
        UseComment("display name"),
    ]
    status: Annotated[
        str,
        UseConstraint(ColumnConstraintType.NOT_NULL),
    ] = "active"
```

The source preserves the declared objects and order:

```python
CoreDeclared.column_name("id")
# 'record_id'

CoreDeclared.column_type("name").data_types
# (VarCharType(length=64),)

CoreDeclared.column_indexes("name")[0].columns
# ['name']

CoreDeclared.column_comment("name")
# 'display name'

CoreDeclared.column_attributes("name")[0].name
# 'und:ci'

CoreDeclared.column_constraints("status")
# ColumnConstraint(NOT_NULL)
```

The same core type renders differently after the consumer binds each dialect:

| Backend | Rendered column fragment for `VarCharType(64)` |
|---------|-----------------------------------------------|
| SQLite | `"value" TEXT` |
| MySQL | `` `value` VARCHAR(64) `` |
| MariaDB | `` `value` VARCHAR(64) `` |
| PostgreSQL | `"value" VARCHAR(64)` |
| SQL Server | `[value] VARCHAR(64)` |
| Oracle | `"VALUE" VARCHAR2(64)` |
| Snowflake | `"value" VARCHAR(64)` |
| ClickHouse | `` `value` String `` |
| BigQuery | `` `value` STRING(64) `` |
| Firebird | `"VALUE" VARCHAR(64)` |

The source does not change the type. The difference is produced by the dialect formatter.

### 2.2 Backend-Specific Expressions

The following snippets show the source declaration and a minimal dialect-bound render for each backend.

#### SQLite

SQLite's dedicated types live in the core package:

```python
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteTextType

value: Annotated[str, UseSqlType(SQLiteTextType())]
```

Observed fragment: `"value" TEXT`.

#### MySQL

```python
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLIntType

value: Annotated[int, UseSqlType(MySQLIntType(unsigned=True))]
```

Observed fragment: `` `value` INT UNSIGNED ``.

MySQL column options can add character set, column format, storage, and invisibility:

```python
option = MySQLColumnOptions(
    character_set="utf8mb4",
    column_format=MySQLColumnFormat.FIXED,
    storage=MySQLColumnStorage.MEMORY,
    invisible=True,
)
column_class = option.column_definition_class()
column = column_class(dialect, "label", bind(VarCharType(length=32), dialect))
option.apply_to(column)
column.to_sql()
```

Observed fragment:

```sql
`label` VARCHAR(32) CHARACTER SET `utf8mb4` COLUMN_FORMAT FIXED STORAGE MEMORY INVISIBLE
```

#### MariaDB

```python
from rhosocial.activerecord.backend.impl.mariadb.expression.types import MariaDBIntType

value: Annotated[int, UseSqlType(MariaDBIntType(unsigned=True))]
```

Observed fragment: `` `value` INT UNSIGNED ``.

`MariaDBColumnOptions` has the same shape as the MySQL option, but it must be applied to a `MariaDBColumnDefinition`, not the core `ColumnDefinition`.

#### PostgreSQL

```python
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresUUIDType

identifier: Annotated[str, UseSqlType(PostgresUUIDType())]
```

Observed fragment: `"identifier" UUID`.

PostgreSQL column options can express compression, TOAST storage, and statistics:

```python
option = PostgresColumnOptions(
    compression="lz4",
    storage=PostgresColumnStorage.EXTERNAL,
    statistics=500,
)
column = option.column_definition_class()(
    dialect,
    "label",
    bind(VarCharType(length=32), dialect),
)
option.apply_to(column)
column.to_sql()
```

Observed fragment:

```sql
"label" VARCHAR(32) COMPRESSION lz4 STORAGE EXTERNAL STATISTICS 500
```

#### SQL Server

```python
from rhosocial.activerecord.backend.impl.sqlserver.expression.types import SQLServerNVarCharType

value: Annotated[str, UseSqlType(SQLServerNVarCharType(length=64))]
```

Observed fragment: `[value] NVARCHAR(64)`.

```python
option = SQLServerColumnOptions(sparse=True, rowguidcol=True)
column = option.column_definition_class()(
    dialect,
    "value",
    bind(VarCharType(length=64), dialect),
)
option.apply_to(column)
column.to_sql()
```

Observed fragment:

```sql
[value] VARCHAR(64) ROWGUIDCOL SPARSE
```

#### Oracle

```python
from rhosocial.activerecord.backend.impl.oracle.expression.types import OracleVarChar2Type

value: Annotated[str, UseSqlType(OracleVarChar2Type(length=64))]
```

Observed fragment: `"VALUE" VARCHAR2(64)`.

```python
option = OracleColumnOptions(invisible=True)
column = option.column_definition_class()(
    dialect,
    "value",
    bind(VarCharType(length=64), dialect),
)
option.apply_to(column)
column.to_sql()
```

Observed fragment: `"VALUE" VARCHAR2(64) INVISIBLE`.

#### Snowflake

```python
from rhosocial.activerecord.backend.impl.snowflake.expression.types import SnowflakeVariantType

payload: Annotated[dict, UseSqlType(SnowflakeVariantType())]
```

Observed fragment: `"payload" VARIANT`.

Snowflake has no dedicated `ColumnOptions` class in the current package. Its table options can be expressed with `SnowflakeCreateTableOptions`:

```python
options = SnowflakeCreateTableOptions(None, or_replace=True, transient=True)
```

The resulting statement begins with:

```sql
CREATE OR REPLACE TRANSIENT TABLE "docs_example" (...)
```

#### ClickHouse

```python
from rhosocial.activerecord.backend.impl.clickhouse.expression.types import ClickHouseStringType

payload: Annotated[str, UseSqlType(ClickHouseStringType())]
```

Observed fragment: `` `payload` String ``.

ClickHouse also supports `ClickHouseColumnOptions(codec=("ZSTD",))` and `StorageOptionsExpression`. An observed create-table fragment is:

```sql
CREATE OR REPLACE TABLE `docs_example` (
  `payload` String NOT NULL CODEC(ZSTD)
) ENGINE = MergeTree ORDER BY id
```

ClickHouse rejects ordinary UNIQUE indexes. That capability error is raised by the dialect/expression consumer, not by source collection.

#### BigQuery

BigQuery currently has no `Bigquery*Type`, `BigQueryColumnOptions`, or `BigQueryColumnDefinition` DDL expression classes. Use core expressions:

```python
from rhosocial.activerecord.backend.expression.types import IntegerType, JsonType

id_value: Annotated[int, UseSqlType(IntegerType())]
payload: Annotated[dict, UseSqlType(JsonType())]
```

Observed core fragments:

```sql
`id_value` INT64
`payload` JSON
```

BigQuery table comments use the core `CreateTableOptions` plus `TableCommentClause`; the dialect renders them as a table-level `OPTIONS(description=...)` clause.

#### Firebird

```python
from rhosocial.activerecord.backend.impl.firebird.expression.types import FirebirdVarCharType

value: Annotated[str, UseSqlType(FirebirdVarCharType(length=64))]
```

Observed fragment: `"VALUE" VARCHAR(64) CHARACTER SET UTF8`.

```python
option = FirebirdColumnOptions(
    character_set="UTF8",
    collation="UNICODE",
)
column = option.column_definition_class()(
    dialect,
    "value",
    bind(VarCharType(length=64), dialect),
)
option.apply_to(column)
column.to_sql()
```

Observed fragment:

```sql
"VALUE" VARCHAR(64) CHARACTER SET UTF8 COLLATE UNICODE
```

## Scenario 3: Cross-Backend Candidates in One Field

The important point of a cross-backend declaration is not automatic selection. It is to make the candidate order explicit and let the consumer select using the dialect's capability map.

```python
from typing import Annotated

from rhosocial.activerecord.backend.expression.types import TextType, VarCharType
from rhosocial.activerecord.backend.impl.clickhouse.expression.types import ClickHouseStringType
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresUUIDType
from rhosocial.activerecord.backend.impl.snowflake.expression.types import SnowflakeVariantType
from rhosocial.activerecord.base import UseSqlType

payload_marker = UseSqlType(
    PostgresUUIDType(),
    SnowflakeVariantType(),
    ClickHouseStringType(),
    VarCharType(length=64),
    TextType(),
)
payload: Annotated[str, payload_marker]
```

The source preserves the same ordered candidates regardless of the eventual dialect:

```python
[type(item).__name__ for item in payload_marker.data_types]
# ['PostgresUUIDType', 'SnowflakeVariantType', 'ClickHouseStringType',
#  'VarCharType', 'TextType']
```

A consumer can select explicitly:

```python
supported = dialect.supports_data_types()
selected = next(
    item for item in payload_marker.data_types if item.name in supported
)
selected = bind(selected, dialect)
```

The following results were observed for each backend. The "first supported candidate" is selected by the consumer; it is not selected by `DDLSourceMixin`.

| Backend | Example candidate order | First supported candidate | Rendered fragment |
|---------|--------------------------|---------------------------|-------------------|
| SQLite | `PostgresUUIDType, SQLiteTextType, VarCharType` | `SQLiteTextType` | `"value" TEXT` |
| MySQL | `PostgresUUIDType, MySQLLongTextType, VarCharType` | `MySQLLongTextType` | `` `value` LONGTEXT `` |
| MariaDB | `PostgresUUIDType, MariaDBLongTextType, VarCharType` | `MariaDBLongTextType` | `` `value` LONGTEXT `` |
| PostgreSQL | `MySQLIntType, PostgresUUIDType, VarCharType` | `PostgresUUIDType` | `"value" UUID` |
| SQL Server | `OracleVarChar2Type, SQLServerNVarCharType, VarCharType` | `SQLServerNVarCharType` | `[value] NVARCHAR(64)` |
| Oracle | `SQLServerNVarCharType, OracleVarChar2Type, VarCharType` | `OracleVarChar2Type` | `"VALUE" VARCHAR2(64)` |
| Snowflake | `ClickHouseStringType, SnowflakeVariantType, VarCharType` | `SnowflakeVariantType` | `"value" VARIANT` |
| ClickHouse | `SnowflakeVariantType, ClickHouseStringType, VarCharType` | `ClickHouseStringType` | `` `value` String `` |
| BigQuery | `SnowflakeVariantType, VarCharType, JsonType` | `VarCharType` | `` `value` STRING(64) `` |
| Firebird | `OracleVarChar2Type, FirebirdVarCharType, VarCharType` | `FirebirdVarCharType` | `"VALUE" VARCHAR(64) CHARACTER SET UTF8` |

Taking `marker.data_type` blindly means taking the first candidate. If that candidate belongs to another backend, the render enters the incompatible case below; source does not skip to the second candidate.

## Scenario 4: Only an Incompatible Backend Expression

This scenario intentionally contains no generic core candidate:

```python
class ForeignOnly(ActiveRecord):
    __table_name__ = "foreign_only"

    id: int
    value: Annotated[str, UseSqlType(ForeignType())]
```

The class definition and `column_type("value")` can succeed. The failure appears only when a consumer binds the candidate to the active dialect and renders it. The following table records the foreign type used in each probe:

| Active dialect | Only declared expression | Collection phase | Render phase |
|----------------|---------------------------|------------------|--------------|
| SQLite | `PostgresUUIDType()` | Returns `UseSqlType` | `TypeError`: no `format_data_type_postgres_uuid` |
| MySQL | `PostgresUUIDType()` | Returns `UseSqlType` | `TypeError`: MySQL does not support `postgres_uuid` |
| MariaDB | `PostgresUUIDType()` | Returns `UseSqlType` | `TypeError`: MariaDB does not support `postgres_uuid` |
| PostgreSQL | `MySQLIntType(unsigned=True)` | Returns `UseSqlType` | `TypeError`: PostgreSQL does not support `mysql_int` |
| SQL Server | `OracleVarChar2Type(length=64)` | Returns `UseSqlType` | `TypeError`: SQL Server does not support `oracle_varchar2` |
| Oracle | `SQLServerNVarCharType(length=64)` | Returns `UseSqlType` | `TypeError`: Oracle does not support `sqlserver_nvarchar` |
| Snowflake | `ClickHouseStringType()` | Returns `UseSqlType` | `TypeError`: Snowflake does not support `clickhouse_string` |
| ClickHouse | `SnowflakeVariantType()` | Returns `UseSqlType` | `TypeError`: ClickHouse does not support `snowflake_variant` |
| BigQuery | `SnowflakeVariantType()` | Returns `UseSqlType` | `TypeError`: BigQuery does not support `snowflake_variant` |
| Firebird | `OracleVarChar2Type(length=64)` | Returns `UseSqlType` | `TypeError`: Firebird does not support `oracle_varchar2` |

A typical error is:

```text
SQLServerDialect does not support the generic type 'oracle_varchar2'
(no format_data_type_oracle_varchar2). Use a type this backend supports.
```

This demonstrates three rules:

1. `DDLSourceMixin` does not validate a backend expression against the active dialect at model import time.
2. `supports_data_types()` and `suggested_data_types()` are capability queries, not automatic substitution mechanisms.
3. If a model has only an incompatible backend expression, the consumer must handle `TypeError`; the source will not silently fall back to `VARCHAR`, `TEXT`, or another core type.

## Backend-Specific Options

`ColumnOptions` is not a `DDLAnnotation`. To have `column_options()` return a backend option from a field annotation, wrap it in a custom `DDLAnnotation` and register a handler. For direct expression construction, instantiate the backend option directly.

| Backend | Option or table expression | Observed behavior |
|---------|----------------------------|-------------------|
| SQLite | Core `CreateTableOptions` | Core options are rendered by the SQLite dialect. |
| MySQL | `MySQLCreateTableOptions(engine="InnoDB", charset="utf8mb4")` | Produces MySQL `ENGINE` and `DEFAULT CHARSET` table options. |
| MariaDB | `MariaDBCreateTableOptions` | Produces options matched to the MariaDB dialect. |
| PostgreSQL | `PostgresCreateTableOptions(unlogged=True)` | Produces `CREATE UNLOGGED TABLE`; version capability is checked by PostgreSQL. |
| SQL Server | `SQLServerCreateTableOptions(memory_optimized=True)` and `SQLServerCreateTableExpression` | Produces `WITH (MEMORY_OPTIMIZED = ON)`; requires SQL Server 2014+. |
| Oracle | Core `CreateTableOptions` and `tablespace="TS_DATA"` | Oracle's table formatter handles tablespaces; generic `StorageOptionsExpression` fails fast in the Oracle create-table path. |
| Snowflake | `SnowflakeCreateTableOptions(transient=True)` | Produces `CREATE OR REPLACE TRANSIENT TABLE`. |
| ClickHouse | `ClickHouseColumnOptions` and `StorageOptionsExpression` | Produces `CODEC(...)` and `ENGINE = ...` clauses. |
| BigQuery | Core `CreateTableOptions` plus `TableCommentClause` | Produces table-level `OPTIONS(description=...)`; there is no BigQuery-specific `ColumnOptions` today. |
| Firebird | `FirebirdCreateTableExpression` and `FirebirdColumnOptions` | Produces `CREATE GLOBAL TEMPORARY TABLE` and `CHARACTER SET` clauses. |

Applying one backend's `ColumnOptions` to another backend's core `ColumnDefinition` normally raises `TypeError`. If it is applied to a different backend's own column definition class, unknown backend fields may be silently ignored by that formatter. Keep the option class, column definition class, and dialect from the same backend.

## Conclusions

- Without DDL annotations, the source still exposes table, key, field, and composed constraint metadata, but it does not create a `DataType`.
- Core and backend expressions are both candidates in `UseSqlType`; the source preserves order and does not select.
- Cross-backend candidates must be selected explicitly with the dialect capability map.
- With only an incompatible backend expression, model declaration and source reading can succeed; binding/rendering raises `TypeError`.
- Backend options are additional expression/dialect capabilities, not automatically inferred source results.

## Related Documentation

- [DDLSource Interface Reference](ddl_source.md)
- [DDL Expressions](ddl.md)
- [Data Types and Dialect Dispatch](../backend/expression/types.md)
