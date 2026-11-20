# Migrations — The Backend Runtime System

> This chapter documents ActiveRecord's **native migration system** — the backend/runtime layer that
> orders, executes, records, and rolls back schema changes over time. It is distinct from the
> model-level DDL derivation described in [DDL](../modeling/ddl.md): that layer turns a model's current
> declaration into a statement; this layer manages a *sequence* of such statements as versioned,
> reversible migrations.
>
> Scope note: all examples use the built-in SQLite backend. Other backends are documented in their
> own repositories.

## 1. Two APIs, two entry points

The migration system exposes **two authoring APIs that are deliberately separate** (see
`backend/migration/functions.py:14-16`). They are not interchangeable:

| | Function migrations (primary) | Class migrations (legacy-compatible) |
|---|---|---|
| Authoring unit | an `@migration`-decorated function | a `NamedMigration` / `AsyncNamedMigration` subclass with `up()`/`down()` |
| Orchestrator | `run_migration_group()` / `run_migration_group_async()` | `MigrationRunner` / `AsyncMigrationRunner` / `BatchMigrationRunner` |
| CLI | the model CLI's `migrate` command | each backend CLI's `named-migration` command |
| Status | actively developed, recommended | fully supported, kept for compatibility |

Both paths share the same foundations: `MigrationContext`, `MigrationDirection`, the version-record
model, the typed exception hierarchy, and the `Procedure` execution engine. Use **function
migrations** for new work; use class migrations only to maintain existing migration classes.

> 💡 **AI Prompt**: "I have a model with a `@migration`-decorated classmethod. Show me how to run it
> as a dry run and then for real with a JSON version record using SQLite."

## 2. Vocabulary

- **version** — a string identifier for a migration (`@migration("v001_create_users")`). Uniqueness
  is enforced at run time; a versionless decorator falls back to the function name.
- **direction** — `UP` (apply) or `DOWN` (roll back), from `MigrationDirection`.
- **dependency** — another version that must already be applied (or appear earlier in the group).
  Dependencies are **validated, not auto-resolved** — see §4.
- **record store** — a `MigrationRecordStore` strategy that persists which versions are applied.
  The only built-in implementation is `JSONFileMigrationRecordStore`; there is **no built-in
  database-table store** — you supply one if you want records in the database.
- **dry run** — render and collect every statement without touching the database or writing records.

## 3. Function migrations (primary API)

### 3.1 Writing a migration function

```python
from typing import Annotated, Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.migration import migration, MigrationDirection


# ActiveRecord already mixes in MigrationMixin, so the statement getters
# (create_table_statement / drop_table_statement) are available on every model.
class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("v001_create_users", description="initial users table")
def create_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(User.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))
```

Key rules:

- The decorator signature is `migration(version="", *, dependencies=(), description="", async_variant="")`.
  `dependencies` must be a sequence of non-empty strings (a bare string is rejected); `async_variant`
  must be a non-blank FQN.
- A migration function must take **exactly one positional `ctx`** parameter — no required keyword-only
  parameters, no `*args`/`**kwargs`. Signature checks happen when the function reference is resolved,
  not at decoration time.
- A function may be **module-level** or a model `@classmethod`/`@staticmethod`. Plain instance
  methods are rejected. The model owning a classmethod is remembered as the function's `owner`.
- `ctx.apply(*expressions)` accepts statement objects (anything with `.to_sql() -> (sql, params)`) or
  a single list/tuple of them. It is the DDL path. The named-expression path is `ctx.execute(FQN, ...)`
  — see the [Named Expressions](../backend/named_expression.md) chapter.

### 3.2 Referencing a function (FQN)

Functions are referenced by **fully qualified name**, either `module:function` (preferred) or
`module.Class.method`. `resolve_migration_function()` validates the reference, the `@migration`
metadata, the signature, and the owner type, returning a `MigrationFunctionRef` (`fqn`, `function`,
`info`, `owner`, `is_async`). Passing a class FQN — including a `NamedMigration` subclass — is an
error with a hint to use the backend's `named-migration` command instead.

### 3.3 Running a group

