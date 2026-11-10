# DQL: queries, pagination, and aggregates

`dql` calls `ActiveQuery` methods directly. There is no second filter language:
the CLI maps simple options onto `where()`, `order_by()`, `select()`, `limit()`,
and `offset()`.

## Commands

| Command | Purpose |
|---------|---------|
| `dql get` | One record by primary key |
| `dql list` | Filtered, sorted, paginated records |
| `dql count` | Number of matching records |
| `dql exists` | Whether any record matches |
| `dql aggregate` | Scalar or grouped aggregate |
| `dql run` | Execute a user-supplied `ActiveQuery` |

## Filters

```bash
rhosocial-activerecord dql list --model app.models:User \
  --where "status=active" --where "age=30" \
  --order-by "created_at desc" --order-by "id asc" \
  --select id,name --limit 20 --offset 0 -o json
```

- `--where` supports **equality only**: `field=value`. Clauses may be repeated
  and are ANDed. Values are converted to the field type.
- Unknown fields are rejected before SQL runs, and the message lists the
  available fields.
- `--order-by` accepts `field` or `field asc|desc`.
- `--select` limits the selected columns and validates the names.
- For comparisons (`>=`, `LIKE`, `IN`, …) use [`dql run`](#run-your-own-query)
  with a Python factory.

Soft-delete models add two visibility flags:

```bash
rhosocial-activerecord dql list --model app.models:Task --include-deleted
rhosocial-activerecord dql list --model app.models:Task --only-deleted
```

They call `query_with_deleted()` / `query_only_deleted()` and are mutually
exclusive.

## Pagination

`dql list`, `dql aggregate` with `--group-by`, and `dql run --mode list|aggregate`
apply pagination. `dql get`, `dql count`, `dql exists`, and `dql run --mode
one|count|exists` do not.

Options:

| Option | Effect |
|--------|--------|
| `--limit N` | At most `N` rows |
| `--offset N` | Skip `N` rows |
| `--page N --page-size M` | Equivalent to `limit M offset (N-1)*M`; both required, both positive |
| `--no-limit` | Disable automatic injection |
| `--limit 0` | Also disables the limit (no pagination) |
| `--quiet` | Suppress the automatic-pagination note |

### Automatic injection

When a paginating command has no explicit limit and the query itself carries no
limit, the CLI injects `DEFAULT_LIST_LIMIT` (100) and explains it on stderr:

```text
Showing first 100 rows (default pagination); use --limit N or --no-limit to change.
```

For grouped aggregates the label changes:

```text
Showing first 100 groups (default pagination); use --limit N or --no-limit to change.
```

The note goes to **stderr only**; stdout stays machine-readable. `--quiet`
removes the note. `--no-limit` (a guard against accidentally loading an entire
table) keeps the query unbounded.

Scalar aggregates are never paginated: `dql aggregate --fn count` runs a
`COUNT(*)` and returns one value.

## Count and existence

```bash
rhosocial-activerecord dql count --model app.models:User --where "status=active" -o value
rhosocial-activerecord dql exists --model app.models:User --where "status=active" -o value
```

`-o value` prints `4` or `true` / `false`; `-o json` prints a JSON scalar.

## Aggregates

```bash
# Scalar: one value
rhosocial-activerecord dql aggregate --model app.models:Order \
  --fn sum --field total -o value

# Grouped: one row per group
rhosocial-activerecord dql aggregate --model app.models:Order \
  --fn count --field '*' --group-by status -o json
```

- `--fn` is one of `count`, `sum`, `avg`, `min`, `max`.
- `--field '*'` is only valid for `count`.
- `--field` must name a model field; unknown names are rejected before SQL runs.
- `--group-by` may be repeated; each name is validated.
- `--distinct` applies `DISTINCT` inside the aggregate.
- A grouped aggregate returns dictionary rows; a scalar aggregate returns one
  value.

Empty grouped results cannot be used to infer columns. Pass `--fields` when the
result may be empty, otherwise the command reports:

```text
Error: The query returned no rows, so output fields cannot be inferred. Pass --fields explicitly.
```

## Run your own query

`dql run` executes an `ActiveQuery` (or subclass) returned by a
`module:callable` or `module:Class.method` reference:

```python
# app/queries.py
from app.models import User

def active_users():
    return User.query().where(User.c.age >= 30).order_by(User.c.age.desc())
```

```bash
rhosocial-activerecord dql run --model app.models:User \
  --query app.queries:active_users -o json

# A model classmethod that returns a query
rhosocial-activerecord dql run --model app.models:User \
  --query app.models:User.active_users -o json
```

- The factory is called **without arguments**.
- The return value must be an `ActiveQuery` or subclass, including business
  wrappers and `__query_class__` methods that return `self`. Anything else is
  rejected with a message naming the expected type.
- `--mode` selects how the query is executed:

| Mode | Equivalent call |
|------|----------------|
| `list` (default) | `all()` |
| `one` | `one()`; a missing row exits 3 |
| `count` | `count()` |
| `exists` | `exists()` |
| `aggregate` | `aggregate()`; returns dictionary rows |

- `list` and `aggregate` modes apply pagination (including automatic injection).
- `one`, `count`, and `exists` ignore pagination options.

## Using these commands from an AI agent

- `--where` is equality-only. Do not try `age>=30`; generate a query factory and
  call `dql run` instead.
- Automatic pagination is silent on stdout and loud on stderr. Default to
  `--limit N` (or `--no-limit`) so the result size is explicit, and pass
  `--quiet` to drop the note if you parse stderr.
- Use `dql count` before a large `dql list` to estimate cost.
- Ask for `-o jsonl` when piping row-by-row into another tool.
- `dql run` factories are imported from `--path` directories; write the factory
  in the project rather than trying to express complex predicates as strings.
- When a grouped aggregate may be empty, pass `--fields` to avoid the
  field-inference error.
