# Errors and validation

The CLI translates model and backend exceptions into command-level errors. It
never changes framework semantics: models still validate when constructed, and
`save()` still re-validates business rules.

## Message and exit code mapping

| Situation | Message starts with | Exit code |
|---|---|---|
| Invalid record data | `Invalid data for Model ...` | 1 |
| Constraint conflict | `Integrity constraint failed ...` | 1 |
| Record not found | `Model with pk=... was not found` | 3 |
| Read-only model | `... is read-only ...` | 6 |
| Confirmation required | `... Pass --yes ...` | 5 |
| Version conflict | `Record version mismatch ...` | 1 |
| Lock or deadlock | `Record is locked ...` / `Deadlock detected ...` | 1 |
| Connection failure | `Database connection failed ...` | 1 |
| Other database error | `Database error ...` | 1 |
| Missing backend or config class | `Cannot import the ...` | 4 |
| Unknown failure | `Unexpected error (TypeName): ...` | 1 |

Please see [Output and pipes](output.md#exit-codes) for the complete code list.

## Model exceptions versus CLI errors

The model layer raises `backend.errors.RecordNotFound` when a query returns no
row. The CLI raises its own `CliNotFoundError` and maps it to exit code 3. They
stay separate classes on purpose:

- `RecordNotFound` describes a query result and carries no exit code.
- `CliNotFoundError` describes a command outcome.

Command handlers translate with `raise ... from exc`, so the original exception
stays available in the chain for debugging.

## Validation

Validation happens at two points:

1. When the model instance is constructed (`dml create`, `bulk create`, and the
   data loaded by `dml update`).
2. Inside `save()`: `model_validate(model_dump())` plus `validate_record()`,
   which runs business rules.

A failure writes nothing and exits 1. For `dml update` the message names the
model and primary key:

```text
Error: Invalid data for User pk=42: age: Input should be less than or equal to 100
```

For bulk operations the message names the item (and the primary key when it is
known):

```text
Error: Invalid data for User (item 2): name: String should have at least 2 characters
Error: Bulk update failed at item 2 (pk=2): age: Input should be <= 100
```

Bulk commands validate the whole batch before issuing SQL, so a failed batch
leaves the table untouched.

## Cancellation

Declining a confirmation is not an error:

- exit code 0;
- stderr shows `Operation cancelled.` without the `Error:` prefix;
- nothing is written.

In a non-interactive context the CLI never prompts: a destructive command without
`--yes` exits 5 with a message asking for `--yes`.

## Unexpected failures

Known exceptions are mapped as above. Anything else prints one line:

```text
Unexpected error (ValueError): ...
```

No traceback is printed. Run with `--log-level DEBUG` to get the full traceback
in the log stream (stderr).

## Using these commands from an AI agent

- Branch on exit codes: 3 means "not found", 5 means "confirmation required",
  6 means "read-only", 4 means "bad import path", 1 is a general failure.
- Distinguish `RecordNotFound` (model layer) from `CliNotFoundError` when reading
  library code: the CLI error is what a command returns.
- A validation failure guarantees no write; do not issue compensating deletes.
- Capture stderr separately. Error lines start with `Error:` (or `Unexpected
  error (...)` for unknown failures) and are not valid JSON.
- Re-run with `--log-level DEBUG` only when diagnosing; it produces verbose
  output on stderr.
