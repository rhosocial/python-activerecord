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
