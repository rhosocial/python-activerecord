"""
Experiment script: verify the correct API for execute_batch_dml and execute_batch_dql.

Purpose:
  Validate that execute_batch_dml / execute_batch_dql are instance methods on the
  backend object (via BatchExecutionMixin), NOT free functions importable from
  rhosocial.activerecord.backend.batch.

Correct import paths confirmed by this script:
  - BatchCommitMode   ← from rhosocial.activerecord.backend.result
  - BatchDMLResult    ← from rhosocial.activerecord.backend.result
  - BatchDQLResult    ← from rhosocial.activerecord.backend.result
  - InsertExpression  ← from rhosocial.activerecord.backend.expression
  - QueryExpression   ← from rhosocial.activerecord.backend.expression.statements
  - WildcardExpression← from rhosocial.activerecord.backend.expression
  - TableExpression   ← from rhosocial.activerecord.backend.expression
  - ValuesSource      ← from rhosocial.activerecord.backend.expression
  - Column, Literal   ← from rhosocial.activerecord.backend.expression
  - OrderByClause     ← from rhosocial.activerecord.backend.expression.query_parts
  - LimitOffsetClause ← from rhosocial.activerecord.backend.expression.query_parts
  - execute_batch_dml / execute_batch_dql are methods on backend instances

All demos use SQLite :memory: backends and are fully self-contained.
"""

# ---------------------------------------------------------------------------
# Assertion 1: free-function import does NOT exist
# ---------------------------------------------------------------------------

def assert_no_free_function_import() -> None:
    """Confirm there is no standalone execute_batch_dql/dml in a .batch module."""

    print("\n" + "=" * 60)
    print("CHECK 1 — No free-function import at backend.batch")
    print("=" * 60)

    # Attempt to import a non-existent module
    try:
        import rhosocial.activerecord.backend.batch  # type: ignore  # noqa: F401
        has_batch_module = True
    except ModuleNotFoundError:
        has_batch_module = False

    if has_batch_module:
        # Even if the module exists (future), the functions should not be there yet
        import rhosocial.activerecord.backend.batch as batch_mod  # type: ignore
        has_dql = hasattr(batch_mod, "execute_batch_dql")
        has_dml = hasattr(batch_mod, "execute_batch_dml")
        print(f"\n  Module exists: True")
        print(f"  has execute_batch_dql as free function: {has_dql}")
        print(f"  has execute_batch_dml as free function: {has_dml}")
        # The documentation in batch_processing.md was WRONG if it said
        # "from rhosocial.activerecord.backend.batch import execute_batch_dql"
        if not has_dql:
            print("\n✓ Free-function import confirmed absent — doc was incorrect.")
        else:
            print("\n✗ Unexpected: free function found — investigate further.")
    else:
        print("\n  rhosocial.activerecord.backend.batch module: does not exist")
        print("\n✓ Confirmed: no batch free-function module — methods live on backend.")


# ---------------------------------------------------------------------------
# Assertion 2: the methods ARE on the backend instance
# ---------------------------------------------------------------------------

def assert_methods_on_backend() -> None:
    """Confirm execute_batch_dml and execute_batch_dql are backend instance methods."""

    print("\n" + "=" * 60)
    print("CHECK 2 — Methods live on the backend instance")
    print("=" * 60)

    from rhosocial.activerecord.backend.impl.sqlite import (
        SQLiteBackend, SQLiteConnectionConfig,
    )
    from rhosocial.activerecord.backend.base import BatchExecutionMixin

    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)

    has_dml = hasattr(backend, "execute_batch_dml")
    has_dql = hasattr(backend, "execute_batch_dql")
    is_mixin = isinstance(backend, BatchExecutionMixin)

    print(f"\n  backend.execute_batch_dml  : {has_dml}")
    print(f"  backend.execute_batch_dql  : {has_dql}")
    print(f"  isinstance(BatchExecutionMixin): {is_mixin}")

    assert has_dml, "execute_batch_dml must be a backend method"
    assert has_dql, "execute_batch_dql must be a backend method"

    print("\n✓ Both methods confirmed as backend instance methods.")


# ---------------------------------------------------------------------------
# Assertion 3: correct import paths for all related types
# ---------------------------------------------------------------------------

