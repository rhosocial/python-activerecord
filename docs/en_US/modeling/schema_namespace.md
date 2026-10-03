# docs/en_US/modeling/schema_namespace.md
# Schema Namespaces

> How to bind a model to a database schema, and what decides whether the
> schema shows up in the SQL that gets executed.

Schemas are the closest thing most databases have to a namespace. PostgreSQL,
SQL Server and Oracle treat them as a first-class part of an object's name;
MySQL/MariaDB call the same thing a "database"; BigQuery calls it a "dataset";
Snowflake nests it inside a database. This guide covers declaring a schema on a
model, naming a schema for each DDL object separately, and what a declaration
does *not* cover.

Every SQL fragment below was produced by running the expression layer on the
`fix/schema-name-propagation-gaps` branch. Qualified names are rendered by
`rhosocial.activerecord.backend.impl.dummy.backend.DummyDialect`, the core
package's own dialect, whose `supports_schema()` is `True`. The quoting is
PostgreSQL's; see [§11](#11-sqlite-and-why-this-guide-is-written-in-postgresqls-dialect)
for why the reference spelling is that dialect's, and for what the built-in
SQLite backend does instead.

## 1. Declaring a schema

A model declares its schema with the `__schema_name__` class attribute. It is
optional and defaults to `None`, which means "resolve through the connection's
default".

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"          # -> "app"."users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    name: str
```

`schema_name()` is the only reader of that attribute, and it may be overridden
for dynamic namespaces. Four patterns, in rough order of how often they fit:

```python
# 1) Static — the common case. Every statement for this model is qualified.
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"

# 2) Template base — share one namespace across several models.
class AppModel(ActiveRecord):
    __schema_name__ = "app"

class User(AppModel):
    __table_name__ = "users"

class Order(AppModel):
    __table_name__ = "orders"

# 3) Dynamic — multi-tenancy. One class per namespace, chosen at call time.
class Order(ActiveRecord):
    __table_name__ = "orders"

    @classmethod
    def schema_name(cls) -> str:
        return f"tenant_{current_tenant_id()}"

# 4) Configuration-driven.
class User(ActiveRecord):
    __schema_name__ = settings.db_schema
```

`__table_name__` and `__schema_name__` are separate on purpose. Do **not** fold
them together:

```python
__table_name__ = "app.users"   # WRONG
```

The identifier is quoted as a single unit, so this renders `FROM "app.users"` —
one identifier containing a dot, not a qualified reference. PostgreSQL then
reports `relation "app.users" does not exist`. Declare `__schema_name__`
instead.

## 2. How the namespace reaches the SQL

There is one decision chain, and no configuration knob in it:

```
__schema_name__  ->  schema_name()  ->  TableExpression.schema_name
                                          / Column.schema_name
                                      ->  format_table() / format_column()