```python
from rhosocial.activerecord.backend.migration import run_migration_group
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore

store = JSONFileMigrationRecordStore("migration_records.json")

# dry run — nothing is written
preview = run_migration_group(backend, ["app.migrations:create_users"], dry_run=True)
print(preview.dry_run_sql)        # [(label, sql, params), ...]
print(preview.dry_run_total)      # statement count

# real run
result = run_migration_group(backend, ["app.migrations:create_users"], record_store=store)
print(result.applied, result.versions, result.records_written)

# roll back
run_migration_group(backend, ["app.migrations:create_users"],
                    direction=MigrationDirection.DOWN, record_store=store)
```

`run_migration_group(backend, functions, *, direction=UP, record_store=None, dry_run=False,
transaction_mode=TransactionMode.AUTO)` accepts `MigrationFunctionRef`s, FQN strings, or decorated
callables. It returns a `MigrationGroupResult` (`direction`, `dry_run`, `versions`, `applied`,
`rolled_back`, `dry_run_sql`, `dry_run_total`, `records_written`).

What it guarantees:

- **Order is caller-defined**: UP executes functions in the order given; DOWN reverses that order.
  The group does **not** topologically sort — dependencies are checked, not resolved (§4).
- A group internally builds a `Procedure` subclass and runs it through `ProcedureRunner`, so each
  function sees a `MigrationContext` with its `ctx.version` set and `transaction_mode` applied.
- After a run it calls `backend.introspector.clear_cache()` so subsequent introspection sees the
  new schema.
- On success (and only when not a dry run) it writes one `MigrationRecord` per function. On failure
  it writes no record and raises `MigrationFunctionExecutionError` carrying `version`, `fqn`,
  `cause`, `executed`, and `transactional_ddl`.

### 3.4 Async variant

`run_migration_group_async()` mirrors the sync API. An async run uses
`select_async_functions()` to substitute each function's `@migration(async_variant="...")` partner:
the async function must declare the **same version**, and the version record keeps the **sync FQN**
as its canonical key, so a version applied synchronously and one applied asynchronously never
collide. A sync function with no `async_variant` cannot be used in an async run.

## 4. Ordering, dependencies, and validation

This is the most misunderstood part of the function API:

- **No auto-sort.** Unlike the legacy `BatchMigrationRunner` (which performs a real topological
  sort), `run_migration_group` uses your list order verbatim for UP and its reverse for DOWN.
- **Dependencies are validated**: for UP, a dependency must either appear earlier in the group or be
  already applied in the record store; otherwise `MigrationDependencyError` is raised. Duplicate
  versions in one group raise `MigrationError`; a version recorded under a different FQN raises
  `MigrationVersionConflictError`; re-applying an applied version (UP) or rolling back an unapplied
  one (DOWN) raises `MigrationAlreadyAppliedError` / `MigrationNotAppliedError`.
- Consequently, **you are responsible for supplying the correct execution order**; dependencies are
  a safety check, not a scheduler.

## 5. Version records

`MigrationRecord` (`backend/migration/record.py`) carries `version`, `migration_fqn`, `direction`,
`applied_at` (timezone-aware UTC), `success`, and an optional `error_message`.

`MigrationRecordStore` is an abstract strategy with `get_applied()`, `record()`, and `is_applied()`.
There is no built-in database-backed store; `JSONFileMigrationRecordStore(path)` is the only
concrete implementation. Its `get_applied()` computes **successful UP versions minus successfully
rolled-back DOWN versions**, so a version disappears from "applied" after a clean rollback.

## 6. Dry run — two capture paths

Dry run renders every statement and never touches the database or records. There are two ways a
migration emits statements, and both are captured:

1. **`ctx.apply(...)`** — statements are recorded by the context with a label
   `"<version> <ExpressionClass>"`, landing in `ctx.dry_run_sql`.
2. **Direct model writes**, e.g. `User.create_table(backend=ctx.backend)` — these call the backend
   directly. The group wraps the backend in a `DryRunBackend` and temporarily repoints each owner
   model's `__backend__` to that proxy, so even direct writes are recorded (as `backend.execute`) and
   no real SQL runs. All state is restored in a `finally` block.

The CLI caps dry-run display at 100 statements (`--dry-run` prints the rendered SQL plus a
"N statement(s) rendered; no changes written" summary).