def assert_import_paths() -> None:
    """Verify every symbol used in batch processing can be imported correctly."""

    print("\n" + "=" * 60)
    print("CHECK 3 — Correct import paths for all batch-related types")
    print("=" * 60)

    imports_ok = []
    imports_fail = []

    def try_import(module: str, name: str) -> None:
        try:
            mod = __import__(module, fromlist=[name])
            getattr(mod, name)
            imports_ok.append(f"from {module} import {name}")
        except (ImportError, AttributeError) as e:
            imports_fail.append(f"from {module} import {name}  ← {e}")

    # Result / commit-mode types
    try_import("rhosocial.activerecord.backend.result", "BatchCommitMode")
    try_import("rhosocial.activerecord.backend.result", "BatchDMLResult")
    try_import("rhosocial.activerecord.backend.result", "BatchDQLResult")

    # Expression types (DML)
    try_import("rhosocial.activerecord.backend.expression", "InsertExpression")
    try_import("rhosocial.activerecord.backend.expression", "UpdateExpression")
    try_import("rhosocial.activerecord.backend.expression", "DeleteExpression")
    try_import("rhosocial.activerecord.backend.expression", "TableExpression")
    try_import("rhosocial.activerecord.backend.expression", "ValuesSource")
    try_import("rhosocial.activerecord.backend.expression", "Column")
    try_import("rhosocial.activerecord.backend.expression", "Literal")

    # Expression types (DQL)
    try_import("rhosocial.activerecord.backend.expression.statements", "QueryExpression")
    try_import("rhosocial.activerecord.backend.expression.query_sources", "WithQueryExpression")
    try_import("rhosocial.activerecord.backend.expression", "WildcardExpression")
    try_import("rhosocial.activerecord.backend.expression.query_parts", "OrderByClause")
    try_import("rhosocial.activerecord.backend.expression.query_parts", "LimitOffsetClause")

    # Mixin base classes (for type-checking)
    try_import("rhosocial.activerecord.backend.base", "BatchExecutionMixin")
    try_import("rhosocial.activerecord.backend.base", "AsyncBatchExecutionMixin")

    print("\n  ✓ Successful imports:")
    for s in imports_ok:
        print(f"    {s}")

    if imports_fail:
        print("\n  ✗ Failed imports:")
        for s in imports_fail:
            print(f"    {s}")
    else:
        print("\n  (No failures)")

    assert not imports_fail, f"Some imports failed: {imports_fail}"
    print("\n✓ All import paths verified.")


# ---------------------------------------------------------------------------
# Demo 1: execute_batch_dml — bulk INSERT via backend method
# ---------------------------------------------------------------------------

