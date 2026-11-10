# Bulk DML

Bulk commands call `Model.bulk_create()`, `bulk_update()`, and `bulk_delete()`.
Validation, events, transactions, batching, and soft delete keep their
framework semantics; the CLI only parses the payload.

## Input

`--data` accepts a JSON array, a single object, an `@file`, stdin (`@-` / `-`),
and JSONL (one object per line). `--input-format json|jsonl` forces the parser
when auto-detection is ambiguous:

```bash
# JSON array
rhosocial-activerecord dml bulk create --model app.models:User \
  --data '[{"name": "A"}, {"name": "B"}]' -o json

# JSONL from stdin
cat users.jsonl | rhosocial-activerecord dml bulk create --model app.models:User \
  --data @- --input-format jsonl -o json
```

Auto-detection reads the first non-space character: `[` means a JSON array,
`{` means one object or a JSONL stream, anything else is parsed as JSONL.

## Bulk create

```bash
rhosocial-activerecord dml bulk create --model app.models:User \
  --data '[{"name": "Grace", "age": 26}, {"name": "Heidi", "age": 33}]' \
  --batch-size 2 -o json
```

- Output is the list of created records, in input order.
- `--batch-size N` splits the work into batches of `N` records.
- A validation failure names the item:

```text
Error: Invalid data for User (item 2): name: String should have at least 2 characters
```

Nothing is written when any item fails validation.

## Bulk update

```bash
rhosocial-activerecord dml bulk update --model app.models:User \
  --data '[{"id": 1, "age": 31}, {"id": 2, "age": 26}]' \
  --update-fields age -o json
```

- Every object must carry its primary key plus the update fields.
- Without `--update-fields`, every object must contain the same non-key field
  set; otherwise the command refuses and asks for `--update-fields`.
- `--update-fields a,b` selects the fields explicitly and is validated against
  the model fields before any SQL runs.
- A missing record fails the whole batch with the item index and primary key:

```text
Error: User bulk update item 2 with pk=2 was not found
```

- A validation failure names the item and primary key:

```text
Error: Bulk update failed at item 2 (pk=2): age: Input should be <= 100
```

- Output: `{"action": "update", "affected": 2}`.

## Bulk delete

```bash
rhosocial-activerecord dml bulk delete --model app.models:User \
  --data '[1, 2]' --yes -o json
```

- `--data` holds primary keys: scalars, JSON objects for composite keys, or
  JSONL.
- Confirmation uses the same rules as single delete: `--yes` is required when
  non-interactive, `--dry-run` previews.
- Soft-delete models report `soft_delete`.

## Output shape

| Command | JSON output |
|---------|-------------|
| `bulk create` | array of created records |
| `bulk update` | `{"action": "update", "affected": N}` |
| `bulk delete` | `{"action": "delete"\|"soft_delete", "affected": N}` |

`-o csv` / `-o tsv` render the summary rows with a header (`action,affected`);
`--no-header` omits the header. `-o value` prints only the affected count for
update and delete.

## Using these commands from an AI agent

- Chunk large payloads with `--batch-size` (for example 100–500 rows) instead of
  sending one enormous array; the CLI keeps framework validation per batch.
- Prefer `-o json` for create (the created rows carry database-generated keys)
  and `-o value` for update/delete when only the affected count matters.
- Payloads are validated before SQL, so a failure means "nothing was written";
  do not attempt compensating deletes.
- Every object in `bulk update` needs the same fields. If your data is ragged,
  pass `--update-fields` explicitly.
- Feed JSONL through stdin to avoid command-line length limits on large batches.
