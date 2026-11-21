# ActiveRecord-layer migration examples — core (SQLite)

Runnable examples for the **ActiveRecord-layer migration API**
(`rhosocial.activerecord.migration`) using the built-in SQLite backend. No server
needed — each script uses a temporary database.

Run from the repository root with `PYTHONPATH=src;tests`:

```bash
python docs/examples/ar-migration/core/01_hello_migration.py
python docs/examples/ar-migration/core/02_add_drop_column.py
python docs/examples/ar-migration/core/03_backfill_not_null.py
python docs/examples/ar-migration/core/04_dry_run_and_rollback.py
```

| Script | Scenario |
|---|---|
| `01_hello_migration.py` | Declare `up`/`down`, dry-run, apply, roll back — the full loop |
| `02_add_drop_column.py` | Add/drop a column — single action, no backend suggestion needed |
| `03_backfill_not_null.py` | Add a nullable column + backfill (multi-step DDL + DML) |
| `04_dry_run_and_rollback.py` | dry-run, DOWN reversal, dependency/guard validation |

> This is the **AR-layer** migration system (up/down + suggestions + dry-run),
> distinct from `docs/examples/migration/` which demonstrates the backend
> `migrate` command. See `../README.md` for backend-specific (partition) examples.