def demonstrate_batch_dml() -> None:
    """execute_batch_dml is called as backend.execute_batch_dml(expressions, ...)."""

    print("\n" + "=" * 60)
    print("DEMO 1 — execute_batch_dml (backend method, not free function)")
    print("=" * 60)

    from rhosocial.activerecord.backend.impl.sqlite import (
        SQLiteBackend, SQLiteConnectionConfig,
    )
    from rhosocial.activerecord.backend.expression import (
        InsertExpression, ValuesSource, Literal,
    )
    from rhosocial.activerecord.backend.result import BatchCommitMode
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType

    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)
    backend.connect()

    # Create table
    backend.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )

    dialect = backend.dialect

    # Build InsertExpression list
    rows = [
        ("Alice", "alice@example.com"),
        ("Bob",   "bob@example.com"),
        ("Carol", "carol@example.com"),
        ("Dave",  "dave@example.com"),
        ("Eve",   "eve@example.com"),
    ]
    exprs = [
        InsertExpression(
            dialect,
            into="users",
            columns=["name", "email"],
            source=ValuesSource(
                dialect,
                values_list=[[Literal(dialect, name), Literal(dialect, email)]],
            ),
        )
        for name, email in rows
    ]

    # ✅ Correct: call as backend method
    total_inserted = 0
    for batch_result in backend.execute_batch_dml(
        exprs,
        batch_size=2,
        commit_mode=BatchCommitMode.WHOLE,
    ):
        total_inserted += batch_result.total_affected_rows
        print(f"  Batch {batch_result.batch_index}: "
              f"{batch_result.total_affected_rows} rows, "
              f"duration={batch_result.duration:.4f}s")

    count_result = backend.execute(
        "SELECT COUNT(*) as cnt FROM users", None,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    count = count_result.data[0]["cnt"] if count_result.data else 0
    print(f"\n  Total rows in DB  : {count}")
    print(f"  Total rows reported: {total_inserted}")

    assert count == len(rows)
    backend.disconnect()
    print("\n✓ execute_batch_dml: called as backend.execute_batch_dml(expressions, ...)")


# ---------------------------------------------------------------------------
# Demo 2: execute_batch_dql — paginated SELECT via backend method
# ---------------------------------------------------------------------------

def demonstrate_batch_dql() -> None:
    """execute_batch_dql is called as backend.execute_batch_dql(expression, ...)."""

    print("\n" + "=" * 60)
    print("DEMO 2 — execute_batch_dql (backend method, not free function)")
    print("=" * 60)

    from rhosocial.activerecord.backend.impl.sqlite import (
        SQLiteBackend, SQLiteConnectionConfig,
    )
    from rhosocial.activerecord.backend.expression.statements import QueryExpression
    from rhosocial.activerecord.backend.expression import (
        WildcardExpression, TableExpression,
    )
    from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
    from rhosocial.activerecord.backend.expression import Column
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType

    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)
    backend.connect()

    DDL_OPTS = ExecutionOptions(stmt_type=StatementType.DDL)
    DML_OPTS = ExecutionOptions(stmt_type=StatementType.INSERT)

    backend.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)", options=DDL_OPTS)

    # Seed 25 rows
    total_rows = 25
    for i in range(1, total_rows + 1):
        backend.execute(
            "INSERT INTO items (name) VALUES (?)",
            (f"item{i:03d}",),
            options=DML_OPTS,
        )

    dialect = backend.dialect

    # Build SELECT * FROM items ORDER BY id
    query_expr = QueryExpression(
        dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, "items"),
        order_by=OrderByClause(
            dialect,
            expressions=[(Column(dialect, "id"), "ASC")],
        ),
    )

    # ✅ Correct: call as backend method
    page_size = 10
    all_rows = []
    for page in backend.execute_batch_dql(query_expr, page_size=page_size):
        all_rows.extend(page.data)
        print(f"  Page {page.page_index}: {page.page_size} rows, "
              f"has_more={page.has_more}, duration={page.duration:.4f}s")

    print(f"\n  Total rows fetched: {len(all_rows)}")
    assert len(all_rows) == total_rows, f"Expected {total_rows}, got {len(all_rows)}"

    backend.disconnect()
    print("\n✓ execute_batch_dql: called as backend.execute_batch_dql(expression, page_size=...)")


# ---------------------------------------------------------------------------
# Summary: correct vs. incorrect usage patterns
# ---------------------------------------------------------------------------

def print_usage_summary() -> None:
    print("\n" + "=" * 60)
    print("USAGE SUMMARY")
    print("=" * 60)
    print("""
❌ WRONG (does not exist):
    from rhosocial.activerecord.backend.batch import execute_batch_dql
    from rhosocial.activerecord.backend.batch import execute_batch_dml

✅ CORRECT — call as backend instance methods:
    backend.execute_batch_dml(expressions, batch_size=500, commit_mode=BatchCommitMode.WHOLE)
    backend.execute_batch_dql(query_expression, page_size=500)

✅ CORRECT imports for related types:
    from rhosocial.activerecord.backend.result import BatchCommitMode, BatchDMLResult, BatchDQLResult
    from rhosocial.activerecord.backend.expression import InsertExpression, ValuesSource, Column, Literal
    from rhosocial.activerecord.backend.expression.statements import QueryExpression
    from rhosocial.activerecord.backend.expression.query_parts import OrderByClause, LimitOffsetClause
    from rhosocial.activerecord.backend.base import BatchExecutionMixin  # for type hints only
""")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("execute_batch_dql / execute_batch_dml — API Verification Script")
    print("=" * 60)

    assert_no_free_function_import()
    assert_methods_on_backend()
    assert_import_paths()
    demonstrate_batch_dml()
    demonstrate_batch_dql()
    print_usage_summary()

    print("=" * 60)
    print("All checks passed.")
