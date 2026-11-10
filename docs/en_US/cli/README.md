# Model Command-Line Interface

`rhosocial-activerecord` is the **model** entry point. It is not the same
command as `rhosocial-activerecord-<backend>` (for example
`rhosocial-activerecord-sqlite`): the backend command executes SQL and
introspects the database, while this command operates on ActiveRecord model
classes through the framework APIs.

The CLI is a thin adapter. It never builds SQL strings: DML calls ActiveRecord
methods, DQL calls `ActiveQuery`, and `set` / `cte` execute user-supplied
`SetOperationQuery` / `CTEQuery` objects.

## Pages

| Page | Contents |
|------|----------|
| [DML](dml.md) | `dml create/update/delete`, dry runs, soft delete, read-only models |
| [Bulk DML](bulk.md) | `dml bulk create/update/delete`, JSON and JSONL input, batching |
| [DQL](dql.md) | `dql get/list/count/exists/aggregate/run`, filters, pagination, aggregates |
| [Set operations and CTEs](set-cte.md) | `set union/union-all/intersect/except`, `set run`, `cte run` |
| [Connections](connections.md) | Model references, backend/config classes, named connections, async models |
| [Output and pipes](output.md) | Formats, fields, pipes, logging, exit codes |
| [Errors](errors.md) | Exception mapping, validation semantics, cancellation |

Runnable examples live in
[`docs/examples/chapter_13_cli`](../../examples/chapter_13_cli/README.md).

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

## Feature summary

| Command | Purpose | Main options | Typical output |
|---------|---------|--------------|----------------|
| `dml create` | Insert one record | `--data` | the created record |
| `dml update` | Update one record by primary key | `--pk`, `--data` | the updated record |
| `dml delete` | Delete one record | `--pk`, `--yes`, `--dry-run` | `action`, `pk`, `affected` |
| `dml bulk create` | Insert many records | `--data`, `--input-format`, `--batch-size` | created records |
| `dml bulk update` | Update many records | `--data`, `--update-fields`, `--batch-size` | `action`, `affected` |
| `dml bulk delete` | Delete many records by primary key | `--data`, `--yes`, `--dry-run` | `action`, `affected` |
| `dql get` | Fetch one record by primary key | `--pk` | one record |
| `dql list` | Filter, sort, and page records | `--where`, `--order-by`, `--select`, pagination | records |
| `dql count` | Count matching records | `--where` | scalar |
| `dql exists` | Test whether any record matches | `--where` | scalar |
| `dql aggregate` | Scalar or grouped aggregate | `--fn`, `--field`, `--group-by`, `--distinct` | scalar or rows |
| `dql run` | Execute a user-supplied `ActiveQuery` | `--query`, `--mode` | depends on `--mode` |
| `set union` etc. | Combine two model queries | `--left-model`, `--right-model`, `--left-where`, `--right-where` | rows |
| `set run` | Execute a user-supplied `SetOperationQuery` | `--query` | rows |
| `cte run` | Execute a user-supplied `CTEQuery` | `--query` | rows |

Rules that apply to every command:

- stdout carries data only; notes, logs, and errors go to stderr.
- `-o` defaults to `table` on a TTY and `json` otherwise.
- Exit codes are stable; see [Output and pipes](output.md#exit-codes).
- Destructive commands never prompt in a non-interactive context; they fail
  with exit code 5 unless `--yes` is given.

## Quick start

```bash
# One record
rhosocial-activerecord dml create \
  --model app.models:User \
  --backend-class mypkg.backend:MyBackend \
  --config-class mypkg.config:MyConnectionConfig \
  --config database=app.db \
  --data '{"name": "Alice", "age": 30}' -o json

# Filtered list
rhosocial-activerecord dql list \
  --model app.models:User \
  --where "status=active" --order-by "created_at desc" --limit 20 -o json

# Count as a bare value
rhosocial-activerecord dql count --model app.models:User -o value
```

The connection flags are only needed when the model module does not call
`configure()` itself. See [Connections](connections.md).

## Using these commands from an AI agent

- Prefer `-o json` or `-o jsonl`: the payload is parseable and never mixed with
  log lines.
- Always pass `--yes` to destructive commands; prompts would block the agent.
- Branch on exit codes, not on message text. The codes are stable; messages are
  meant for humans.
- Prefer `dql run` with a small Python query factory when `--where` is not
  expressive enough: it avoids shell-quoting complex predicates.
- Read the per-page "Using these commands from an AI agent" section for
  command-specific advice.
