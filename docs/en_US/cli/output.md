# Output, pipes, and exit codes

Machine formats write only data to stdout. Notes, logs, and errors always go to
stderr, so a payload can be piped or captured without filtering.

## Formats

`-o table|json|jsonl|csv|tsv|value`:

| Format | Use |
|--------|-----|
| `json` | Array for lists, object for one record, scalar for counts |
| `jsonl` | One JSON value per line; ideal for pipes and streaming |
| `csv` / `tsv` | A header row plus data rows; `--no-header` omits the header |
| `value` | A bare scalar for `count`, `exists`, or a scalar aggregate |
| `table` | Human-readable Rich table; falls back to JSON without Rich |

When stdout is not a TTY and `-o` is omitted, the default is `json`. On a TTY the
default is `table`.

`--fields id,name` limits the output columns. For list results the names are
validated against the model (or the dictionary keys); an unknown name lists the
available fields. `--fields` on a scalar result is ignored.

`-o value` is only valid for scalar results. Passing it to a list or a single
record exits 1 with `Error: -o value is only valid for scalar results`.

## Write results

DML delete and bulk update/delete return summary objects:

| Command | JSON | CSV/TSV columns |
|---------|------|-----------------|
| `dml delete` | `{"action", "pk", "affected"}` (+ `deleted_at_field`, `dry_run`) | `action,pk,affected` (+ extras) |
| `dml bulk update` | `{"action", "affected"}` | `action,affected` |
| `dml bulk delete` | `{"action", "affected"}` | `action,affected` |

`-o value` prints only the affected count for these commands. `dml bulk create`
and `dml create` return the created records, so `json` / `jsonl` / `csv` / `tsv`
describe rows, not an envelope.

## Pipes

```bash
cat user.json | rhosocial-activerecord dml create --model app.models:User --data @-

rhosocial-activerecord dql list --model app.models:User -o jsonl \
  | jq -c 'select(.status == "active")'

rhosocial-activerecord dql count --model app.models:User -o value
```

- `--data @-` and `--data -` read stdin.
- A downstream pipe closing early (for example `| head`) is handled without a
  traceback and exits with code 141.
- JSONL is the safest format for long pipelines: each line is a complete value.

## Logging and notes

- The default framework log level is `WARNING`; logs go to stderr.
- `--log-level DEBUG` prints backend and model detail useful for diagnosing a
  connection or model-loading problem.
- `--quiet` suppresses informational stderr such as the automatic-pagination
  note. It does not suppress errors.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success, including a declined confirmation |
| 1 | Model, connection, validation, or database error |
| 2 | Command-line usage error (argparse) |
| 3 | Record not found |
| 4 | A backend or connection config class cannot be imported |
| 5 | Destructive command needs `--yes` in a non-interactive context |
| 6 | DML refused on a read-only model |
| 141 | Downstream pipe closed |

## Using these commands from an AI agent

- Default to `-o json` (or `jsonl` for streams). Never parse `table` output.
- stdout is payload-only; treat any text on stderr as diagnostics, not data.
- Handle 141 explicitly: it means the consumer stopped reading, not that the
  command failed.
- Use `--fields` to keep payloads small and stable when the model has many
  columns.
- Use `--quiet` together with `-o json` when you capture stderr for logs; the
  pagination note is informational and safe to drop.
