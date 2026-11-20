# Migration Examples

Runnable examples for the backend migration system (see the
[Migration System](../../en_US/migration/README.md) chapter). All use a temporary SQLite database —
no server or credentials needed. Run them from the repository root with
`PYTHONPATH=src;tests`:

```bash
python docs/examples/migration/01_first_migration.py
python docs/examples/migration/02_dependency_chain.py
python docs/examples/migration/03_cli_migrate.py
```

| Script | Demonstrates |
|---|---|
| `01_first_migration.py` | `@migration` classmethod + `ctx.apply()`; dry run → UP → DOWN with a `JSONFileMigrationRecordStore` |
| `02_dependency_chain.py` | caller-defined order (no auto-sort), dependency validation, duplicate-version errors |
| `03_cli_migrate.py` | the `migrate` CLI: `--list`, `--plan`, `--dry-run`, real UP, `--direction down -o json` |
| `migration_models.py` | importable model + migration function used by `03_cli_migrate.py` (the CLI resolves them by FQN) |

> Note: the class-style (`NamedMigration`) system has its own longer-running demos under
> `src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/`.
