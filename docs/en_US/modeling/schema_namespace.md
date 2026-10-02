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
* **The connection's `default_schema` setting.** Deprecated and inert: it has
  never affected generated SQL, and a model without `__schema_name__`
  resolves through `search_path` regardless. Set `search_path` instead.
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

Why reject rather than treat `""` as absent, when the renderer already treats a
falsy schema as absent? Because that fallback is the problem. `format_table`
asks `if expr.schema_name:` and takes the unqualified branch for `""` — so a
caller who asked for `app.users` would get `users`, with no error, no warning
and no affected-row count to notice it by. The statement still runs, and on any
connection whose search path happens to contain `app` it runs against the wrong
table. An empty string is nearly always how a schema gets lost in the first
place — an f-string that came out blank, a `config.get(...) or ""`, a missing
environment variable — and it is exactly the case where the caller is least able
to tell that the namespace went missing. Failing at construction is cheaper than
debugging a write that landed in the default schema.

The same reasoning is why the check lives in one place
(`_validate_schema_name`) rather than in each statement: an empty string has to
be rejected identically by all 40-odd expressions that accept one, at the moment
they are built, with a message that names the expression at fault.

## 4. DDL takes a schema of its own

> **`__schema_name__` selects the read/write namespace. DDL statements do not
> read it** -- but every statement that names a schema-bearing object accepts a
> `schema_name` of its own, so migration DDL no longer has to be qualified by
> hand.

| Statement | Picks up the model's schema? | How to qualify it |
|---|---|---|
| `CREATE TABLE` / `DROP TABLE` | no | pass `TableExpression(dialect, "users", schema_name="app")` |
| `ALTER TABLE` | no | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` / `REFRESH` VIEW, incl. materialized | no | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` TYPE | no | `schema_name="app"` |
| `CREATE INDEX` / `DROP INDEX`, incl. full-text | no | `schema_name="app"` |
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

## 5. What each kind of query does with the schema

`__schema_name__` is read in one place — `schema_name()` — and every query the
model builds passes it down. So the schema follows the model without each query
type having to know about it. What differs is the *shape* of the SQL, which is
worth knowing before you read a generated statement.

The examples below are PostgreSQL's rendering, measured rather than
illustrative.

### ActiveQuery — DML carries the schema

A model's `query()` qualifies every range it builds, which covers `SELECT`,
`INSERT`, `UPDATE` and `DELETE` alike:

```python
ShopOrder.query().select(ShopOrder.c.id).to_sql()[0]
# SELECT "shop"."orders"."id" FROM "shop"."orders"
```

Note the column is three-part: the range is unaliased, so the schema qualifies
it all the way through. Once an alias is in play the schema is dropped from the
column, because the alias already identifies the range:

```python
# FROM "shop"."orders" AS "o"
# SELECT "o"."id"        <- not "shop"."orders"."id"
```

This is not a simplification. A schema-qualified reference to an aliased range
is a syntax error on PostgreSQL and SQL Server.

### Joins — each side qualifies its own range

No additional configuration is required. Each model contributes its own
namespace, so a single statement may span two:

```python
Order.query().join(Customer, on=Order.c.customer_id == Customer.c.id)
# FROM "shop"."orders" JOIN "crm"."customers"
#   ON "shop"."orders"."customer_id" = "crm"."customers"."id"
```

### SetOperationQuery — no schema of its own

`UNION`, `INTERSECT` and `EXCEPT` combine queries rather than naming an object,
so there is nothing for them to qualify. Each branch retains its own:

```python
# SELECT ... FROM "shop"."orders"
# UNION
# SELECT ... FROM "crm"."customers"
```

One statement spanning two namespaces is legal on PostgreSQL, so a `UNION` over
two schema-bound models needs no special handling.

### CTEQuery — the CTE name is not in a namespace

A CTE is named for the rest of the query, not for the database, so its name is
never qualified — qualifying it would look for a table called `recent_orders` in
that schema and fail:

```python
# WITH recent_orders AS (SELECT "shop"."orders"."id" FROM "shop"."orders")
# SELECT "recent_orders"."id" FROM "recent_orders"
```

The inner `SELECT` still carries the model's schema; only the CTE's own name is
bare.

### Soft delete — restore carries it too