```

You supply two inputs; everything else follows:

1. whether `schema_name()` returns a string or `None`;
2. whether a table alias is in effect.

The rendered forms:

| Range in `FROM` | Column reference | PostgreSQL |
|---|---|---|
| `"users"` (no schema) | `"users"."id"` | valid |
| `"ar_crm"."users"` | `"ar_crm"."users"."id"` | valid |
| `"ar_crm"."users"` | `"users"."id"` | valid |
| `"ar_crm"."users" AS "u"` | `"u"."id"` | valid |
| `"ar_crm"."users" AS "u"` | `"ar_crm"."users"."id"` | **error** |
| `"ar_crm"."users" AS "u"` | `"users"."id"` | **error** |

Read that as: an **unaliased** range may be referenced either way, while an
**aliased** range must be referenced by its alias alone. "Always two-part" is
therefore not a self-consistent rule — it is wrong exactly when an alias is
present.

The suppression for aliased ranges happens when the column expression is
*constructed*, not when it is rendered: `FieldProxy` sets `schema_name` to
`None` as soon as a table alias is in effect, which is why

```python
Order.query().select(Order.c.with_table_alias("o").id).to_sql()[0]
# SELECT "o"."id" FROM "shop"."orders"
```

drops the schema from the column while keeping it on the range. Building a
`Column` by hand bypasses that guard, so a hand-built
`Column(dialect, "id", table="u", schema_name="ar_crm")` renders
`"ar_crm"."u"."id"`, the three-part form PostgreSQL rejects.

### Three things you do not control

* **`search_path`.** `PostgresConnectionConfig.search_path` is appended to the
  connection parameters handed to psycopg when the connection is opened
  (`python-activerecord-postgres`, `backend/impl/postgres/config.py`), so it is
  fixed for the life of the connection and cannot be changed per query or per
  transaction. Unqualified names resolve through it.
* **The connection's `default_schema` setting.** It does not reach the server —
  it is not among the parameters `PostgresConnectionConfig` passes — and it
  never affects generated SQL. It is read in one place only: the PostgreSQL
  introspector's fallback for which schema to inspect when no schema is given,
  ahead of `search_path`'s first entry and `"public"`.
* **The alias.** Once set, the schema is dropped from column references by
  design.

## 3. When validation happens

An expression collects its parameters at construction and does not check them.
The namespace is judged while the statement is rendered, by
`SchemaMixin.validate_schema_name()`, which every formatter that renders a
qualified name reaches through `format_table()` or `format_column()`
(`backend/dialect/mixins/ddl_schema.py`).

Three things are refused there, in increasing order of how long they would
otherwise go unnoticed:

* a value that is neither `None` nor a string;
* an empty or blank string, which `format_table()` treats as "no schema", so a
  caller who asked for `app.users` would receive `users`;
* any value on a dialect whose `supports_schema()` is `False`, which would
  render into SQL the server rejects.

```python
TableExpression(dialect, "users", schema_name="")     # constructs fine
expr.to_sql()
# ValueError: TableExpression.schema_name must be a non-empty string;
#             use None for an unqualified reference
```

A model reaches the same check through its declared namespace:

```python
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = ""            # a mistake, not a way to spell "public"

User.build_table_reference(dialect).to_sql()
# ValueError: TableExpression.schema_name must be a non-empty string;
#             use None for an unqualified reference
```

A fourth case is decided before validation. A dialect that does not implement
the `SchemaSupport` protocol has no namespaces to talk about, so `format_table()`
neither validates nor qualifies: the namespace it carries is not that dialect's
business and is ignored. Only a dialect that implements `SchemaSupport` is held
to the value. Every backend in the matrix in [§10](#10-backend-support-matrix)
implements it.

Why refuse an empty string rather than treat it as absent, when the renderer
already treats a falsy schema as absent? Because that fallback is the problem. A
caller who asked for `app.users` would get `users`, with no error and no warning,
and the statement still runs — against the wrong table on any connection whose
`search_path` contains `app`. An empty string is nearly always how a namespace
gets lost in the first place: an f-string that came out blank, a
`config.get(...) or ""`, a missing environment variable. It is also the case
where the caller is least able to tell that the namespace went missing.

## 4. `TableExpression` carries every qualified name

One expression represents "a named object, optionally in a namespace", and it is
the only one. `TableExpression` plays two roles:

* a **range in a `FROM` clause** — a table or a view;
* a **named DDL object** — an index, a sequence, a type, a function.

```python
TableExpression(
    dialect,
    name: str,
    schema_name: Optional[str] = None,
    alias: Optional[str] = None,
    temporal_options: Optional[Dict[str, Any]] = None,
    name_need_quote: bool = True,
    alias_need_quote: bool = True,
    schema_need_quote: bool = True,
)
```

`alias` and `temporal_options` only carry meaning for a range in a `FROM`
clause. Elsewhere they stay at their defaults, which is why the same expression
serves both roles.

Two rendering paths reach this one carrier, and which one a statement uses
depends on what the statement names:

| Statement group | How the namespace is supplied |
|---|---|
| `ALTER TABLE`, `TRUNCATE`, `UPDATE`, `MERGE` | `table` takes a `TableExpression` |
| `CREATE` / `DROP` INDEX, full-text index | `table` takes a `TableExpression`; `schema_name` names the index |
| `CREATE` / `DROP` TRIGGER | `table` and `function_name` take `TableExpression`s; `schema_name` names the trigger |
| `CREATE` / `DROP` TABLE | `table` takes a `TableExpression` |
| VIEW, TYPE, SEQUENCE, FUNCTION, DOMAIN | a plain `schema_name` string; the formatter wraps the object name in a `TableExpression` |

### Bare strings: refused in some places, accepted in others

The `table` parameter is not uniform across statements, so the safe rule is to
pass a `TableExpression` everywhere. What happens today if you do not:

| Parameter | Bare `str` |
|---|---|
| `AlterTableExpression.table` | `TypeError` at construction |
| `TruncateExpression.table` | `TypeError` at construction |
| `UpdateExpression.table` | `TypeError` at construction |
| `MergeExpression.target_table` | `TypeError` at construction |
| `CreateTableExpression.table`, `DropTableExpression.table` | accepted, wrapped as an unqualified `TableExpression` |
| `CreateIndexExpression.table`, `DropIndexExpression.table` | accepted, wrapped as an unqualified `TableExpression` |
| `CreateFulltextIndexExpression.table`, `DropFulltextIndexExpression.table` | accepted, wrapped as an unqualified `TableExpression` |
| `CreateTriggerExpression.table` / `.function_name`, `DropTriggerExpression.table` | not checked; surfaces as an `AttributeError` while rendering |

The accepted case is the one worth knowing about, because the namespace it
produces is not the one a caller may expect:

```python
CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table="users",             # a bare string
    columns=["email"],
    schema_name="app",
).to_sql()[0]
# CREATE INDEX "app"."idx_users_email" ON "users" ("email")
```

`schema_name` qualifies the index, and the table stays in the connection's
default namespace. Pass `table=TableExpression(dialect, "users", schema_name="app")`
to place both.

## 5. DDL: each object chooses its own namespace

> **`__schema_name__` selects the read/write namespace.** Expressions assembled
> by hand do not read it — see [§6](#6-model-level-ddl-factories) for the
> factories that do.

| Statement | How to qualify it |
|---|---|
| `SELECT` / `INSERT` / `UPDATE` / `DELETE` | automatic, from the model's `__schema_name__` |
| `CREATE TABLE` / `DROP TABLE` | `table=TableExpression(dialect, "users", schema_name="app")` |
| `ALTER TABLE` | `table=TableExpression(dialect, "users", schema_name="app")` |
| `TRUNCATE` | `table=TableExpression(dialect, "users", schema_name="app")` |
| `CREATE` / `ALTER` / `DROP` / `REFRESH` VIEW, incl. materialized | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` TYPE | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` SEQUENCE | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` DOMAIN | `schema_name="app"` |
| `CREATE` / `DROP` FUNCTION | `schema_name="app"` |
| `CREATE INDEX` / `DROP INDEX`, incl. full-text | `schema_name="app"` for the index **and** `table=TableExpression(...)` for the table |
| `CREATE` / `DROP` TRIGGER | `schema_name="app"` for the trigger, plus `table=` and `function_name=` |

