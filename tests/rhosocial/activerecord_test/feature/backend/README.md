# Backend tests

Backend tests cover the backend implementation itself — dialect SQL generation, protocol
switches, executable statements and driver behaviour. They are **not** imported from the shared
testsuite; the ORM-level contract lives in `rhosocial-activerecord-testsuite`.

The tree has a generic layer and two concrete backends. Directory names describe the test focus.

## Layout

| Directory | Content |
| --------- | ------- |
| `core/` | Framework-level contracts: MRO/dispatch, cast, transaction base, partition, schema, named expressions |
| `adapters/` | Type adapter contracts and round-trips |
| `errors/` | Error taxonomy and execute contract |
| `dialect/` | Backend-agnostic dialect protocols (CTE, window, arrays, JSON, quoting, …) |
| `dummy/` | Concrete backend with **no database**: the SQL-standard reference baseline |
| `sqlite/` | Concrete backend with a real database: per-backend diff plus everything needing a live connection |

`dummy/` is split into `capability/` (protocol completeness, `supports_*`, placeholder IO),
`expression/`, `statements/`, `ddl/`, `dialect/`, `types/` and `mixin/`.

`sqlite/` is split into `cli/`, `core/`, `dialect/{capabilities,ddl,execution,expressions,functions,statements}`,
`extensions/`, `introspection/`, `native/`, `migration/` and `named_connection/`.

## Naming rules

- Sync/async tests for the same IO behaviour live in the **same directory**: `test_X.py` ↔
  `test_X_async.py`. Only the `_async` suffix differs; method names stay identical.
- Non-IO tests (expression construction, `to_sql`, dialect formatting, `supports_*`, protocol
  completeness) are written once — no `_async` copy. Dummy's backend "IO" is placeholder-only,
  so `dummy/` is never split by sync/async.
- `dummy/` holds the generic baseline; `sqlite/` holds only where SQLite differs from that
  baseline, plus SQLite-only capabilities.

## Parallelism

Parallel grouping is **declared, never inferred**. A leaf directory that shares a database or
other IO state declares this in its `conftest.py`:

```python
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    parallel=True,
    purpose="what this directory verifies",
    passes_means="what a pass says about the system",
    fails_means="what a failure says about the system",
)
```

A declared directory is pinned to one xdist worker **per scenario**; a directory that declares
nothing runs in unlimited parallel. A `conftest.py` or a `database` fixture alone is **not** a
declaration. Declarations are inherited from the nearest parent, so an opt-out under a declared
parent must be explicit: `Declaration(parallel=False)`.

The declared directories are the seven SQLite IO leaves: `sqlite/cli`, `sqlite/core`,
`sqlite/dialect/ddl`, `sqlite/dialect/execution`, `sqlite/extensions`, `sqlite/introspection`
and `sqlite/native`. The generic layer, all of `dummy/` and the remaining `sqlite/dialect/*`
directories stay undeclared.

Run with `-n 4 --dist=loadgroup`; `--dist` is mandatory for a parallel run. More workers regress
on this suite because of worker overhead.
