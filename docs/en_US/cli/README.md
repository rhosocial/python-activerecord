# Model Command-Line Interface

`rhosocial-activerecord` is the **model** entry point. It is not the same
command as `rhosocial-activerecord-<backend>` (for example
`rhosocial-activerecord-sqlite`): the backend command executes SQL and
introspects the database, while this command operates on ActiveRecord model
classes through the framework APIs.

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
├── dml
│   ├── create
│   ├── update
│   ├── delete
│   └── bulk
│       ├── create
│       ├── update
│       └── delete
├── dql
│   ├── get
│   ├── list
│   ├── count
│   ├── exists
│   ├── aggregate
│   └── run
├── set
│   ├── union
│   ├── union-all
│   ├── intersect
│   ├── except
│   └── run
└── cte
    └── run
```

The CLI is a thin adapter: DML calls ActiveRecord methods, DQL calls
`ActiveQuery`, and `set` / `cte` execute user-supplied `SetOperationQuery` /
`CTEQuery` objects. It never builds SQL strings.

## Model references

A model reference is `module:Class`, not `module.Class`:

```bash
rhosocial-activerecord dql list --model app.models:User
```

The CLI adds the current directory and every `--path DIR` to `sys.path` before
importing the model. The class must be an `ActiveRecord` or
`AsyncActiveRecord` subclass.

## Backend and connection

The core package does not keep a registry of backends. Name the classes your
project actually uses:

- Backend class: `--backend-class MODULE:CLASS`, otherwise the model module's
  own `configure()` call.
- Connection config: `--connection MODULE:CALLABLE`, or
  `--config-class MODULE:CLASS` together with `--config KEY=VALUE`, otherwise
  the model module's own `configure()` call.

Class references accept either `module:Class` or the dotted `module.Class`
spelling. For an asynchronous model, name the asynchronous backend class.

```bash
# SQLite file, synchronous model
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --config-class rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig \
  --config database=app.db \
  --where "status=active" --order-by "created_at desc" --limit 20

# Named connection with an explicit backend class
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --connection app.connections:prod_db \
  -o json
```

If the model module already calls `configure()`, both `--backend-class` and
`--connection` / `--config-class` may be omitted. Any `--config` values then
override the model's existing configuration.

## DML

```bash
# Create one record
rhosocial-activerecord dml create --model app.models:User \
  --data '{"username": "alice", "email": "alice@example.com", "age": 30}'

# Update one record by primary key
rhosocial-activerecord dml update --model app.models:User --pk 42 \
  --data '{"age": 31}'

# Delete one record; non-interactive use needs --yes
rhosocial-activerecord dml delete --model app.models:User --pk 42 --yes
```

`--data` accepts inline JSON, `@file.json`, `@-` (stdin), or `-` (stdin).
`create` and `update` accept one JSON object; primary-key fields cannot be
updated through `update`.

Deletion asks for confirmation on a TTY. When stdin/stdout is not a terminal,
pass `--yes`; otherwise the command exits with code 5. If the model mixes in a
soft-delete behaviour, the output action is `soft_delete` instead of `delete`.
`--dry-run` reports what would happen without writing.

Read-only models (`ReadOnlyMixin`, `__read_only__ = True`) reject every DML
command before connecting, with exit code 6. DQL remains available.

### Bulk DML

```bash
# Create records from a JSON array
rhosocial-activerecord dml bulk create --model app.models:User \
  --data '[{"username": "a", "email": "a@example.com", "age": 20}, {"username": "b", "email": "b@example.com", "age": 30}]'

# JSONL from stdin
cat users.jsonl | rhosocial-activerecord dml bulk create --model app.models:User --data @-

# Update records; each object carries its primary key plus update fields
rhosocial-activerecord dml bulk update --model app.models:User \
  --data '[{"id": 1, "age": 21}, {"id": 2, "age": 31}]'

# Delete records by primary keys
rhosocial-activerecord dml bulk delete --model app.models:User \
  --data '[1, 2]' --yes
```

Bulk commands call `Model.bulk_create()` / `bulk_update()` / `bulk_delete()`,
so validation, events, transactions and soft delete keep their framework
semantics. `bulk update` requires every object to contain the same update field
set; `--update-fields` selects them explicitly. `--batch-size` splits create and
update work. `bulk delete` asks for the same confirmation as single delete.

## DQL

```bash
# Fetch by primary key
rhosocial-activerecord dql get --model app.models:User --pk 42