Every `schema_name` defaults to `None`, which means unqualified — the same
default as everywhere else in the expression layer.

### Indexes: the index and the table are placed independently

For an index, one statement names two objects, so it takes two namespaces.
`schema_name` qualifies **the index name**; `table` qualifies **the table**.

```python
# Both in "app".
CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table=TableExpression(dialect, "users", schema_name="app"),
    columns=["email"],
    schema_name="app",
).to_sql()[0]
# CREATE INDEX "app"."idx_users_email" ON "app"."users" ("email")

# Index in "app", table in "sales".
CreateIndexExpression(
    dialect,
    index_name="idx_shared",
    table=TableExpression(dialect, "orders", schema_name="sales"),
    columns=["user_id"],
    schema_name="app",
).to_sql()[0]
# CREATE INDEX "app"."idx_shared" ON "sales"."orders" ("user_id")

# Index name left bare, table qualified.
CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table=TableExpression(dialect, "users", schema_name="app"),
    columns=["email"],
).to_sql()[0]
# CREATE INDEX "idx_users_email" ON "app"."users" ("email")
```

`DropIndexExpression` splits the same way:

```python
DropIndexExpression(
    dialect,
    index_name="idx_users_email",
    table=TableExpression(dialect, "users", schema_name="app"),
    schema_name="app",
).to_sql()[0]
# DROP INDEX "app"."idx_users_email" ON "app"."users"
```

### Triggers: three namespaces, chosen separately

A trigger names three objects: the trigger, the table it is attached to, and
the function its body calls. Each carries its own.

```python
CreateTriggerExpression(
    dialect,
    trigger_name="trg_users_audit",
    table=TableExpression(dialect, "users", schema_name="app"),
    timing=TriggerTiming.AFTER,
    events=[TriggerEvent.UPDATE],
    function_name=TableExpression(dialect, "audit_row", schema_name="util"),
    schema_name="monitor",
).to_sql()[0]
# CREATE TRIGGER "monitor"."trg_users_audit" AFTER UPDATE ON "app"."users"
#   FOR EACH ROW EXECUTE "util"."audit_row"
```