> ⚠️ **Legacy-runner caveat (class API only)**: in the `MigrationRunner` path, `ctx.apply()` SQL goes
> to `ctx.dry_run_sql`, but `MigrationRunner.run()` builds its returned `dry_run_sql` only from the
> named-expression callback. The function-style `run_migration_group` path captures both correctly.

## 7. The `migrate` CLI (function API)

The model CLI exposes a top-level `migrate` command:

```bash
python -m rhosocial.activerecord.cli migrate app.migrations:create_users \
    --model app.models:User --record-store records.json --dry-run
python -m rhosocial.activerecord.cli migrate --list --model app.models:User
python -m rhosocial.activerecord.cli migrate --plan --model app.models:User
python -m rhosocial.activerecord.cli migrate app.migrations:create_users \
    --model app.models:User --record-store records.json --direction down -o json
```

Arguments: one or more function FQNs; `--direction up|down`; `--record-store PATH|module:Class`;
`--dry-run`; `--list`; `--plan`; `--async`; `-o text|json`; `--model MODULE:CLASS`; plus shared
connection options. `--list`/`--plan` print and exit **before connecting**. Connection comes either
from `--model` (the model's configured backend) or explicit `--backend-class`/`--config-class`.

JSON mode emits a `{"command": "migrate", ...}` payload; failures include `migration_version`,
`migration_fqn`, `executed`, `transactional_ddl`, and `rolled_back`.

## 8. Class migrations (legacy-compatible)

Author a `NamedMigration` subclass with `up(ctx)`/`down(ctx)` (or `AsyncNamedMigration` with async
methods). `MigrationRunner(migration_fqn).run(backend, direction, ...)` executes one migration with
dependency checks, duplicate protection, version-record writes, and a `MigrationResult`.
`BatchMigrationRunner(module_name)` discovers all `NamedMigration` subclasses in a module and runs
them in **topological order by dependencies** (the only auto-sorting component), with
`migrate_up()`/`migrate_down()`, `status()`, and `pending_versions()`. `DOWN` reverses the
topological order; `single_transaction=True` wraps the whole batch and writes records only after the
final commit.

Each backend CLI also exposes a `named-migration` command that delegates to these helpers. Its
parser takes a **qualified name** plus `--direction up|down`, `--record-store`, `--dry-run`,
`--describe`, `--list`, `--param KEY=VALUE`, `--all`, and `--single-transaction`.

> The legacy class-style system is fully supported but not the recommended path for new work.
> Existing runnable demos live in
> `src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/`.

## 9. Exception hierarchy

All under `MigrationError` (which extends `ProcedureError`): `MigrationDependencyError`,
`MigrationAlreadyAppliedError`, `MigrationNotAppliedError`, `MigrationVersionConflictError`,
`MigrationDialectError` (a dialect raised `ProtocolNotImplementedError`/`UnsupportedFeatureError`
during DDL), and `MigrationFunctionExecutionError` (wraps a failing function with context).
`MigrationFunctionError` is separate — it signals a bad FQN, signature, or ownership at resolution.

## 10. API quick reference

| Concern | API | Module |
|---|---|---|
| Decorator / resolver | `migration`, `resolve_migration_function`, `MigrationInfo`, `MigrationFunctionRef` | `backend.migration.functions` |
| Execution context | `MigrationContext.apply`, `AsyncMigrationContext.apply` | `backend.migration.context` |
| Function groups | `run_migration_group`, `run_migration_group_async`, `select_async_functions` | `backend.migration.group` |
| Class runners | `MigrationRunner`, `AsyncMigrationRunner`, `BatchMigrationRunner` | `backend.migration.{runner,async_runner,batch_runner}` |
| Class bases | `NamedMigration`, `AsyncNamedMigration`, `MigrationDirection` | `backend.migration.core` |
| Records | `MigrationRecord`, `MigrationRecordStore`, `JSONFileMigrationRecordStore` | `backend.migration.record` |
| Exceptions | `MigrationError` and subclasses, `MigrationFunctionError` | `backend.migration.exceptions`, `functions` |
| Model DDL | `MigrationMixin`, `AsyncMigrationMixin` | `base.migration_mixin` |
| CLI | `migrate` (model CLI), `named-migration` (backend CLI) | `cli`, `backend.migration.cli` |
