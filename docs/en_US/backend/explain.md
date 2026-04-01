# Query Explain Interface

The `explain()` interface provides a structured way to execute `EXPLAIN` statements against a database backend and receive typed, backend-specific result objects. It is designed for query analysis, performance debugging, and index-usage verification.

## Overview

The explain system is accessible directly via `backend.explain(expression, options)` and provides:

- **Bytecode Analysis** (SQLite): Inspect the virtual machine program SQLite compiles for a query
- **Query Plan Analysis**: Obtain a human-readable description of the query strategy
- **Index Usage Detection**: Automatically determine whether a query performs a full scan, uses an index with table lookup, or benefits from a covering index
- **Typed Results**: Backend-specific `pydantic.BaseModel` result objects rather than raw dictionaries
- **Sync and Async Parity**: Identical API shapes for synchronous and asynchronous backends

## Architecture Design

### Module Structure

```
backend/explain/
├── __init__.py          # Module exports
├── types.py             # BaseExplainResult base class
├── protocols.py         # Sync and async protocol definitions
└── backend_mixin.py     # SyncExplainBackendMixin / AsyncExplainBackendMixin

backend/impl/sqlite/explain/
├── __init__.py          # SQLite explain exports
└── types.py             # SQLite-specific result row and result classes
```

### Sync and Async Separation

The explain system follows the project's sync/async parity principle. Protocols and mixins are strictly separated:

| Class | Role |
|-------|------|
| `SyncExplainBackendProtocol` | Runtime-checkable protocol for synchronous backends |
| `AsyncExplainBackendProtocol` | Runtime-checkable protocol for asynchronous backends |
| `SyncExplainBackendMixin` | Mixin that implements sync `explain()` via `fetch_all()` |
| `AsyncExplainBackendMixin` | Mixin that implements async `explain()` via `await fetch_all()` |
| `_ExplainMixinBase` | Shared non-I/O logic: SQL building and the `_parse_explain_result()` hook |

### Result Base Class

All explain results inherit from `BaseExplainResult`, a plain `pydantic.BaseModel` (not an `ActiveRecord`):

```python
class BaseExplainResult(BaseModel):
    raw_rows: List[Dict[str, Any]]  # Raw rows from fetch_all()
    sql: str                         # The EXPLAIN SQL that was executed
    duration: float                  # Execution time in seconds
```

Using `pydantic.BaseModel` avoids a reverse dependency from the backend layer back to the ActiveRecord model layer.

## Basic Usage

### Explaining a Query (Sync)

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteExplainResult
from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

dialect = SQLiteDialect()
backend = SQLiteBackend(database="mydb.sqlite3")
backend.connect()

# Explain the bytecode for a query
expr = RawSQLExpression(dialect, "SELECT * FROM users WHERE id = 1")
result = backend.explain(expr)

assert isinstance(result, SQLiteExplainResult)
print(f"SQL:      {result.sql}")
print(f"Duration: {result.duration * 1000:.2f} ms")
for row in result.rows:
    print(f"  {row.addr:>4}  {row.opcode:<18}  {row.p1:>4}  {row.p2:>4}  {row.comment or ''}")
```

### Using the Expression Builder

You can pass any `BaseExpression` (except `ExplainExpression` itself):

```python
from rhosocial.activerecord.backend.expression.core import (
    TableExpression, WildcardExpression,
)
from rhosocial.activerecord.backend.expression.statements import QueryExpression