`DropTriggerExpression` takes the trigger's `schema_name` and the table's own:

```python
DropTriggerExpression(
    dialect,
    trigger_name="trg_users_audit",
    table=TableExpression(dialect, "users", schema_name="app"),
    schema_name="app",
).to_sql()[0]
# DROP TRIGGER "app"."trg_users_audit" ON "app"."users"
```

### Statements that still take one `schema_name`

A view, a type, a sequence, a function and a domain each name one object, so
they take a single `schema_name` string and the formatter wraps the name:

```python
CreateSequenceExpression(dialect, sequence_name="order_seq", schema_name="app").to_sql()[0]
# CREATE SEQUENCE "app"."order_seq" NO CYCLE

CreateFunctionExpression(dialect, function_name="audit_row", schema_name="util").to_sql()[0]
# CREATE FUNCTION "util"."audit_row" () LANGUAGE plpgsql
```

### MySQL and MariaDB: an index name cannot be qualified

On these two backends an index belongs to the namespace of the table that owns
it, and their grammar rejects a qualified index name. Both dialects answer
`False` to `supports_index_schema_qualification()` and refuse the request while
rendering, instead of emitting SQL the server would reject:

```python
CreateIndexExpression(
    mariadb_dialect,
    index_name="idx_users_email",
    table=TableExpression(mariadb_dialect, "users", schema_name="app"),
    columns=["email"],
    schema_name="app",
).to_sql()
# UnsupportedFeatureError: 'MariaDB' dialect does not support a
# namespace-qualified index name. … Qualify the table instead by passing it as
# a TableExpression with schema_name set.
```

Placing the namespace on the table is the correct form there, and it is what
renders:

```python
CreateIndexExpression(
    mariadb_dialect,
    index_name="idx_users_email",
    table=TableExpression(mariadb_dialect, "users", schema_name="app"),
    columns=["email"],
).to_sql()[0]
# CREATE INDEX `idx_users_email` ON `app`.`users` (`email`)
```

The check applies to `CREATE INDEX`, `DROP INDEX`, `CREATE FULLTEXT INDEX` and
`DROP FULLTEXT INDEX`. Every other backend inherits the default, `True`.

## 6. Model-level DDL factories

`__schema_name__` originally covered the query layer only, so migration DDL had
to name its namespace by hand at every call site. Seven class methods on the
model build the DDL statements for that model inside its own namespace:

```python
Model.build_table_reference(dialect, alias=None)
Model.build_create_table_statement(dialect, columns, *, indexes=None,
                                   table_constraints=None, temporary=False,
                                   if_not_exists=False)
Model.build_drop_table_statement(dialect, if_exists=False)
Model.build_truncate_statement(dialect, restart_identity=False, cascade=False)
Model.build_alter_table_statement(dialect, actions)
Model.build_create_index_statement(dialect, index_name, columns, *,
                                    index_schema_name=None, **options)
Model.build_drop_index_statement(dialect, index_name, *,
                                  index_schema_name=None, if_exists=False, **options)
```

Every one of them goes through `build_table_reference()`, so a migration cannot
qualify one statement in the model's namespace and the next in another:

```python
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"

User.build_table_reference(dialect).to_sql()[0]
# "app"."users"
User.build_table_reference(dialect, alias="u").to_sql()[0]
# "app"."users" AS "u"

User.build_create_table_statement(dialect, [
    ColumnDefinition(dialect, "id", IntegerType(dialect)),
    ColumnDefinition(dialect, "name", TextType(dialect)),
]).to_sql()[0]
# CREATE TABLE "app"."users" ("id" INTEGER, "name" TEXT)

User.build_drop_table_statement(dialect, if_exists=True).to_sql()[0]
# DROP TABLE IF EXISTS "app"."users"

User.build_truncate_statement(dialect, restart_identity=True).to_sql()[0]
# TRUNCATE TABLE "app"."users" RESTART IDENTITY

User.build_alter_table_statement(dialect, [
    AddColumn(dialect, ColumnDefinition(dialect, "email", TextType(dialect))),
]).to_sql()[0]
# ALTER TABLE "app"."users" ADD COLUMN "email" TEXT
```

The two index factories default `index_schema_name` to the model's namespace and
accept an explicit namespace for an index placed elsewhere:

