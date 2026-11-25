# ActiveRecord-layer migration guide

> This chapter documents ActiveRecord's **own** migration capability: you write
> `up(ctx)` / `down(ctx)` logic and the framework manages ordering, execution,
> dry-run and version records. It is distinct from the backend `migrate` command
> (see [Migration System](README.md)), which belongs to the backend runtime.

## 1. The mental model

A migration has two parts:

```python
from rhosocial.activerecord.migration import Migration

def up(ctx):     # apply a change
    ...

def down(ctx):   # roll it back
    ...

m = Migration("v001_add_users", up, down, dependencies=(), description="...")
```

The **user owns** the up/down logic. The **framework owns** everything around it:

| Concern | Owner |
|---|---|
| Order (UP as given, DOWN reversed), dependency checks, duplicate/guard checks | `MigrationRunner` |
| Execution vs dry-run rendering | `ctx.apply()` |
| Version records (applied / rolled back) | pluggable `MigrationRecordStore` |
| "How do I do this operation on this database?" | backend **suggestions** (optional) |

## 2. The context: `ctx`

`ctx` is your bridge to the database:

- `ctx.apply(*expressions)` — execute DDL/DML expressions, or, under dry-run,
  only render them into `ctx.dry_run_sql`. Accepts a single list/tuple, so a
  suggestion's result can be passed straight through.
- `ctx.backend`, `ctx.direction`, `ctx.version`, `ctx.is_up`, `ctx.is_down`.
- `ctx.suggest_partition_<x>(strategy, plan)` — eight "how-to" accessors:
  `build`, `table_drop`, `table_alter`, `add`, `drop`, `split`, `merge`,
  `retention`. Each returns an ordered expression chain, `None` (nothing to do),
  or `None` (unsupported — the helper folds both to `None`; check the raw
  suggestion if the distinction matters).

## 3. When to use a suggestion

Use the expression-dialect system directly when an operation is a **single
standard action** whose only difference across databases is spelling (add/drop
column, rename, etc.). The dialect renders the right SQL per backend.

Ask for a suggestion when the same intent needs a **different multi-step action
chain** on different databases — e.g. partitioning lifecycle:

- "add a partition" → `ADD PARTITION` (MySQL) / `CREATE TABLE ... PARTITION OF`
  (PostgreSQL) / `SPLIT RANGE` (SQL Server, data-affecting) / no-op (ClickHouse).
- "retire old partitions" → DROP (MySQL/Oracle) / DETACH→DROP (PostgreSQL) /
  MERGE RANGE (SQL Server) / DROP PARTITION ID (ClickHouse).

A suggestion is **optional**: if you know you are locked to one backend, write
that backend's expression directly in `up`/`down` instead.

## 4. Dry-run

```python
preview = runner.run([migration], store=store, dry_run=True)
for sql, params in preview.results[0].dry_run_sql:
    print(sql)          # rendered, never executed
assert preview.applied == []   # no records written
```

## 5. up / down and version records

```python
runner.run([m], store=store)                       # UP, records version
runner.run([m], direction="down", store=store)     # DOWN, reverses + clears
store.get_applied()                                 # current applied versions
```

DOWN reverses the supplied order. Dependencies must appear earlier in the
group or already be applied; re-applying an applied version or rolling back an
unapplied one raises a typed error.

## 6. Async

`AsyncMigration` / `AsyncMigrationRunner` / `AsyncMigrationContext` mirror the
sync API (`await ctx.apply(...)`, `await runner.run(...)`) with identical names.

## 7. Backend differences

Partitioning differs sharply across databases. See the runnable examples under
`docs/examples/ar-migration/` — one directory per backend — and the user guide
in each. The short version:

| Backend | Partition model |
|---|---|
| SQLite / Firebird | No table partitioning — suggestions return "unsupported" |
| MySQL / MariaDB | Inline `PARTITION BY`, ADD/DROP/REORGANIZE |
| PostgreSQL | Separate child tables (`PARTITION OF`), DETACH→DROP, no split/merge |
| Oracle | Inline + INTERVAL/REFERENCE, DROP by name, SPLIT/MERGE |
| SQL Server | RANGE only; SPLIT/MERGE RANGE (data-affecting) |
| ClickHouse | `PARTITION BY <expr>` storage clause, no ADD, DROP PARTITION ID |

> Reading live partition state (`introspect partitions`) and capability probing
> are **backend CLI** concerns, not part of this API.

## 8. User-facing change planning API

Instead of assembling `plan_changes` / `resolve_suggestions` /
`suggest_partition_*_raw` yourself, the context offers two entry points that
return **frozen, dialect-neutral outcomes**:

- `ctx.plan_schema_change(old_model, new_model) -> SchemaChangeOutcome`
  composes the model-declaration diff with suggestion resolution. `statements`
  is the executable expression chain (one action per statement);
  `supported` / `unsupported` / `no_answer` / `missing` group **every** decision
  point by state, so `False` (explicitly unsupported), `None` (no answer) and a
  missing protocol are never silently dropped.
- `ctx.plan_partition_change(intent, strategy, plan) -> PartitionChangeOutcome`
  reads `dialect.partition_capability()` **first**, then decides whether to ask
  the backend at all. `capability` is one of `NATIVE` / `AUTOMATIC` /
  `UNSUPPORTED`:

  | Capability | `state` | `operations` | Meaning |
  |---|---|---|---|
  | `NATIVE` | `actions` / `no-action` / `unsupported` / `no-protocol` | expression tuple or `False` | Only this state consults `suggest_partition_*_raw` |
  | `AUTOMATIC` | `engine-managed` | `False` | The engine partitions and manages storage itself; there is **no partition DDL to target, so no DDL is fabricated** and no partition suggestion is called |
  | `UNSUPPORTED` | `not-supported` | `False` | No table partitioning at all; no partition suggestion is called |

Both `report()` methods return **text only** — what can be applied and why each
other point cannot — never SQL strings.

`ctx.apply_change(outcome, *, allow_incomplete=False, authorized_destructive=False)`
executes only the chain carried by the outcome:

- While any `unsupported` / `no_answer` / `missing` point remains (for a
  partition outcome, `operations is False`), execution is refused by default.
  Pass `allow_incomplete=True` when you intend to apply only the resolved part.
- A generic last-line guard refuses destructive DDL (`DropTableStatement`,
  `DropSchemaStatement`, `TruncateStatement`, `DeleteStatement`, plus rendered
  spellings such as `DROP TABLE` / `DELETE FROM`) and unpaired `SWITCH ... TO`
  data moves. Pass `authorized_destructive=True` only with explicit
  authorization. **One expression must carry exactly one action**; bundled
  statements are always refused. This is a generic backstop, not a replacement
  for the backend's own safety checks.

```python
def up(ctx):
    outcome = ctx.plan_schema_change(User20261124, User)
    print(outcome.report())            # text only, no SQL
    ctx.apply_change(outcome)          # raises while incomplete

    # Explicitly skip unresolved points:
    ctx.apply_change(outcome, allow_incomplete=True)

    part = ctx.plan_partition_change("add", strategy, plan)
    print(part.report())
    if part.capability.name == "NATIVE":
        ctx.apply_change(part)         # operations is False otherwise
```

`AsyncMigrationContext` mirrors every method; apply with
`await ctx.apply_change(outcome)`.