query = QueryExpression(
    dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, "users"),
)
result = backend.explain(query)
```

### EXPLAIN QUERY PLAN

Pass `ExplainOptions(type=ExplainType.QUERY_PLAN)` to obtain the query strategy instead of bytecode:

```python
from rhosocial.activerecord.backend.expression.statements import (
    ExplainOptions, ExplainType,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteExplainQueryPlanResult

opts = ExplainOptions(type=ExplainType.QUERY_PLAN)
result = backend.explain(query, opts)

assert isinstance(result, SQLiteExplainQueryPlanResult)
for row in result.rows:
    print(f"  {row.detail}")
```

### Async API

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database="mydb.sqlite3")
await backend.connect()

result = await backend.explain(query)                # bytecode
result = await backend.explain(query, opts)          # query plan
```

## SQLite Result Types

SQLite provides two completely different output schemas depending on the EXPLAIN mode. The backend returns a dedicated typed object for each.

### SQLiteExplainResult (Bytecode)

Returned for plain `EXPLAIN <stmt>`. Each row represents one VDBE (Virtual DataBase Engine) instruction:

```python
class SQLiteExplainRow(BaseModel):
    addr: int           # Program counter address
    opcode: str         # Instruction name (e.g. "OpenRead", "SeekGE", "Column")
    p1: int             # First operand (often cursor number)
    p2: int             # Second operand (often B-tree page number or jump target)
    p3: int             # Third operand
    p4: Optional[str]   # Optional string or blob operand
    p5: int             # Flags bitmask
    comment: Optional[str]  # Human-readable annotation
```

```python
class SQLiteExplainResult(BaseExplainResult):
    rows: List[SQLiteExplainRow]
```

#### Understanding Bytecode Opcodes

The most important opcodes for query analysis:

| Opcode | Meaning |
|--------|---------|
| `OpenRead` | Opens a cursor on a B-tree (table or index) |
| `Rewind` | Moves cursor to the first row (beginning of a full scan) |
| `Next` | Advances cursor to the next row |
| `SeekGE` / `SeekGT` / `SeekLE` / `SeekLT` / `SeekEQ` | Positions cursor on index using a key comparison |
| `DeferredSeek` | Defers moving the table cursor until a column is actually needed |
| `IdxRowid` | Reads the rowid from the current index cursor |
| `Column` | Reads a column value from a cursor |

### SQLiteExplainQueryPlanResult (Query Plan)

Returned for `EXPLAIN QUERY PLAN <stmt>`. Each row describes one step in the query strategy:

```python
class SQLiteExplainQueryPlanRow(BaseModel):
    id: int       # Row identifier (used to build the tree structure)
    parent: int   # Parent row id (0 = top-level)
    notused: int  # Reserved field (always 0 in current SQLite)
    detail: str   # Human-readable description of the step
```

```python
class SQLiteExplainQueryPlanResult(BaseExplainResult):
    rows: List[SQLiteExplainQueryPlanRow]
```

The `detail` text uses keywords such as `SCAN`, `SEARCH`, and `USING (COVERING) INDEX` that directly indicate the query strategy.

## Index Usage Analysis

Both `SQLiteExplainResult` and `SQLiteExplainQueryPlanResult` provide built-in helpers for detecting whether a query uses an index.

### `analyze_index_usage()`

Returns one of four string labels:

| Label | Meaning |
|-------|---------|
| `"full_scan"` | No index used; all rows are examined |
| `"index_with_lookup"` | Index used to locate rows, but the table is still accessed for non-index columns |
| `"covering_index"` | A covering index satisfies the query without any table access |
| `"unknown"` | Pattern not recognised (complex multi-table query or future SQLite version) |

### Convenience Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_full_scan` | `bool` | `True` when no index is used |
| `is_index_used` | `bool` | `True` when any index is used |
| `is_covering_index` | `bool` | `True` when a covering index eliminates table access |

### Example: Diagnosing Index Usage

```python
from rhosocial.activerecord.backend.expression import RawSQLExpression

dialect = SQLiteDialect()
backend = SQLiteBackend(database="mydb.sqlite3")
backend.connect()

queries = {
    "full scan":       "SELECT * FROM orders",
    "index lookup":    "SELECT * FROM orders WHERE status = 'pending'",
    "covering index":  "SELECT sku FROM order_items WHERE order_id = 1",
}

for label, sql in queries.items():
    # Bytecode analysis
    result = backend.explain(RawSQLExpression(dialect, sql))
    print(f"{label}: {result.analyze_index_usage()}")
    print(f"  is_full_scan={result.is_full_scan}, "
          f"is_index_used={result.is_index_used}, "
          f"is_covering_index={result.is_covering_index}")

    # Query plan analysis (same properties available)
    plan = backend.explain(
        RawSQLExpression(dialect, sql),
        ExplainOptions(type=ExplainType.QUERY_PLAN),
    )
    for row in plan.rows:
        print(f"  plan: {row.detail}")
```

#### Reading the Bytecode Patterns

**Full table scan** — single `OpenRead` cursor on the main table, no seek opcode:

```
OpenRead  p1=0  p2=<table root>   # opens the table B-tree
Rewind    p1=0                     # start from beginning
Ne        ...                      # compare each row
Next      p1=0                     # move to next row
```

**Index with table lookup** — two `OpenRead` cursors (table + index), seek opcode present:

```
OpenRead  p1=0  p2=<table root>         # table cursor
OpenRead  p1=1  p2=<index root>  p5=2   # index cursor (OPFLAG_SEEKEQ)
SeekGE    p1=1  ...                      # seek on index
IdxGT     p1=1  ...                      # range boundary check
DeferredSeek p1=1                        # defer table access
IdxRowid  p1=1                           # retrieve rowid from index
Column    p1=0  ...                      # read remaining columns from table
```

**Covering index** — single `OpenRead` cursor pointing to the index only; all `Column` reads use the index cursor:

```
OpenRead  p1=1  p2=<index root>  p4=k(n,,)  # only index cursor opened
SeekGE    p1=1  ...                           # seek on index
IdxGT     p1=1  ...                           # range boundary
Column    p1=1  p2=<col>                      # read directly from index
```

## Protocol Checking

You can verify that a backend satisfies the explain protocol at runtime:

```python
from rhosocial.activerecord.backend.explain import (
    SyncExplainBackendProtocol,
    AsyncExplainBackendProtocol,
)

assert isinstance(backend, SyncExplainBackendProtocol)
assert isinstance(async_backend, AsyncExplainBackendProtocol)
```

## Implementing `explain()` in a Custom Backend

1. **Import the appropriate mixin** based on whether your backend is sync or async.
2. **Add it to the class MRO** before the storage backend base class.
3. **Override `_parse_explain_result()`** to return your backend's typed result class.

```python
from rhosocial.activerecord.backend.explain import SyncExplainBackendMixin
from rhosocial.activerecord.backend.base import StorageBackend
from pydantic import BaseModel
from typing import List, Dict, Any

class MyExplainRow(BaseModel):
    # Define fields matching your database's EXPLAIN output
    ...

class MyExplainResult(BaseExplainResult):
    rows: List[MyExplainRow]

class MyBackend(SyncExplainBackendMixin, StorageBackend):
    def _parse_explain_result(
        self,
        raw_rows: List[Dict[str, Any]],
        sql: str,
        duration: float,
    ) -> MyExplainResult:
        rows = [MyExplainRow(**r) for r in raw_rows]
        return MyExplainResult(raw_rows=raw_rows, sql=sql, duration=duration, rows=rows)
```

You also need to override `format_explain_statement()` in your dialect if your database uses non-standard EXPLAIN syntax.

## API Reference

### `backend.explain(expression, options=None)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `expression` | `BaseExpression` | Any expression except `ExplainExpression` |
| `options` | `ExplainOptions \| None` | Optional explain options (type, format, analyze) |

**Returns**: A `BaseExplainResult` subclass specific to the backend.

### `ExplainOptions`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `ExplainType \| None` | `None` | `ExplainType.QUERY_PLAN` for query plan mode |
| `format` | `ExplainFormat \| None` | `None` | Output format (backend-specific) |
| `analyze` | `bool` | `False` | Execute the query and include runtime stats (PostgreSQL) |

### `SQLiteExplainResult` Methods

| Method / Property | Return Type | Description |
|-------------------|-------------|-------------|
| `analyze_index_usage()` | `str` | `"full_scan"`, `"index_with_lookup"`, `"covering_index"`, or `"unknown"` |
| `is_full_scan` | `bool` | `True` when no index is used |
| `is_index_used` | `bool` | `True` when any index is used |
| `is_covering_index` | `bool` | `True` when a covering index eliminates table access |

### `SQLiteExplainQueryPlanResult` Methods

Same `analyze_index_usage()`, `is_full_scan`, `is_index_used`, and `is_covering_index` as above, based on the `detail` text from `EXPLAIN QUERY PLAN`.