```python
User.build_create_index_statement(dialect, "idx_users_email", ["email"]).to_sql()[0]
# CREATE INDEX "app"."idx_users_email" ON "app"."users" ("email")

User.build_create_index_statement(
    dialect, "idx_users_email", ["email"], index_schema_name="ops",
).to_sql()[0]
# CREATE INDEX "ops"."idx_users_email" ON "app"."users" ("email")

User.build_drop_index_statement(
    dialect, "idx_users_email", index_schema_name="ops", if_exists=True,
).to_sql()[0]
# DROP INDEX IF EXISTS "ops"."idx_users_email" ON "app"."users"
```

A model with no `__schema_name__` builds the same statements unqualified, and
`index_schema_name` still moves an index on its own:

```python
Plain.__schema_name__ is None
# True

Plain.build_table_reference(dialect).to_sql()[0]
# "plain"

Plain.build_create_index_statement(
    dialect, "idx_plain_id", ["id"], index_schema_name="ops",
).to_sql()[0]
# CREATE INDEX "ops"."idx_plain_id" ON "plain" ("id")
```

**A statement you assemble by hand does not pick up `__schema_name__`.** Pass
`TableExpression(dialect, name, schema_name=...)` yourself, or use the factories
above. That is the whole difference between the two forms: the factories read
`schema_name()` for you, and nothing else does.

## 7. What each kind of query does with the namespace

`__schema_name__` is read in one place — `schema_name()` — and every query the
model builds passes it down. So the namespace follows the model without each
query type having to know about it. What differs is the *shape* of the SQL.

The examples below were produced with `DummyDialect` against two models,
`Order` in `"shop"` and `Customer` in `"crm"`.

### ActiveQuery — DML carries the namespace

A model's `query()` qualifies every range it builds, which covers `SELECT`,
`INSERT`, `UPDATE` and `DELETE` alike:

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT "shop"."orders"."id" FROM "shop"."orders"

Order.query().where(Order.c.total > 100).to_sql()
# SELECT * FROM "shop"."orders"
#   WHERE "shop"."orders"."total" > ?        -- params (100,)
```

The column is three-part: the range is unaliased, so the namespace qualifies it
all the way through. Once an alias is in play the namespace is dropped from the
column, because the alias already identifies the range:

```python
Order.query().select(Order.c.with_table_alias("o").id).to_sql()[0]
# SELECT "o"."id" FROM "shop"."orders"
```

This is not a simplification. A namespace-qualified reference to an aliased
range is a syntax error on PostgreSQL and SQL Server.

`update_all()` and `delete_all()` reach the same namespace through
`UpdateOptions` and `DeleteOptions`, passing the model's `table_name()` and
`schema_name()` (`query/active_query.py`). The DML options objects — `InsertOptions`,
`UpdateOptions`, `DeleteOptions` — are where a table is still named by string:
`UpdateOptions(table="orders", schema_name="shop", …)`, which the backend
converts into an `UpdateExpression` with the namespace attached
(`backend/base/operations.py`).

### Joins — each side qualifies its own range

No additional configuration is required. Each model contributes its own
namespace, so a single statement may span two:

```python
Order.query().join(Customer, on=Order.c.id == Customer.c.id).to_sql()[0]
# SELECT * FROM "shop"."orders" JOIN "crm"."customers"
#   ON "shop"."orders"."id" = "crm"."customers"."id"
```

### SetOperationQuery — no namespace of its own

`UNION`, `INTERSECT` and `EXCEPT` combine queries rather than naming an object,
so there is nothing for them to qualify. Each branch retains its own:

```python
Order.query().union(Customer.query()).to_sql()[0]
# SELECT * FROM "shop"."orders" UNION SELECT * FROM "crm"."customers"
```

One statement spanning two namespaces is legal on PostgreSQL, so a `UNION` over
two namespace-bound models needs no special handling.

### CTEQuery — the CTE name is not in a namespace

A CTE is named for the rest of the query, not for the database, so its name is
never qualified — qualifying it would look for a table with that name in some
namespace and fail:

```python
(CTEQuery(backend)
    .with_cte("recent_orders", Order.query().select(Order.c.id))
    .from_cte("recent_orders")
    .to_sql()[0])
