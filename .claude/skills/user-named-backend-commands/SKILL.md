---
name: user-named-backend-commands
description: Addressable named-* layers in rhosocial-activerecord - named-connection, named-expression, named-procedure, named-procedure-graph and named-migration, resolved by fully qualified name, and their CLI subcommands
license: MIT
compatibility: opencode
metadata:
  category: backend
  level: advanced
  audience: users
  order: 7
  prerequisites:
    - user-activerecord-pattern
---

## What I do

Cover the **named-\* family** — the five layers where behaviour is addressed by
name rather than constructed inline. Each is a superset of the one below it:

| Layer | Subcommand | Resolves to |
|---|---|---|
| `named-connection` | `named-connection` | a callable returning a `BaseConfig` subclass |
| `named-expression` | `named-expression` | a function returning a `BaseExpression` |
| `named-procedure` | `named-procedure` | a `Procedure` subclass with `run(ctx)` |
| `named-procedure-graph` | `named-procedure-graph` | a callable returning a `ProcedureGraph` |
| `named-migration` | `named-migration` | a `NamedMigration` subclass with `up()`/`down()` |

## When to use me

- You want SQL, a workflow, or a schema change defined **once** and invoked by
  name from the CLI, a test, or another migration.
- You are running a migration and need to review, dry-run, or reverse it.
- A `NamedExpressionModuleNotAllowedError` or "no dialect bound" error appeared
  and you need to know which rule you broke.
- You are accepting a fully qualified name from outside your process and need to
  know how to constrain it.

## The three rules that govern every layer

These are enforced, not conventions. Violating them raises at resolution or
execution time — rule 1 surfaces as a plain Python `TypeError` about the
keyword `dialect`, rule 3 as `NamedExpressionModuleNotAllowedError`.

### 1. The first parameter must be named `dialect`

```python
# ✅ resolves — the resolver passes by keyword
def active_orders(dialect, customer_id: int):
    return QueryExpression(dialect, ...)

# ❌ TypeError: build_orders() got an unexpected keyword argument 'dialect'
def build_orders(sql_dialect, customer_id: int):
    ...
```

Because resolution is by keyword, a valid named expression is also an ordinary
function you can call directly from Python — same function, no wrapper.

### 2. Fully qualified names only

```bash
# ✅
named-expression myapp.queries.active_orders --list

# ❌ not accepted — no module path, no search path
named-expression active_orders --list
```

A short name is ambiguous as soon as two modules define the same function, and a
runner that guesses will eventually pick the wrong one. The resolver splits the
final `.` and imports the module path.

### 3. `allowed_modules` is mandatory for untrusted names

`None` (the default) means unrestricted. If the FQN came from a config file, a
web request, or anything an end user can influence, pass an allowlist:

```python
resolver = NamedExpressionResolver(allowed_modules=["myapp.queries"])
```

The check runs on the **string**, in the resolver's constructor, before
`import_module` is ever reached — so a disallowed module is never loaded into
the process. The CLI and the devtools MCP both accept names from outside the
code and must be given one.

> Most "it works in Python but not through the CLI" reports are rule 1 or rule 2.
> The errors are `NamedExpressionNotFoundError` (name does not resolve),
> `NamedExpressionModuleNotFoundError` (module does not import),
> `NamedExpressionNotCallableError` (resolves, but is not callable), and
> `NamedExpressionInvalidReturnTypeError` (called, but returned the wrong thing).

## Working with each layer

### named-expression — the base case

```bash
# What is in this module?
python -m rhosocial.activerecord.backend.impl.sqlite named-expression myapp.queries --list

# Signature and parameters, without running
... named-expression myapp.queries.active_orders --describe

# Render the SQL only
... named-expression --db-file app.db --dry-run --param customer_id=7 \
    myapp.queries.active_orders
```

Always `--dry-run` first. It costs nothing and shows the exact SQL, including
whether the dialect substituted anything.

### named-procedure — multi-step work

```bash
... named-procedure myapp.procedures.checkout --describe
... named-procedure --db-file app.db --dry-run --param order_id=7 \
    myapp.procedures.checkout
```

Flags: `--list --describe --dry-run --param --transaction --db-file
--named-connection --conn-param --async`.

### named-procedure-graph — a DAG of steps

The graph is validated and scheduled before anything runs, so the cheap
questions come first:

```bash
... named-procedure-graph myapp.graphs.monthly_report --list
... named-procedure-graph myapp.graphs.monthly_report.monthly_report --validate
... named-procedure-graph myapp.graphs.monthly_report.monthly_report --waves
... named-procedure-graph --db-file app.db --trace \
    myapp.graphs.monthly_report.monthly_report
```

`--waves` shows the topological layers — which steps run in parallel. Use it
when a graph is slower than you expect.

### named-migration — the only stateful layer

```bash
... named-migration myapp.migrations.migrations --list
... named-migration --db-file app.db --dry-run --direction up \
    myapp.migrations.migrations.V001CreateUsers
... named-migration --db-file app.db --direction up \
    --record-store migrations.json myapp.migrations.migrations.V001CreateUsers
```

Without `--record-store` the runner has no memory of what ran, so `down()` has
nothing to reverse. See `docs/en_US/backend/named_migration.md`.

## Async

Every layer has an async twin with identical names. Add `--async` to any of the
subcommands, or import `AsyncNamedMigration` / `AsyncMigrationRunner` /
`AsyncProcedure` in Python. `named-connection` and the record store are
synchronous regardless.

## Verify, do not trust the exit code

A green exit means the code path completed. To confirm the effect, check
independently:

```bash
... query --db-file app.db "SELECT name FROM sqlite_master WHERE type='table'"
```

The examples under `src/rhosocial/activerecord/backend/impl/sqlite/examples/`
follow this pattern — `named_migrations/run_basic.py` applies a migration,
asserts the table exists with a separate `query`, rolls back, and asserts it is
gone.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `TypeError: ... unexpected keyword argument 'dialect'` | first parameter is not named `dialect` |
| `NamedExpressionNotFoundError` | the FQN resolves, but that name is not in the module |
| `NamedExpressionModuleNotFoundError` | the module path does not import |
| `NamedExpressionModuleNotAllowedError` | module outside `allowed_modules` |
| `TypeError: ... is not a NamedMigration subclass` | FQN resolves, but to the wrong kind of object |
| `No dialect bound` | a type or expression was built without the dialect |
| `UnsupportedFeatureError` | the dialect lacks the feature; read the suggestion |
| Migration "already applied" | no `--record-store`, or a different store than last time |
| CLI hangs or fails inside `runpy` on `types` | run from the repo root, and prefer `-m` |

## Notes

- This is the only part of the library resolved by reflection, so **a typo in a
  name is a runtime error, not an import error** — static analysis will not catch
  it. The examples are executed in CI for this reason.
- There is no registry, decorator, or entry point. Discovery is purely
  "give me the FQN".

## See also

- `docs/en_US/backend/named_expression.md`
- `docs/en_US/backend/named_migration.md`
- `docs/en_US/backend/named_connection.md`
- `.claude/architecture.md` → "Named-* Subsystem"
