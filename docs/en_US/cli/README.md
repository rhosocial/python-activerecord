# Model CRUD Command-Line Interface

`rhosocial-activerecord` is the model CRUD entry point. It is **not** the same
command as `rhosocial-activerecord-<backend>` (for example
`rhosocial-activerecord-sqlite`): the backend command executes SQL and introspects
the database, while this command operates on an ActiveRecord model class.

## Installation

The CLI ships with the core package. `table` output needs the optional `[cli]`
extra:

```bash
pip install "rhosocial-activerecord[cli]"
```

Without `rich`, `-o table` falls back to JSON instead of failing.

## Command tree

```text
rhosocial-activerecord
└── crud
    ├── get      --model ... --pk ...
    ├── list     --model ... [--where ...] [--order-by ...] [--limit N] [--offset N]
    ├── create   --model ... --data JSON|@file|@-
    ├── update   --model ... --pk ... --data JSON|@file|@-
    └── delete   --model ... --pk ...
```

A model reference is `module:Class`, not `module.Class`:

```bash
rhosocial-activerecord crud list --model app.models:User
```

The CLI adds the current directory and every `--path DIR` to `sys.path` before
importing the model. The model class must be an `ActiveRecord` or
`AsyncActiveRecord` subclass.

## Backend and connection

Resolution order:

1. `--connection module:callable` — the callable returns a `ConnectionConfig`.
2. `--backend` plus connection flags (`--database`, `--host`, `--port`,
   `--user`, `--password`, `--option KEY=VALUE`).
3. The model module's own `configure()` call, when no CLI connection is given.

Built-in backend names: `sqlite`, `mysql`, `mariadb`, `postgres`, `sqlserver`,
`oracle`, `firebird`, `snowflake`, `clickhouse`, `bigquery`. SQLite ships in the
core package; the others are installed separately, for example:

```bash
pip install rhosocial-activerecord-postgres
```

A missing backend package exits with code 4 and prints that install command.

Examples:

```bash
# SQLite file
rhosocial-activerecord crud list \
  --model app.models:User \
  --backend sqlite --database app.db \
  --where "status=active" --order-by "created_at desc" --limit 20

# Named connection, backend inferred from the config type
rhosocial-activerecord crud list \
  --model app.models:User \
  --connection app.connections:prod_db \
  -o json
```

`--option KEY=VALUE` sets a config field when the field exists, otherwise it is
placed in `config.options`. Passwords are never written to logs; prefer a named
connection or environment variables for production credentials.

## CRUD semantics

| Command | Required | Behaviour |
|---------|----------|-----------|
| `get` | `--pk` | Fetch one record by primary key. Missing record exits with 3. |
| `list` | — | Equality filters, sorting, limit, offset. Default limit is 100; `--limit 0` means unlimited. |
| `create` | `--data` | Build and save a record; Pydantic validates the data. |
| `update` | `--pk`, `--data` | Load the record, apply only the given fields, save. Primary-key fields are rejected. |
| `delete` | `--pk` | Load and delete the record; soft-delete mixins still apply. |

`update` and `delete` only work by primary key. There is no bulk update or delete
mode in v1.

`--data` accepts inline JSON, `@file.json`, or `@-` for stdin. It must be a JSON
object.

Primary keys:

```bash
# Single column
--pk 42

# Composite key
--pk '{"order_id": 1, "product_id": 101}'
```

`--where` accepts equality only and may be repeated; repeated clauses are ANDed.
`--order-by` accepts `field` or `field asc|desc` and may be repeated.

## Output formats

`-o table|json|csv|tsv`:

| Format | `list` | `get` / `create` / `update` | `delete` |
|--------|--------|------------------------------|----------|
| `json` | array | object | `{"deleted": N, "pk": ...}` |
| `csv` / `tsv` | header + rows | header + one row | one summary row |
| `table` | Rich table | Rich vertical table | Rich panel |

`--fields id,name` limits the output columns. `--rich-ascii` switches table
borders to ASCII.

Machine formats write **only data** to stdout. Logs and errors go to stderr, so
`-o json` output can be piped straight into `jq`.

## Logging

The default framework log level is `WARNING`. Use `--log-level DEBUG` when
diagnosing a connection or model problem. Logs always go to stderr.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Model, connection, validation, or database error |
| 2 | Command-line usage error (argparse) |
| 3 | Record not found |
| 4 | Backend package missing or unknown backend |

## Sync and async models

The CLI detects the model type automatically. `ActiveRecord` uses the synchronous
backend; `AsyncActiveRecord` uses the asynchronous backend and an event loop
inside the CLI. There is no `--async` flag.

## Python module form

The same entry point is available without installing a console script:

```bash
python -m rhosocial.activerecord.cli crud list --model app.models:User -o json
```