# Equality filters, sorting, pagination
rhosocial-activerecord dql list --model app.models:User \
  --where "status=active" --order-by "created_at desc" --limit 20 --offset 0

# Count and existence
rhosocial-activerecord dql count --model app.models:User --where "status=active" -o value
rhosocial-activerecord dql exists --model app.models:User --where "status=active" -o value

# Aggregate (grouped or scalar)
rhosocial-activerecord dql aggregate --model app.models:User \
  --fn count --field '*' --group-by status -o json
```

`dql list` injects a default limit of 100 when no limit is given and prints a
note on stderr. Use `--no-limit`, `--limit N`, `--offset N`, or
`--page N --page-size M` to control it.

`--select id,name` limits selected columns. `--include-deleted` and
`--only-deleted` call `query_with_deleted()` / `query_only_deleted()` when the
model supports soft delete.

`dql run` executes any `ActiveQuery` or derived query returned by a
`module:callable` or `module:Class.method` reference:

```python
# app/queries.py
from app.models import User

def active_users():
    return User.query().where(User.c.status == "active")
```

```bash
rhosocial-activerecord dql run --model app.models:User \
  --query app.queries:active_users -o json

# Or a model classmethod
rhosocial-activerecord dql run --model app.models:User \
  --query app.models:User.active_users -o json
```

`--mode list|one|count|exists|aggregate` chooses how the query is executed.
DQL is recognised by return type: `ActiveQuery` and subclasses, including
business wrappers and custom `__query_class__` methods that return `self`.

## Set operations and CTEs

Simple set operations use two model queries:

```bash
rhosocial-activerecord set union \
  --left-model app.models:User --right-model app.models:Admin \
  --left-where "status=active" --right-where "status=active" -o json
```

For composed queries, pass a factory returning an existing
`SetOperationQuery` / `CTEQuery`:

```bash
rhosocial-activerecord set run --model app.models:User \
  --query app.queries:active_users_union -o json

rhosocial-activerecord cte run --model app.models:User \
  --query app.queries:org_tree -o json
```

`SetOperationQuery` and `CTEQuery` return rows as dictionaries. The CLI calls
`aggregate()`; these types do not support `all()` or `limit()`.

## Output formats

`-o table|json|jsonl|csv|tsv|value`:

- `json`: array for lists, object for one record.
- `jsonl`: one JSON object per line, suitable for pipes.
- `csv` / `tsv`: rows with a header; `--no-header` omits it.
- `value`: a bare scalar for `count`, `exists`, or scalar aggregate.
- `table`: human Rich table; falls back to JSON when Rich is unavailable.

When stdout is not a TTY and `-o` is omitted, the default is `json`. Machine
formats write only data to stdout. `--quiet` suppresses informational stderr
messages such as the default-pagination note. `--fields id,name` limits output
columns.

## Pipes

```bash
cat user.json | rhosocial-activerecord dml create --model app.models:User --data @-

rhosocial-activerecord dql list --model app.models:User -o jsonl | jq -c 'select(.status == "active")'

rhosocial-activerecord dql count --model app.models:User -o value
```

A downstream pipe closing early (`| head`) is handled without a traceback and
exits with code 141.

## Examples

Runnable scripts for every command group live in
[`docs/examples/chapter_13_cli`](../../examples/chapter_13_cli/README.md).
They seed a temporary SQLite database and print the command, its stdout,
stderr, and exit code.

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
| 4 | A backend or connection config class cannot be imported |
| 5 | Destructive command needs `--yes` in a non-interactive context |
| 6 | DML refused on a read-only model |
| 141 | Downstream pipe closed |

## Sync and async models

The CLI detects the model type automatically. `ActiveRecord` uses the
synchronous backend; `AsyncActiveRecord` uses the asynchronous backend and an
event loop inside the CLI. There is no `--async` flag, but `--backend-class`
must name a class that matches the model: an `AsyncStorageBackend` subclass for
an asynchronous model, a `StorageBackend` subclass otherwise.

## Python module form

```bash
python -m rhosocial.activerecord.cli dql list --model app.models:User -o json
```
