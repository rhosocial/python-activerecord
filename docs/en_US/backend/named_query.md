# Named Query & Named Procedure

> **Scope of this document**: A practical guide for application developers, focused on
> *why* and *how*.

---

## Table of Contents

1. [Why Named Query?](#1-why-named-query)
2. [Quick Start: Your First Named Query](#2-quick-start-your-first-named-query)
3. [Three Ways to Invoke a Named Query](#3-three-ways-to-invoke-a-named-query)
   - [3.1 Command-Line Interface (CLI)](#31-command-line-interface-cli)
   - [3.2 Jupyter Notebook / Programmatic API](#32-jupyter-notebook--programmatic-api)
   - [3.3 CI/CD Static Validation](#33-cicd-static-validation)
4. [Why Named Procedure?](#4-why-named-procedure)
5. [Writing a Named Procedure](#5-writing-a-named-procedure)
6. [Invoking a Named Procedure](#6-invoking-a-named-procedure)
   - [6.1 CLI Invocation](#61-cli-invocation)
   - [6.2 Notebook / Programmatic API](#62-notebook--programmatic-api)
   - [6.3 Async Environments (FastAPI)](#63-async-environments-fastapi-aiohttp)
7. [Transaction Mode Selection Guide](#7-transaction-mode-selection-guide)
8. [Feature Summary](#8-feature-summary)

> **Important**: This is a **backend feature**, independent of ActiveRecord pattern and ActiveQuery.

---

## Expression Construction Quick Reference

All expression classes take `dialect` as their first constructor argument.
Comparisons use Python operators (which return `ComparisonPredicate`);
predicates are combined with bitwise operators:

| SQL intent | Python expression |
|---|---|
| `col = val` | `Column(dialect, "col") == val` |
| `col >= val` | `Column(dialect, "col") >= val` |
| `col LIKE 'x%'` | `Column(dialect, "col").like("x%")` |
| `col IS NULL` | `Column(dialect, "col").is_null()` |
| `col IN (1,2,3)` | `Column(dialect, "col").in_([1, 2, 3])` |
| `p1 AND p2` | `p1 & p2` |
| `p1 OR p2` | `p1 \| p2` |
| `NOT p` | `~p` |
| `FROM table` | `TableExpression(dialect, "table")` |
| `SELECT *` | `WildcardExpression(dialect)` |

---

## 1. Why Named Query?

### Pain Points of the Traditional Approach

Before Named Query, the most common pattern for running database queries in Python projects was to **embed raw SQL strings directly in business logic**:

```python
# ❌ Before: routes/orders.py
import sqlite3

def get_high_value_orders(db_path, threshold=1000, days=30):
    conn = sqlite3.connect(db_path)
    sql = f"""
        SELECT id, amount, created_at FROM orders
        WHERE status = 'pending'
          AND amount >= {threshold}
          AND created_at >= DATE('now', '-{days} days')
    """
    return conn.cursor().execute(sql).fetchall()
```

**This approach has the following problems:**

| Problem | Description |
|---|---|
| **SQL injection risk** | `f-string` interpolation of parameters — malicious input can alter the query |
| **Poor reusability** | SQL strings scattered everywhere, copy-pasted across multiple files |
| **Dialect-locked** | Hard-coded SQLite syntax; migrating to PostgreSQL requires a global find-replace |
| **Cannot be tested in isolation** | The entire application must be running to execute a single query |
| **No dry-run** | The actual SQL is invisible until it runs — debugging happens after the fact |

### How Named Query Solves These Problems

Named Query encapsulates query logic in a **pure Python function**, using `dialect` as the first parameter (injected automatically by the framework at execution time):

```python
# ✅ After: myapp/queries/orders.py
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, QueryExpression,
    LimitOffsetClause,
)

def high_value_pending(dialect, threshold: int = 1000, days: int = 30):
    """Fetch high-value pending orders."""
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "amount"),
            Column(dialect, "created_at"),
        ],
        from_=TableExpression(dialect, "orders"),
        where=(
            (Column(dialect, "status") == "pending")
            & (Column(dialect, "amount") >= threshold)
            & (Column(dialect, "created_at") >= Literal(dialect, f"DATE('now', '-{days} days')"))
        ),
    )
```

---

## 2. Quick Start: Your First Named Query

### Step 1: Define the Query

```python
# myapp/queries/users.py
from rhosocial.activerecord.backend.expression import (
    Column, TableExpression, QueryExpression, LimitOffsetClause,
)

def active_users(dialect, limit: int = 100, status: str = "active"):
    """Get active users."""
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name"),
            Column(dialect, "email"),
        ],
        from_=TableExpression(dialect, "users"),
        where=Column(dialect, "status") == status,
        limit_offset=LimitOffsetClause(dialect, limit=limit),
    )
```

### Step 2: Make the Module Importable

```bash
export PYTHONPATH=/path/to/your/project:$PYTHONPATH
python -c "import myapp.queries.users; print('OK')"
```

### Step 3: Invoke via CLI

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.users.active_users \
    --db-file mydb.sqlite \
    --param limit=10
```

---

## 3. Three Ways to Invoke a Named Query

### 3.1 Command-Line Interface (CLI)

```bash
# ① Execute the query
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.users.active_users \
    --db-file mydb.sqlite \
    --param limit=10 \
    --param status=active

# ② Render SQL without executing (dry-run)
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.users.active_users \
    --db-file mydb.sqlite --dry-run

# Sample output:
# [DRY RUN] SELECT "id", "name", "email" FROM "users" WHERE "status" = ? LIMIT ?
# Params: ('active', 100)

# ③ Describe query signature without executing
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.users.active_users --describe

# ④ List all named queries in a module
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.users --list

# ⑤ Async execution (requires aiosqlite)
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.users.active_users \
    --db-file mydb.sqlite --async
```

#### Full CLI Options

| Option | Description |
|---|---|
| `qualified_name` | Fully qualified name (positional, e.g. `myapp.queries.users.active_users`) |
| `--param KEY=VALUE` | Query parameter (repeatable) |
| `--list` | List all named queries in the module |
| `--describe` | Print parameter signature, do not execute |
| `--dry-run` | Render SQL and params, do not execute |
| `--async` | Use async execution |
| `--force` | Allow non-SELECT statements (DML/DDL) |
| `--explain` | Execute EXPLAIN plan |

---

### 3.2 Jupyter Notebook / Programmatic API

```python
# ✅ After: Named Query Programmatic API
from rhosocial.activerecord.backend.named_query import (
    NamedQueryResolver, resolve_named_query,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
import pandas as pd

backend = SQLiteBackend(database="mydb.sqlite")
dialect = backend.dialect

# Option A: one-shot (quick)
# resolve_named_query returns (expression, sql_string, params_tuple)
expr, sql, params = resolve_named_query(
    "myapp.queries.users.active_users",
    dialect,
    {"limit": 50, "status": "active"},
)
print("SQL:", sql)

# Use pandas to execute
df = pd.read_sql(sql, backend.connection, params=list(params))

# Option B: step-by-step control (flexible)
resolver = NamedQueryResolver("myapp.queries.users.active_users").load()
info = resolver.describe()
print(info["parameters"])

# Generate SQL
expr = resolver.execute(dialect, {"limit": 50})
sql, params = expr.to_sql()
```

---

### 3.3 CI/CD Static Validation

```yaml
# .github/workflows/validate-queries.yml
name: Validate Named Queries
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e .
      - name: Static validation
        run: |
          python -m rhosocial.activerecord.backend.impl.sqlite named-query \
            myapp.queries.users.active_users \
            --db-file :memory: --dry-run \
            --param limit=100 --param status=active
```

> **Tip**: Use `--db-file :memory:` with `--dry-run` — no persistent database file required in CI.

---

## 4. Why Named Procedure?

Named Query solves management and reuse of **individual queries**. Real-world operations often require **multi-step sequences with conditional branching**. For example:

> "Count this month's orders → skip if empty → archive completed orders → delete archived records"

---

## 5. Writing a Named Procedure

```python
# myapp/procedures/monthly_cleanup.py
from rhosocial.activerecord.backend.named_query import Procedure, ProcedureContext

class MonthlyCleanupProcedure(Procedure):
    """Monthly order archival and cleanup procedure."""
    month: str = "2026-03"

    def run(self, ctx: ProcedureContext) -> None:
        # Step 1: count orders and bind result
        ctx.execute(
            "myapp.queries.orders.count_monthly_orders",
            params={"month": self.month},
            bind="order_count",
        )

        # Step 2: extract scalar and branch
        count = ctx.scalar("order_count", "cnt")
        if not count:
            ctx.log(f"No orders for {self.month}, skipping cleanup.", level="INFO")
            ctx.abort("MonthlyCleanupProcedure", f"No orders in {self.month}")

        # Step 3: archive completed orders
        ctx.execute(
            "myapp.queries.orders.archive_completed_orders",
            params={"month": self.month},
            output=True,
        )

        # Step 4: delete archived records
        ctx.execute(
            "myapp.queries.orders.delete_archived_orders",
            params={"month": self.month},
            output=True,
        )

        ctx.log("Cleanup complete.", level="INFO")
```

#### ProcedureContext Method Reference

| Method | Signature | Description |
|---|---|---|
| `execute` | `(qualified_name, params=None, bind=None, output=False)` | Run a named query |
| `scalar` | `(var_name, column)` | Extract a single column value from bound variable |
| `rows` | `(var_name)` | Iterate all rows of a bound variable |
| `bind` | `(name, data)` | Manually bind arbitrary data to a variable |
| `log` | `(message, level="INFO")` | Append a log entry |
| `abort` | `(procedure_name, reason)` | Terminate procedure, trigger rollback |

---

## 6. Invoking a Named Procedure

### 6.1 CLI Invocation

```bash
# ① Execute (AUTO transaction mode)
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    myapp.procedures.monthly_cleanup.MonthlyCleanupProcedure \
    --db-file mydb.sqlite \
    --param month=2026-03 \
    --transaction auto

# ② Describe the procedure (no execution)
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    myapp.procedures.monthly_cleanup.MonthlyCleanupProcedure \
    --db-file mydb.sqlite --describe

# ③ Dry-run: render each step's SQL without executing
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    myapp.procedures.monthly_cleanup.MonthlyCleanupProcedure \
    --db-file mydb.sqlite --dry-run --param month=2026-03

# ④ STEP transaction mode (per-step commit)
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    myapp.procedures.monthly_cleanup.MonthlyCleanupProcedure \
    --db-file mydb.sqlite --param month=2026-03 --transaction step

# ⑤ List all named procedures in a module
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    myapp.procedures.monthly_cleanup --list
```

#### named-procedure CLI Options

| Option | Description |
|---|---|
| `qualified_name` | Fully qualified class name |
| `--param KEY=VALUE` | Procedure parameter (repeatable) |
| `--transaction {auto,step,none}` | Transaction mode (default `auto`) |
| `--describe` | Print parameter definitions, do not execute |
| `--dry-run` | Render each step's SQL, do not execute |
| `--list` | List all named procedures in the module |
| `--async` | Async execution (requires an `AsyncProcedure` subclass) |

---

### 6.2 Notebook / Programmatic API

```python
from rhosocial.activerecord.backend.named_query import (
    ProcedureRunner, TransactionMode, ProcedureResult,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database="mydb.sqlite")
dialect = backend.dialect

runner = ProcedureRunner(
    "myapp.procedures.monthly_cleanup.MonthlyCleanupProcedure"
).load()

result: ProcedureResult = runner.run(
    dialect,
    user_params={"month": "2026-03"},
    transaction_mode=TransactionMode.AUTO,
    backend=backend,
    execute_query=backend.execute,
)

if result.aborted:
    print(f"��️  Aborted: {result.abort_reason}")
else:
    print(f"✅  Done. Output steps: {len(result.outputs)}")

for entry in result.logs:
    print(f"[{entry.level}] {entry.message}")
```

---

### 6.3 Async Environments (FastAPI/aiohttp)

```python
# myapp/procedures/monthly_cleanup_async.py
from rhosocial.activerecord.backend.named_query import AsyncProcedure, AsyncProcedureContext

class MonthlyCleanupAsyncProcedure(AsyncProcedure):
    """Monthly cleanup (async version)."""
    month: str = "2026-03"

    async def run(self, ctx: AsyncProcedureContext) -> None:
        await ctx.execute(
            "myapp.queries.orders.count_monthly_orders",
            params={"month": self.month},
            bind="order_count",
        )

        count = await ctx.scalar("order_count", "cnt")
        if not count:
            await ctx.log(f"No orders for {self.month}, skipping.")
            await ctx.abort("MonthlyCleanupAsyncProcedure", f"No orders in {self.month}")

        await ctx.execute(
            "myapp.queries.orders.archive_completed_orders",
            params={"month": self.month},
            output=True,
        )
```

```python
# FastAPI endpoint
from fastapi import FastAPI
from rhosocial.activerecord.backend.named_query import AsyncProcedureRunner, TransactionMode
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

app = FastAPI()
async_backend = AsyncSQLiteBackend(database="mydb.sqlite")

@app.post("/admin/cleanup/{month}")
async def run_cleanup(month: str):
    runner = AsyncProcedureRunner(
        "myapp.procedures.monthly_cleanup_async.MonthlyCleanupAsyncProcedure"
    ).load()
    result = await runner.run(
        async_backend.dialect,
        user_params={"month": month},
        transaction_mode=TransactionMode.AUTO,
        backend=async_backend,
        execute_query=async_backend.execute,
    )
    return {
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "outputs": result.outputs,
    }
```

> **Important**: `AsyncProcedure` subclasses must be run by `AsyncProcedureRunner`;
> `Procedure` subclasses must be run by `ProcedureRunner`. Do not mix them.

---

## 7. Transaction Mode Selection Guide

| Mode | Description | Best For | On Failure |
|---|---|---|---|
| `AUTO` (default) | Entire procedure wrapped in one transaction | Batch archival, data migration (atomicity required) | Full rollback |
| `STEP` | Each step commits independently | Long workflows, partial completion acceptable | Completed steps preserved |
| `NONE` | No transaction | Read-only procedures, externally managed transactions | No protection |

---

## 8. Feature Summary

| Dimension | Traditional | Named Query | Named Procedure |
|---|---|---|---|
| **SQL safety** | ❌ Injection risk | ✅ Forced expression | ✅ Forced expression |
| **Reusability** | ❌ Scattered | ✅ Call by qualified name | ✅ Compose multiple queries |
| **CLI invocable** | ❌ Requires a script | ✅ Built-in | ✅ Built-in |
| **Transaction management** | ❌ Manual | — | ✅ AUTO / STEP / NONE |
| **Notebook-friendly** | △ Possible but verbose | ✅ Clean API | ✅ Clean API |
| **CI/CD dry-run** | ❌ Requires DB connection | ✅ DB-free dry-run | ✅ DB-free dry-run |
| **Async support** | △ Manual | ✅ `--async` flag | ✅ `AsyncProcedure` |
| **Cross-dialect** | ❌ Locked | ✅ `dialect` param | ✅ `ctx.dialect` |
| **Execution log** | ❌ None | — | ✅ `ctx.log()` |
| **Multi-step orchestration** | ❌ Handwritten scripts | ❌ Single step | ✅ Sequential + branch + loop |

---

## API Reference

### Exceptions

- `NamedQueryError` - Base exception
- `NamedQueryNotFoundError` - Query not found
- `NamedQueryModuleNotFoundError` - Module not found
- `NamedQueryInvalidReturnTypeError` - Invalid return type
- `NamedQueryInvalidParameterError` - Invalid parameter
- `NamedQueryMissingParameterError` - Missing required parameter
- `NamedQueryNotCallableError` - Not callable
- `NamedQueryExplainNotAllowedError` - EXPLAIN not allowed

### Named Query API

- `NamedQueryResolver` - Main resolver class
- `resolve_named_query()` - One-shot resolve and execute
- `list_named_queries_in_module()` - List queries in module
- `validate_expression()` - Validate expression type

### Named Procedure API

- `Procedure` - Synchronous procedure base class
- `ProcedureContext` - Synchronous execution context
- `ProcedureRunner` - Synchronous executor
- `AsyncProcedure` - Asynchronous procedure base class
- `AsyncProcedureContext` - Asynchronous execution context
- `AsyncProcedureRunner` - Asynchronous executor
- `TransactionMode` - Transaction mode enum
- `ProcedureResult` - Execution result