# WITH "recent_orders" AS (SELECT "shop"."orders"."id" FROM "shop"."orders")
# SELECT * FROM "recent_orders"
```

The inner `SELECT` still carries the model's namespace; only the CTE's own name
is bare.

### Soft delete — restore carries it too

`restore()` builds an `UpdateOptions` from the model's `table_name()` and
`schema_name()` (`field/soft_delete.py`), so it qualifies the same way `delete()`
does. A restore that dropped the namespace would clear `deleted_at` on the
same-named table in the default namespace and leave the intended row
soft-deleted — a cross-namespace write that no read-only assertion would catch.

## 8. Qualifier binding

`Model.c.field` snapshots `table_name()` and `schema_name()` **when the
expression is built**, not when it is executed:

```python
condition = Order.c.total > 100     # bound to tenant_a
Order.__schema_name__ = "tenant_b"
condition.to_sql()[0]
# "tenant_a"."orders"."total" > ?        -- unchanged
condition = Order.c.total > 100     # rebuild to pick up the new namespace
condition.to_sql()[0]
# "tenant_b"."orders"."total" > ?
```

The same applies to `table_name()`. For tenant-style switching, rebuild
conditions after switching, or use one model class per namespace.

## 9. Guard clauses are refused, not dropped

An existence or cascade guard that a backend does not have is refused while the
statement is rendered, rather than discarded so the statement runs without it:

| Statement | Backend | Guard |
|---|---|---|
| `DROP TABLE IF EXISTS` | Oracle | `supports_if_exists_table()` is `False`; the flag raises `UnsupportedFeatureError` |
| `CREATE SCHEMA IF NOT EXISTS` | SQL Server | `supports_schema_if_not_exists()` is `False`; the flag raises `UnsupportedFeatureError` |
| `DROP SCHEMA IF EXISTS` | SQL Server | `supports_schema_if_exists()` is `False`; the flag raises `UnsupportedFeatureError` |
| `DROP SCHEMA CASCADE` | SQL Server | `supports_schema_cascade()` is `False`; the flag raises `UnsupportedFeatureError` |

```python
DropTableExpression(
    oracle_dialect, TableExpression(oracle_dialect, "users", schema_name="app"),
    if_exists=True,
).to_sql()
# UnsupportedFeatureError: 'Oracle' dialect does not support DROP TABLE IF
# EXISTS. … Drop the flag, or guard the call yourself.

DropTableExpression(
    oracle_dialect, TableExpression(oracle_dialect, "users", schema_name="app"),
).to_sql()[0]
# DROP TABLE "APP"."USERS"
```

Dropping the flag is a decision about semantics, not about SQL: without
`IF EXISTS`, dropping a table that is already gone is an error. Guard the call
in application code, or check the catalog first, and the statement stays
correct on every backend.

## 10. Backend support matrix

What a `schema_name` means is defined by each backend. They do not agree on what
it names. Everything in this guide that shows `"app"."users"` is the PostgreSQL /
SQL Server / Oracle spelling.

| Backend | `supports_schema()` | `supports_index_schema_qualification()` | What `schema_name` names | Renders as |
|---|---|---|---|---|
| PostgreSQL | yes | yes | a schema inside the current database | `"app"."users"` |
| SQL Server | yes | yes | a schema inside the current database | `[app].[users]` |
| Oracle | yes | yes | a schema, which is the owning user | `"APP"."USERS"` (folded upper) |
| Snowflake | yes | yes | a schema, which **belongs to** a database — a distinct level, not the database itself | `"app"."orders"` — incomplete without the database level |
| BigQuery | yes | yes | a dataset; columns are never dataset-qualified | `` `app`.`orders` `` |
| MariaDB | yes | **no** | **a database** — `schema` is a synonym for `database`; `CREATE SCHEMA` and `SHOW SCHEMAS` are accepted and list databases | `` `app`.`users` `` |
| MySQL | yes | **no** | **a database** — same synonymy as MariaDB | `` `app`.`users` `` |
| ClickHouse | yes | yes | **a database** — there is no schema level; `CREATE SCHEMA` and `SHOW SCHEMAS` are syntax errors, and no `currentSchema()` function exists | `` `app`.`users` `` |
| SQLite (the built-in), Firebird | no | yes | no namespace layer | **refused** — see [§11](#11-sqlite-and-why-this-guide-is-written-in-postgresqls-dialect) |

Three things follow, and they are the reason a single model definition cannot
be assumed to mean the same thing everywhere:

- **Snowflake is the only one with a real schema layer of its own.** Its fully
  qualified name is `<database>.<schema>.<object>`, so a `schema_name` alone
  does not identify an object there.
- **MySQL, MariaDB and ClickHouse treat the value as a database.** For MySQL
  and MariaDB `schema` and `database` are the same word. ClickHouse is the same
  idea with the word removed: it has no `CREATE SCHEMA` at all, yet a
  `schema_name` is still accepted and used as the database, so `supports_schema()`
  is `True` — there is no distinct schema layer, but the value is usable.
- **MySQL and MariaDB are the two that cannot qualify an index name**, for the
  reason in [§5](#mysql-and-mariadb-an-index-name-cannot-be-qualified). Every
  other backend keeps the index in its own namespace when one is given.

What is *not* checked anywhere is whether the namespace exists, or whether it is
the one the session is using. A `schema_name` naming a different namespace
addresses a different object — or none.

## 11. SQLite, and why this guide is written in PostgreSQL's dialect

The backend this package ships with is SQLite, and **SQLite has no schema
layer** — not a weak one, none. An unqualified name resolves against the
database file; a qualified one names an *attached* database, which is a
different mechanism entirely.

So on the built-in backend, `__schema_name__` is a mistake:

```python
class User(ActiveRecord):
    __schema_name__ = "app"      # on SQLite this raises