`restore()` rebuilds an `UPDATE` against the model's range, so it qualifies the
same way `delete()` does. A restore that dropped the schema would clear
`deleted_at` on the same-named table in the default schema and leave the
intended row soft-deleted — a cross-namespace write that no read-only assertion
would catch.

## 6. Qualifier binding

`Model.c.field` snapshots `table_name()` and `schema_name()` **when the
expression is built**, not when it is executed:

```python
condition = Order.c.total > 100     # bound to the current schema
Order.__schema_name__ = "tenant_b"  # too late for `condition`
condition = Order.c.total > 100     # rebuild to pick up the new schema
```

The same applies to `table_name()`. For tenant-style switching, rebuild
conditions after switching, or use one model class per namespace.

## 7. Backend support matrix

What a `schema_name` means is defined by each backend. All of them accept the
parameter; they do not agree on what it names. The table records what each one
does with it. Everything in this guide that shows `"app"."users"` is the
PostgreSQL / SQL Server / Oracle spelling.

| Backend | `supports_schema()` | What `schema_name` names | Renders as |
|---|---|---|---|
| PostgreSQL | yes | a schema inside the current database | `"app"."users"` |
| SQL Server | yes | a schema inside the current database | `[app].[users]` |
| Oracle | yes | a schema, which is the owning user | `"APP"."USERS"` (folded upper) |
| Snowflake | yes | a schema, which **belongs to** a database — a distinct level, not the database itself | `"app"."orders"` — incomplete without the database level |
| BigQuery | yes | a dataset; columns are never dataset-qualified | `` `app`.`orders` `` |
| MariaDB | yes | **a database** — `schema` is a synonym for `database`; `CREATE SCHEMA` and `SHOW SCHEMAS` are accepted and list databases | `` `app`.`users` `` |
| MySQL | yes | **a database** — same synonymy as MariaDB | `` `app`.`users` `` |
| ClickHouse | yes | **a database** — there is no schema level; `CREATE SCHEMA` and `SHOW SCHEMAS` are syntax errors, and no `currentSchema()` function exists | `` `app`.`users` `` |
| SQLite (the built-in), Firebird | no | no namespace layer | **refused** — see §8 |

Three things follow, and they are the reason a single model definition cannot
be assumed to mean the same thing everywhere:

- **Snowflake is the only one with a real schema layer of its own.** Its fully
qualified name is `<database>.<schema>.<object>`, so a `schema_name` alone
does not identify an object there.
- **MySQL, MariaDB and ClickHouse treat the value as a database.** For MySQL
and MariaDB `schema` and `database` are the same word, so `CREATE SCHEMA` and
`SHOW SCHEMAS` are accepted and list databases. ClickHouse is the same idea
with the word removed: it has no `CREATE SCHEMA` at all, yet a `schema_name`
is still accepted and used as the database, so `supports_schema()` is `True`
-- there is no distinct schema layer, but the value is usable.
- **The value is checked, but not against the connection.** A `schema_name`
  must be `None` or a non-empty string, and the dialect must be able to express
  a namespace at all; both are enforced while the statement is rendered (§7).
  What is *not* checked is whether the namespace exists or whether it is the one
  the session is using, so a `schema_name` naming a different namespace addresses
  a different object — or none.

## 8. SQLite, and why this guide is written in PostgreSQL's dialect

The backend this package ships with is SQLite, and **SQLite has no schema
layer** — not a weak one, none. An unqualified name resolves against the
database file; a qualified one names an *attached* database, which is a
different mechanism entirely.

So on the built-in backend, `__schema_name__` is a mistake:

```python
class User(ActiveRecord):
    __schema_name__ = "app"      # on SQLite this raises
```

It raises rather than being ignored, and that is deliberate. A model that
silently lost its schema would read and write the default schema instead, on
every query, with nothing in the generated SQL to indicate it — the failure
mode this guide is arranged to prevent. On a backend without a namespace, **do
not pass a schema at all**: leave `__schema_name__` unset and let the connection
determine the namespace.

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

Read the examples below as PostgreSQL's rendering, and consult §7 for the
behaviour of your own backend with the same model. The parts that are *not* dialect-specific — where a schema
comes from, when it is read, that DDL needs its own — hold everywhere.

## 9. Recommended layering

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
