# Schema Namespaces

> How to bind a model to a database schema, and what decides whether the
> schema shows up in the SQL that gets executed.

Schemas are the closest thing most databases have to a namespace. PostgreSQL,
SQL Server and Oracle treat them as a first-class part of an object's name;
MySQL/MariaDB call the same thing a "database"; BigQuery calls it a "dataset";
Snowflake nests it inside a database. This guide covers declaring a schema on a
model and — just as importantly — what that declaration does *not* cover.

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
reports `relation "app.users" does not exist`. Use `__schema_name__`, or pass a
`(schema, table)` tuple where a tuple is accepted.

## 2. What decides whether the schema appears in the SQL

There is exactly one decision chain, and no configuration knob in it:

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
`None` as soon as a table alias is in effect. Building a `Column` by hand and
bypassing `FieldProxy` skips that guard, so a hand-built
`Column(dialect, "id", table="u", schema_name="ar_crm")` renders the
three-part form that PostgreSQL rejects.

### Three things you do not control

* **`search_path`.** Applied at connect time as a libpq parameter, so it is
  fixed for the life of the connection and cannot be changed per query or per
  transaction. Unqualified names resolve through it.
* **The connection's `default_schema` setting.** It has never affected
  generated SQL. A model without `__schema_name__` resolves through
  `search_path`; use that instead.
* **The alias.** Once set, the schema is dropped from column references by
  design.

## 3. Anti-patterns

```python
__table_name__ = "app.users"   # WRONG: renders FROM "app.users"
__schema_name__ = ""          # WRONG: treated as "no schema", or rejected
```

`__schema_name__ = ""` deserves emphasis. An empty schema is a mistake, not a
way to say "unqualified" — that is what `None` means. Empty strings are now
rejected outright, and a non-string value is rejected too. The same applies to
`TableExpression(schema_name=...)` and to every `*Options` DML object.

## 4. DDL takes a schema of its own

> **`__schema_name__` selects the read/write namespace. DDL statements do not
> read it** -- but every statement that names a schema-bearing object accepts a
> `schema_name` of its own, so migration DDL no longer has to be qualified by
> hand.

| Statement | Picks up the model's schema? | How to qualify it |
|---|---|---|
| `CREATE TABLE` / `DROP TABLE` | no | pass `TableExpression(dialect, "users", schema_name="app")` |
| `CREATE` / `ALTER` / `DROP` / `REFRESH` VIEW, incl. materialized | no | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` TYPE | no | `schema_name="app"` |
| `CREATE` / `DROP` INDEX, incl. full-text | no | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` SEQUENCE | no | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` DOMAIN | no | `schema_name="app"` |
| `CREATE` / `DROP` FUNCTION | no | `schema_name="app"` |
| `CREATE` / `DROP` TRIGGER | no | `schema_name="app"` |
| `TRUNCATE` | no | has its own `schema=` field |
| `SELECT` / `INSERT` / `UPDATE` / `DELETE` | **yes** | automatic |

`schema_name` defaults to `None`, which means unqualified -- the same default
as everywhere else in the expression layer. Passing `""` is rejected, because an
empty string is a mistake rather than a way of saying "unqualified".

A model pointing at `app.users` and a migration creating `public.users` still do
not agree automatically: `__schema_name__` is not consulted when DDL is built,
so a migration has to name the schema it means. It can now say so directly
rather than assembling a qualified name by hand.

On a backend without namespaces, supplying a schema raises
`UnsupportedFeatureError` rather than quietly dropping it. SQLite is the case
in practice: it has no schema layer, so a qualified name would reach the server
as something it rejects.

## 5. Qualifier binding

`Model.c.field` snapshots `table_name()` and `schema_name()` **when the
expression is built**, not when it is executed:

```python
condition = Order.c.total > 100     # bound to the current schema
Order.__schema_name__ = "tenant_b"  # too late for `condition`
condition = Order.c.total > 100     # rebuild to pick up the new schema
```

The same applies to `table_name()`. For tenant-style switching, rebuild
conditions after switching, or use one model class per namespace.

## 6. Backend support matrix

What a `schema_name` means is defined by each backend. All of them accept the
parameter; they do not agree on what it names. The table records what each one
does with it. Everything in this guide that shows `"app"."users"` is the
PostgreSQL / SQL Server / Oracle spelling.

| Backend | `supports_schema()` | What `schema_name` names | Renders as |
|---|---|---|---|
| PostgreSQL | yes | a schema inside the current database | `"app"."users"` |
| SQL Server | yes | a schema inside the current database | `[app].[users]` |
| Oracle | yes | a schema, which is the owning user | `"APP"."USERS"` (folded upper) |
| Snowflake | yes | a schema, which **belongs to** a database — a distinct level, not the database itself | needs `CURRENT_DATABASE()` to be fully qualified |
| BigQuery | yes | a dataset; columns are never schema-qualified | `` `app.users` `` |
| MariaDB | yes | **a database** — `schema` is a synonym for `database`; `CREATE SCHEMA` and `SHOW SCHEMAS` are accepted and list databases | `` `app`.`users` `` |
| MySQL | yes | **a database** — same synonymy as MariaDB | `` `app`.`users` `` |
| ClickHouse | no | **a database** — there is no schema level; `CREATE SCHEMA` and `SHOW SCHEMAS` are syntax errors, and no `currentSchema()` function exists | `` `app`.`users` `` |
| SQLite, Firebird | no | no namespace layer | rejected |

Three things follow, and they are the reason a single model definition cannot
be assumed to mean the same thing everywhere:

- **Snowflake is the only one with a real schema layer of its own.** Its fully
  qualified name is `<database>.<schema>.<object>`, so a `schema_name` alone
  does not identify an object there.
- **MySQL and MariaDB treat the value as a database**, where `schema` and
  `database` are the same thing; `CREATE SCHEMA` and `SHOW SCHEMAS` are accepted
  and list databases. ClickHouse is the same idea with the word removed: it has
  no `CREATE SCHEMA` at all, and it reports `supports_schema() == False` because
  there is no distinct schema layer, even though a `schema_name` is still
  accepted and used as the database.
- **The value is passed through as given.** Nothing here checks it against the
  connection, so a `schema_name` naming a different namespace than the session's
  current one addresses a different object — or none.

## 7. Recommended layering

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
  from `search_path`. The smaller the exceptional surface, the less chance of
  hitting the anti-patterns above.
* **Cross-schema joins** — each side qualifies its own range, so this works
  without extra configuration:

  ```python
  Order.query().join(
      Customer, on=Order.c.customer_id == Customer.c.id
  ).select(Order.c.id, Customer.c.name)
  # SELECT ... FROM "shop"."orders" JOIN "crm"."customers" ON ...
  ```