```

It raises rather than being ignored, and that is deliberate. A model that lost
its namespace would read and write the default namespace instead, on every
query, with nothing in the generated SQL to indicate it. SQLite implements
`SchemaSupport` and answers `False` to `supports_schema()`, so a namespace is
validated and refused:

```
TableExpression(sqlite_dialect, "users", schema_name="app").to_sql()
# UnsupportedFeatureError: 'SQLite' dialect does not support a schema-qualified
# reference. … SQLite has no namespace to qualify into, so schema_name='app'
# cannot be used.

TableExpression(sqlite_dialect, "users").to_sql()[0]
# "users"
```

On a backend without a namespace, **do not pass one at all**: leave
`__schema_name__` unset and let the connection determine the namespace.

This raises a reasonable question about this document: if the built-in backend
can make no use of any of it, why do the examples throughout use
`"app"."users"`?

Because the rest of the SQL surface here is written to PostgreSQL. PostgreSQL is
the dialect the core expression layer is shaped around — the generic `TRUNCATE`
carries `RESTART IDENTITY` and `CASCADE` because PostgreSQL has them, and a
dialect that does not rejects them rather than ignoring them. Schema
qualification is the same story: the reference spelling, the reference rules
about three-part references and aliases, and the reference behaviour when a
model and its DDL disagree all come from PostgreSQL.

The examples were rendered with `DummyDialect`, the core package's own dialect,
which implements `SchemaSupport` and answers `True` to `supports_schema()` and
`supports_index_schema_qualification()`. It quotes identifiers the PostgreSQL way
and is otherwise the generic layer, so it exercises qualification without a
server. Consult [§10](#10-backend-support-matrix) for what your own backend does
with the same model. The parts that are *not* dialect-specific — where a
namespace comes from, when it is read, that DDL needs its own — hold everywhere.

## 12. Recommended layering

Let `search_path` carry the common case and reserve `__schema_name__` for the
exception:

```python
config = PostgresConnectionConfig(
    ...,
    search_path="app,public",   # ordinary tables resolve unqualified
)
```

* **Single schema** — do not set `__schema_name__` at all. Unqualified names
  plus `search_path` keep DML, DDL and introspection consistent with each other,
  and avoid three-part column references entirely.
* **Several schemas** — set `__schema_name__` only on the models that deviate
  from `search_path`, and build that model's DDL with the factories in
  [§6](#6-model-level-ddl-factories) so the two layers cannot drift apart. The
  smaller the exceptional surface, the less chance of running into the empty
  string of [§3](#3-when-validation-happens) or the unqualified table of
  [§4](#bare-strings-refused-in-some-places-accepted-in-others).
* **Cross-schema joins** — each side qualifies its own range, so this works
  without extra configuration:

  ```python
  Order.query().join(
      Customer, on=Order.c.id == Customer.c.id
  ).select(Order.c.id, Customer.c.name)
  # SELECT "shop"."orders"."id", "crm"."customers"."name"
  #   FROM "shop"."orders" JOIN "crm"."customers"
  #   ON "shop"."orders"."id" = "crm"."customers"."id"
  ```