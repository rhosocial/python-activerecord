# Named Migration

> **Target Audience**: Application developers who change a schema over time and
> need the change to be reviewable, repeatable, and reversible.
> **Prerequisites**: [Named Expressions](./named_expression.md) — a migration
> runs named expressions, so read that first.

---

## Table of Contents

1. [Why Named Migration?](#1-why-named-migration)
2. [Core Concepts](#2-core-concepts)
3. [Defining a Migration](#3-defining-a-migration)
4. [Dependencies](#4-dependencies)
5. [Why Fully Qualified Names Only](#5-why-fully-qualified-names-only)
6. [No Raw SQL](#6-no-raw-sql)
7. [Applying Migrations](#7-applying-migrations)
8. [The Record Store](#8-the-record-store)
9. [CLI Usage](#9-cli-usage)
10. [Async](#10-async)
11. [Runnable Examples](#11-runnable-examples)

---

## 1. Why Named Migration?

Schema changes are the part of an application most likely to be applied twice,
in the wrong order, or to one environment and not another. A migration tool
makes the order explicit and the state recorded.

The named-* family gives you one vocabulary across the whole schema lifecycle:

| Layer | Question it answers | Reference |
|---|---|---|
| `named-connection` | Which database? | [Named Connection](./named_connection.md) |
| `named-expression` | What SQL? | [Named Expressions](./named_expression.md) |
| `named-procedure` | What multi-step operation? | [Named Expressions](./named_expression.md) |
| `named-procedure-graph` | What DAG of operations? | [Named Expressions](./named_expression.md) |
| **`named-migration`** | **In what order, and what has already run?** | **this page** |

A migration is the only layer that is *stateful*. Everything below it is a pure
description of SQL; a migration additionally knows what has already been applied.

---

## 2. Core Concepts

**A migration is a class, not a file of SQL.** It declares a `version`, optional
`dependencies`, and `up()` / `down()` methods:

```python
from rhosocial.activerecord.backend.migration import NamedMigration, MigrationContext


class V001CreateUsers(NamedMigration):
    """Create the ``users`` table."""

    version = "v001_create_users"

    def up(self, ctx: MigrationContext) -> None:
        ctx.execute("myapp.schema.create_users_table")

    def down(self, ctx: MigrationContext) -> None:
        ctx.execute("myapp.schema.drop_users_table")
```

`down()` is not optional in spirit. A migration you cannot reverse is a decision
you have to make deliberately, and the class shape makes you decide it by
writing the method.

**`MigrationContext` is what `up()`/`down()` talk to.** It carries the dialect and
the current bindings, and offers:

| Member | Purpose |
|---|---|
| `ctx.execute(fqn, params=None, bind=None, output=False)` | run a named expression |
| `ctx.scalar(fqn, ...)` | run one and return a single value |
| `ctx.rows(fqn, ...)` | run one and return rows |
| `ctx.bind(key, value)` | record a value for later statements |
| `ctx.parallel(...)` | run independent expressions together |
| `ctx.log(...)` | emit progress |
| `ctx.abort(...)` | stop the migration deliberately |
| `ctx.dialect` | the dialect in use |

**Parameters** are declared by overriding `get_parameters()` and are supplied per
run, which is what lets one migration serve more than one table name:

```python
class V003CreateCustomTable(NamedMigration):
    version = "v003_create_custom_table"
    table_name: str = "custom_table"

    def get_parameters(self) -> dict:
        return {"table_name": self.table_name}

    def up(self, ctx: MigrationContext) -> None:
        ctx.execute("myapp.schema.create_config_table", {"table_name": self.table_name})
```

---

## 3. Defining a Migration

Migrations are ordinary Python, so they can be ordinary Python:

```python
class V004BackfillSlug(NamedMigration):
    """Give every post a slug derived from its title."""

    version = "v004_backfill_slug"
    dependencies = ["v002_create_posts"]

    def up(self, ctx: MigrationContext) -> None:
        ctx.execute("myapp.schema.add_slug_column")
        ctx.execute("myapp.data.backfill_slugs", batch_size=500)

    def down(self, ctx: MigrationContext) -> None:
        ctx.execute("myapp.schema.drop_slug_column")
```

Note that the second statement is a *named data* expression rather than DDL. A
migration is not restricted to schema changes; it is a versioned, ordered,
recorded unit of work.

---

## 4. Dependencies

`dependencies` lists the versions that must already be applied:

```python
class V002CreatePosts(NamedMigration):
    version = "v002_create_posts"
    dependencies = ["v001_create_users"]
```

The runner resolves the graph and applies prerequisites first. Cycles, missing
versions, and a version belonging to a different migration class are all errors
rather than warnings:

| Error | Meaning |
|---|---|
| `MigrationDependencyError` | a declared dependency is missing or unsatisfied |
| `MigrationVersionConflictError` | the record store has this version under a different FQN |
| `MigrationAlreadyAppliedError` | `up()` on a version the store says is already applied |
| `MigrationNotAppliedError` | `down()` on a version that is not recorded as applied |

---

## 5. Why Fully Qualified Names Only

A migration is addressed by **fully qualified name** — module path plus class
name — and nothing shorter is accepted:

```bash
-- ✅ resolves
named-migration myapp.migrations.v001.V001CreateUsers

# ❌ not accepted
named-migration V001CreateUsers
named-migration v001_create_users
```

This is deliberate. A short name is ambiguous the moment there are two modules
that define a `V001CreateUsers`, and a migration runner that guesses between
them will eventually apply the wrong one to production. The cost is verbosity
in the command line; the benefit is that the thing being run is never in doubt.

The resolver also accepts an allowlist. When one is supplied, only migrations
whose module matches are imported at all:

```python
resolver = NamedMigrationResolver(allowed_modules=["myapp.migrations"])
```

Anything else raises `NamedExpressionModuleNotAllowedError` *before* the module
is imported — the check happens on the name, so a disallowed module is never
loaded into the process.

> The same rule governs the whole named-* family. If you are reaching for raw SQL
> in a migration, see the next section.

---

## 6. No Raw SQL

`ctx.execute()` takes a named expression FQN, not a SQL string. Migrations are
built from expressions:

```python
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression, ColumnDefinition, ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteIntegerType, SQLiteTextType,
)


def create_users_table(dialect):
    """CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)."""
    return CreateTableExpression(
        dialect,
        table="users",
        columns=[
            ColumnDefinition(
                dialect, "id", SQLiteIntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition(dialect, "name", SQLiteTextType(dialect)),
        ],
    )
```

Three reasons this matters:

1. **A migration that renders through a dialect is portable.** The same
   migration produces valid SQL on PostgreSQL and SQLite because the dialect
   decided the types, not the string.
2. **It is dry-runnable.** `--dry-run` renders every statement without executing,
   so a migration can be reviewed as SQL before it touches anything.
3. **Capabilities are checked, not discovered at runtime.** SQLite has no
   `CREATE OR REPLACE VIEW`; asking for one raises `UnsupportedFeatureError`
   with a suggestion, rather than failing halfway through a migration.

> `NamedMigration` deliberately does not accept arbitrary SQL. If you need a
> statement the expression layer does not model, model it as a named expression
> first — that keeps it dry-runnable and dialect-aware like everything else.

---

## 7. Applying Migrations

`MigrationRunner` is constructed with a migration FQN, then run against a
backend:

```python
from rhosocial.activerecord.backend.migration import (
    MigrationRunner, MigrationDirection, JSONFileMigrationRecordStore,
)

runner = MigrationRunner("myapp.migrations.v001.V001CreateUsers")
store = JSONFileMigrationRecordStore("migrations.json")

# review first
print(runner.run(backend, MigrationDirection.UP, dry_run=True).statements)

# then apply, recording what happened
result = runner.run(backend, MigrationDirection.UP, record_store=store)

# and reverse it
runner.run(backend, MigrationDirection.DOWN, record_store=store)
```

`run()` takes:

| Argument | Default | Meaning |
|---|---|---|
| `backend` | — | the backend to apply against |
| `direction` | — | `MigrationDirection.UP` or `.DOWN` |
| `user_params` | `None` | values for `get_parameters()` |
| `record_store` | `None` | where to record applied versions |
| `dry_run` | `False` | render only, execute nothing |
| `manage_transaction` | `True` | wrap the run in one transaction |

`manage_transaction=True` is the default on purpose: a migration that half-applies
leaves a schema no code expects. Pass `False` only for statements that cannot run
inside a transaction (`CREATE INDEX CONCURRENTLY` on PostgreSQL, for instance).

---

## 8. The Record Store

Without a record store the runner has no memory: it cannot tell you what has
already run, and `down()` has nothing to reverse. `MigrationRecordStore` is the
interface; `JSONFileMigrationRecordStore` is the bundled implementation:

```python
store = JSONFileMigrationRecordStore("migrations.json")
```

Each entry is a `MigrationRecord`:

| Field | Meaning |
|---|---|
| `version` | the migration's `version` |
| `migration_fqn` | the FQN that was applied |
| `direction` | `up` or `down` |
| `applied_at` | timestamp |
| `success` | whether it completed |
| `error_message` | populated on failure |
| `snapshot_before` | schema snapshot prior to the run |
| `snapshot_after` | schema snapshot after it |

The two snapshots are what make a migration reviewable after the fact: you can
diff them to see exactly what a migration did, rather than inferring it from the
code.

---

## 9. CLI Usage

```bash
# List everything in a module
python -m rhosocial.activerecord.backend.impl.sqlite named-migration \
    myapp.migrations.migrations --list

# Inspect one without running it
python -m rhosocial.activerecord.backend.impl.sqlite named-migration \
    myapp.migrations.migrations.V001CreateUsers --describe

# Render the SQL it would run
python -m rhosocial.activerecord.backend.impl.sqlite named-migration \
    --db-file app.db --dry-run --direction up \
    myapp.migrations.migrations.V001CreateUsers

# Apply it
python -m rhosocial.activerecord.backend.impl.sqlite named-migration \
    --db-file app.db --direction up --record-store migrations.json \
    myapp.migrations.migrations.V001CreateUsers

# Supply a parameter
python -m rhosocial.activerecord.backend.impl.sqlite named-migration \
    --db-file app.db --direction up --param table_name=feature_flags \
    myapp.migrations.migrations.V003CreateCustomTable

# Reverse it
python -m rhosocial.activerecord.backend.impl.sqlite named-migration \
    --db-file app.db --direction down --record-store migrations.json \
    myapp.migrations.migrations.V001CreateUsers
```

| Flag | Meaning |
|---|---|
| `--list` | list migrations in a module |
| `--describe` | show signature, dependencies, and docstring |
| `--dry-run` | render statements without executing |
| `--direction {up,down}` | which way to run |
| `--record-store PATH` | JSON file recording applied versions |
| `--param KEY=VALUE` | repeatable; values for `get_parameters()` |
| `--all` | apply every pending migration in the module |
| `--single-transaction` | run the whole set in one transaction |
| `--async` | use the async runner |
| `--db-file PATH` | target database (overrides a named connection) |
| `--named-connection FQN` | take the target from a named connection |

> **Verify, do not trust the exit code.** A migration reporting success is a
> claim about the code path it took, not evidence about the schema. The
> runnable example below checks with an independent `query` call after each step.

---

## 10. Async

Every synchronous entry point has an async twin, with the same names:

| Sync | Async |
|---|---|
| `NamedMigration` | `AsyncNamedMigration` |
| `MigrationRunner` | `AsyncMigrationRunner` |
| `MigrationContext` | `AsyncMigrationContext` |
| `JSONFileMigrationRecordStore` | shared (I/O is synchronous) |
| `--direction up` | `--direction up --async` |

```python
from rhosocial.activerecord.backend.migration import AsyncMigrationRunner, MigrationDirection

runner = AsyncMigrationRunner("myapp.migrations.v001.V001CreateUsers")
result = await runner.run(backend, MigrationDirection.UP, record_store=store)
```

---

## 11. Runnable Examples

Working code lives in the SQLite backend's examples directory and is executed by
CI:

| File | Shows |
|---|---|
| `named_migrations/migrations.py` | Three migrations: plain, dependent, parameterised |
| `named_migrations/expressions.py` | The named expressions those migrations run |
| `named_migrations/run_basic.py` | Full `up` → verify → `down` cycle in Python, with `assert`s |
| `named_migrations/run_chain.py` | Dependency ordering and the errors it raises |
| `named_migrations/demo_basic.sh` | The same cycle from the shell, verifying with `query` |

```bash
# Run the full example suite
bash src/rhosocial/activerecord/backend/impl/sqlite/examples/run_all_examples.sh --fast

# Just the migration examples
bash src/rhosocial/activerecord/backend/impl/sqlite/examples/run_all_examples.sh named_migrations
```

`run_basic.py` is the best single reference: it creates a temporary database,
applies the migration, asserts the table exists with an independent query, rolls
back, and asserts the table is gone.

---

## See Also

- [Named Expressions](./named_expression.md) — what a migration actually runs
- [Named Connection](./named_connection.md) — choosing the target database
- [Schema Diff](../backend/introspection.md) — verifying what a migration changed
