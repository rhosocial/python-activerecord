# ActiveRecord-layer migration — examples index

ActiveRecord's own migration capability: users write `up(ctx)` / `down(ctx)`
logic; the framework manages ordering, execution, dry-run and version records.
When an operation's "how-to" differs irreconcilably across databases, the user
asks the backend for a **suggestion** (`ctx.suggest_partition_*`); otherwise a
single portable expression suffices.

> This is distinct from `docs/examples/migration/` (the backend `migrate`
> command). See the user guide at
> `docs/en_US/migration/ar-migration-guide.md` for the full story.

## Layout

| Directory | Contents |
|---|---|
| `core/` | Portable examples runnable on built-in SQLite (no server) |
| `mysql/`, `mariadb/` | Inline `PARTITION BY`, ADD/DROP/REORGANIZE, DROP-by-... |
| `postgres/` | `CREATE TABLE ... PARTITION OF`, `DETACH CONCURRENTLY`, no split/merge |
| `oracle/` | RANGE/LIST/HASH/INTERVAL/REFERENCE, DROP by name, SPLIT/MERGE |
| `sqlserver/` | SPLIT/MERGE RANGE (data-affecting), function→scheme→ON |
| `clickhouse/` | `PARTITION BY <expr>`, no ADD (appears with first row), DROP PARTITION ID |
| `firebird/` | Explicit-unsupported path (no table partitioning) |

## Running

- `core/` examples run for real on a temporary SQLite database:
  `python docs/examples/ar-migration/core/NN_*.py` with `PYTHONPATH=src;tests`.
- Backend-specific examples render SQL **offline** (no live server): construct a
  dialect + plan, ask for a suggestion, print `expr.to_sql()`. They demonstrate
  how the same intent produces different SQL on each database.

## Scenario → example map

| Scenario | Core | Backend-specific |
|---|---|---|
| First migration / dry-run / rollback | `core/01` | — |
| Add / drop column | `core/02` | — |
| Backfill NOT NULL | `core/03` | — |
| Management & guards | `core/04` | — |
| Build a partitioned table | — | per-backend `01_partition_build` |
| Add / drop partition | — | per-backend lifecycle script |
| Split / merge / retention | — | per-backend lifecycle script |
