# DML: single-record writes

`dml create`, `dml update`, and `dml delete` operate on exactly one record.
They call the model's own `save()` / `delete()` methods, so events, timestamps,
optimistic locking, soft delete, and validation keep their framework behaviour.

## Create

```bash
rhosocial-activerecord dml create --model app.models:User \
  --data '{"name": "Alice", "email": "alice@example.com", "age": 30}' -o json
```

`--data` accepts:

| Form | Meaning |
|------|---------|
| `'{"k": "v"}'` | inline JSON object |
| `@user.json` | read from a file |
| `@-` or `-` | read stdin |

The payload must be one JSON object. Validation runs when the model instance is
constructed, and again inside `save()` for business rules. A failure writes
nothing and exits 1. See [Errors](errors.md#validation).

## Update

```bash
rhosocial-activerecord dml update --model app.models:User \
  --pk 42 --data '{"age": 31}' -o json
```

- `--pk` is the primary-key value; composite keys use a JSON object
  (`--pk '{"order_id": 1, "product_id": 101}'`, or `--pk-json`).
- Primary-key fields cannot be updated. Delete the record and create a new one
  instead; the command refuses before issuing SQL.
- Only the supplied fields change; the record is loaded first.

## Delete

```bash
rhosocial-activerecord dml delete --model app.models:User --pk 42 --yes -o json
```

Deletion asks for confirmation on a TTY. When stdin or stdout is not a terminal,
pass `--yes`; otherwise the command exits with code 5. `--dry-run` reports what
would happen without writing:

```bash
rhosocial-activerecord dml delete --model app.models:User --pk 42 --yes --dry-run
```

Output:

```json
{"action": "delete", "pk": 42, "affected": 1, "dry_run": true}
```

For a soft-delete model the action is `soft_delete` and the payload names the
timestamp field:

```json
{"action": "soft_delete", "pk": 42, "affected": 1, "deleted_at_field": "deleted_at"}
```

## Read-only models

A model that declares `__read_only__ = True` (for example through
`ReadOnlyMixin`) rejects every DML command before connecting, with exit code 6:

```text
Error: ReadOnlyUser is read-only (__read_only__ = True); 'dml create' is not allowed.
```

DQL remains available for read-only models.

## Using these commands from an AI agent

- Always pass `--yes` to `dml delete`; a prompt is a blocking failure for an
  agent.
- Call `--dry-run` first when the goal is to verify the target row and action
  (`delete` vs `soft_delete`).
- `dml update` is not idempotent in the presence of concurrent writers: a
  version conflict raises `StaleRecordError` and exits 1. Re-read with
  `dql get`, then retry.
- Use `-o json` and check the `action` field rather than assuming a physical
  delete: soft-delete models keep the row.
- A missing primary key exits 3 and writes nothing. Treat 3 as "the row does
  not exist", not as an infrastructure failure.
