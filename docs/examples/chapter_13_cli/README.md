# CLI examples

Runnable examples for the model command-line interface documented in
[`docs/en_US/cli/README.md`](../../en_US/cli/README.md) and
[`docs/zh_CN/cli/README.md`](../../zh_CN/cli/README.md).

Each script seeds a temporary SQLite database, runs real CLI commands, and
prints the command, its stdout/stderr, and the exit code.

## Prerequisites

Install the package from the repository root:

```bash
pip install -e .
```

The scripts also work from a source checkout without installation, because
`cli_runner.py` adds `src/` to `PYTHONPATH` when it exists.

## Scripts

| Script | Shows |
|--------|-------|
| [`01_dml.py`](01_dml.py) | `dml create/update/delete`, `--dry-run`, not-found exit code 3, read-only exit code 6, `soft_delete` label |
| [`02_dql.py`](02_dql.py) | `dql get/list/count/exists/aggregate/run`, default pagination, `--no-limit` |
| [`03_bulk_dml.py`](03_bulk_dml.py) | `dml bulk create/update/delete`, JSON and JSONL input, `--batch-size`, `--update-fields` |
| [`04_set_cte.py`](04_set_cte.py) | `set union/intersect/except`, `set run` and `cte run` factories |
| [`05_output_and_pipes.py`](05_output_and_pipes.py) | `json/jsonl/csv/tsv/table/value`, `--fields`, `--no-header`, `--quiet`, stdin input |

Run one at a time:

```bash
python docs/examples/chapter_13_cli/01_dml.py
```

## Shared pieces

- `models.py` defines `User`, `Admin`, `ReadOnlyUser`, and the soft-delete
  `Task` model, plus the query factories used by `dql run`, `set run`, and
  `cte run`.
- `cli_runner.py` builds the command (`python -m rhosocial.activerecord.cli`),
  adds the model search path, and passes the SQLite backend and config classes.

The examples never call `configure()` inside `models.py`; they pass
`--backend-class`, `--config-class`, and `--config database=...` instead, which
is the pattern for projects that keep configuration outside the model module.

Printed commands shorten the class references and paths for readability; the
executed command always uses the full values.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Model, connection, validation, or database error |
| 2 | Command-line usage error |
| 3 | Record not found |
| 4 | Backend or config class cannot be imported |
| 5 | Destructive command needs `--yes` in a non-interactive context |
| 6 | DML refused on a read-only model |
| 141 | Downstream pipe closed |
