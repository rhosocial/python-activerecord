# Set operations and CTEs

`set` and `cte` execute existing `SetOperationQuery` / `CTEQuery` objects.
There are two ways to use them:

1. **Simple arms** (`set union`, `union-all`, `intersect`, `except`) combine two
   model queries built from CLI options.
2. **Composed queries** (`set run`, `cte run`) execute a factory that returns
   the query object, which covers CTEs, multiple arms, and custom predicates.

## Simple set operations

```bash
rhosocial-activerecord set union \
  --left-model app.models:User --right-model app.models:Admin \
  --left-where "status=active" --right-where "status=active" -o json
```

- `--left-model` / `--right-model` are required and must both be synchronous or
  both asynchronous.
- `--left-where` / `--right-where` use the same equality-only `field=value`
  syntax as `dql list`; `--order-by` and `--select` apply to both arms.
- `--limit`, `--offset`, and `--page/--page-size` are applied to each arm. There
  is **no automatic default pagination** for set arms.
- `union-all` maps to `UNION ALL`; `intersect` / `except` need backend support.

Rows come back as dictionaries, because a set operation is not tied to one model
class. Output formatting rules are the same as for plain query rows.

## Composed queries

```python
# app/queries.py
from app.models import Admin, User

def active_users_union():
    return User.query().where(User.c.status == "active").union(
        Admin.query().where(Admin.c.status == "active")
    )
```

```bash
rhosocial-activerecord set run --model app.models:User \
  --query app.queries:active_users_union -o json
```

- `--model` is optional for `set run` / `cte run`: pass it when the factory
  needs the model to be configured, omit it when the factory configures its own
  connection.
- The factory is called without arguments and must return a `SetOperationQuery`
  (`set run`) or `CTEQuery` (`cte run`); a plain `ActiveQuery` is rejected with
  a message naming the expected type.
- These commands call `aggregate()`. `SetOperationQuery` and `CTEQuery` rows are
  dictionaries; they do not support `all()` or `limit()`.
- `set run` and `cte run` do not add pagination. Put limits inside the query
  when needed.

## CTEs

```python
# app/queries.py
from rhosocial.activerecord.query import CTEQuery
from app.models import User

def older_users():
    cte = CTEQuery(User.backend())
    cte.with_cte("older_users", User.query().where(User.c.age >= 30))
    return cte.from_cte("older_users")
```

```bash
rhosocial-activerecord cte run --model app.models:User \
  --query app.queries:older_users -o json
```

Recursive CTEs and dialect-specific variations are built in Python with the
framework API; the CLI only executes the resulting object.

## Backend support

`intersect` / `except` and recursive CTEs depend on the database. When the
dialect does not support a feature the backend raises an error, which the CLI
reports with exit code 1. There is no CLI-level capability switch: use the
framework's dialect protocols to decide at the application level.

## Using these commands from an AI agent

- Prefer `set run` / `cte run` for anything beyond two simple arms: the factory
  is ordinary Python and avoids CLI quoting problems.
- Pass `--model` when the factory calls `Model.backend()`; omit it only when the
  factory configures its own connection.
- Set-operation rows are dictionaries with no model metadata: `--fields` must
  name keys that actually exist in the rows.
- For an empty result, pass `--fields` so the output columns are known.
- A rejected query type (for example an `ActiveQuery` passed to `set run`)
  exits 1 with a message naming the expected type; fix the factory rather than
  retrying the same command.
