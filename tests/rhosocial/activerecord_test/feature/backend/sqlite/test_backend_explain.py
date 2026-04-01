# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_backend_explain.py
"""
Integration tests for SQLiteBackend.explain() and AsyncSQLiteBackend.explain().

These tests verify:
- backend.explain(expression) returns the correct typed result class
- EXPLAIN (bytecode) → SQLiteExplainResult with SQLiteExplainRow items
- EXPLAIN QUERY PLAN → SQLiteExplainQueryPlanResult with SQLiteExplainQueryPlanRow items
- BaseExplainResult fields (raw_rows, sql, duration) are correctly populated
- SyncExplainBackendProtocol is satisfied at runtime
- AsyncExplainBackendProtocol is satisfied at runtime
- Async explain() returns the same result structure
"""

import pytest

from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.explain import (
    BaseExplainResult,
    SyncExplainBackendProtocol,
    AsyncExplainBackendProtocol,
    SyncExplainBackendMixin,
    AsyncExplainBackendMixin,
)
from rhosocial.activerecord.backend.expression.core import TableExpression, WildcardExpression
from rhosocial.activerecord.backend.expression.statements import (
    ExplainOptions,
    ExplainType,
    QueryExpression,
)
from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteBackend,
    SQLiteExplainRow,
    SQLiteExplainQueryPlanRow,
    SQLiteExplainResult,
    SQLiteExplainQueryPlanResult,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def dialect():
    return SQLiteDialect()


@pytest.fixture()
def sync_backend():
    """In-memory SQLite backend with a single test table."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.execute(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    yield backend
    backend.disconnect()


@pytest.fixture()
def query_expr(dialect):
    """Simple SELECT * FROM items expression."""
    return QueryExpression(
        dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, "items"),
    )


# ---------------------------------------------------------------------------
# Protocol / MRO tests
# ---------------------------------------------------------------------------

class TestMixinAndProtocol:
    def test_sync_backend_is_mixin_instance(self, sync_backend):
        assert isinstance(sync_backend, SyncExplainBackendMixin)

    def test_sync_backend_satisfies_protocol(self, sync_backend):
        assert isinstance(sync_backend, SyncExplainBackendProtocol)

    def test_async_backend_class_is_mixin_instance(self):
        try:
            from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        except ImportError:
            pytest.skip("aiosqlite not installed")
        assert issubclass(AsyncSQLiteBackend, AsyncExplainBackendMixin)


# ---------------------------------------------------------------------------
# EXPLAIN (bytecode) tests
# ---------------------------------------------------------------------------

class TestExplainBytecode:
    def test_returns_sqlite_explain_result(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        assert isinstance(result, SQLiteExplainResult)

    def test_result_is_base_explain_result(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        assert isinstance(result, BaseExplainResult)

    def test_rows_are_sqlite_explain_row(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        assert len(result.rows) > 0
        for row in result.rows:
            assert isinstance(row, SQLiteExplainRow)

    def test_row_fields_types(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        row = result.rows[0]
        assert isinstance(row.addr, int)
        assert isinstance(row.opcode, str)
        assert isinstance(row.p1, int)
        assert isinstance(row.p2, int)
        assert isinstance(row.p3, int)
        assert row.p4 is None or isinstance(row.p4, str)
        assert isinstance(row.p5, int)
        assert row.comment is None or isinstance(row.comment, str)

    def test_sql_field_starts_with_explain(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        assert result.sql.upper().startswith("EXPLAIN ")
        assert "QUERY PLAN" not in result.sql.upper()

    def test_raw_rows_matches_rows(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        assert len(result.raw_rows) == len(result.rows)

    def test_duration_is_non_negative(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr)
        assert result.duration >= 0.0

    def test_explicit_none_options(self, sync_backend, query_expr):
        result = sync_backend.explain(query_expr, None)
        assert isinstance(result, SQLiteExplainResult)

    def test_first_opcode_is_init(self, sync_backend, query_expr):
        """SQLite always starts bytecode programs with the Init opcode."""
        result = sync_backend.explain(query_expr)
        assert result.rows[0].opcode == "Init"


# ---------------------------------------------------------------------------
# EXPLAIN QUERY PLAN tests
# ---------------------------------------------------------------------------

class TestExplainQueryPlan:
    @pytest.fixture()
    def qp_options(self):
        return ExplainOptions(type=ExplainType.QUERY_PLAN)

    def test_returns_sqlite_explain_query_plan_result(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        assert isinstance(result, SQLiteExplainQueryPlanResult)

    def test_result_is_base_explain_result(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        assert isinstance(result, BaseExplainResult)

    def test_rows_are_sqlite_query_plan_row(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        assert len(result.rows) > 0
        for row in result.rows:
            assert isinstance(row, SQLiteExplainQueryPlanRow)

    def test_row_fields_types(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        row = result.rows[0]
        assert isinstance(row.id, int)
        assert isinstance(row.parent, int)
        assert isinstance(row.notused, int)
        assert isinstance(row.detail, str)

    def test_detail_contains_scan_or_search(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        assert any(
            kw in row.detail.upper() for row in result.rows for kw in ("SCAN", "SEARCH", "USE")
        )

    def test_sql_field_starts_with_explain_query_plan(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        assert result.sql.upper().startswith("EXPLAIN QUERY PLAN ")

    def test_raw_rows_matches_rows(self, sync_backend, query_expr, qp_options):
        result = sync_backend.explain(query_expr, qp_options)
        assert len(result.raw_rows) == len(result.rows)


# ---------------------------------------------------------------------------
# Async backend tests
# ---------------------------------------------------------------------------

class TestAsyncExplain:
    @pytest.fixture()
    async def async_backend(self):
        try:
            from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        except ImportError:
            pytest.skip("aiosqlite not installed")
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        await backend.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_explain_returns_sqlite_explain_result(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert isinstance(result, SQLiteExplainResult)
        assert len(result.rows) > 0

    @pytest.mark.asyncio
    async def test_async_explain_query_plan(self, async_backend, query_expr):
        opts = ExplainOptions(type=ExplainType.QUERY_PLAN)
        result = await async_backend.explain(query_expr, opts)
        assert isinstance(result, SQLiteExplainQueryPlanResult)
        assert len(result.rows) > 0

    @pytest.mark.asyncio
    async def test_async_backend_satisfies_protocol(self, async_backend):
        assert isinstance(async_backend, AsyncExplainBackendProtocol)


# ---------------------------------------------------------------------------
# Index-usage analysis — bytecode (SQLiteExplainResult)
# ---------------------------------------------------------------------------

class TestExplainBytecodeIndexAnalysis:
    """Tests for SQLiteExplainResult.analyze_index_usage() and related properties.

    The in-memory backend is set up with:
    - A table ``orders`` with an index on ``status``.
    - A table ``order_items`` with an index on ``(order_id, sku)``
      (composite, so SELECT sku … WHERE order_id=? is a covering-index query).

    Full-scan baseline: SELECT * FROM orders (no WHERE clause).
    Index-with-lookup:  SELECT * FROM orders WHERE status = ?
    Covering-index:     SELECT sku FROM order_items WHERE order_id = ?
    """

    @pytest.fixture()
    def indexed_backend(self):
        backend = SQLiteBackend(database=":memory:")
        backend.connect()
        backend.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, total REAL)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        backend.execute(
            "CREATE INDEX idx_orders_status ON orders(status)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        backend.execute(
            "CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, sku TEXT, qty INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        backend.execute(
            "CREATE INDEX idx_items_order_sku ON order_items(order_id, sku)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        yield backend
        backend.disconnect()

    @pytest.fixture()
    def full_scan_result(self, indexed_backend, dialect):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders")
        return indexed_backend.explain(expr)

    @pytest.fixture()
    def index_lookup_result(self, indexed_backend, dialect):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders WHERE status = 'pending'")
        return indexed_backend.explain(expr)

    @pytest.fixture()
    def covering_index_result(self, indexed_backend, dialect):
        expr = RawSQLExpression(dialect, "SELECT sku FROM order_items WHERE order_id = 1")
        return indexed_backend.explain(expr)

    # --- full scan ---

    def test_full_scan_analyze(self, full_scan_result):
        assert full_scan_result.analyze_index_usage() == "full_scan"

    def test_full_scan_is_full_scan_true(self, full_scan_result):
        assert full_scan_result.is_full_scan is True

    def test_full_scan_is_index_used_false(self, full_scan_result):
        assert full_scan_result.is_index_used is False

    def test_full_scan_is_covering_index_false(self, full_scan_result):
        assert full_scan_result.is_covering_index is False

    # --- index with lookup ---

    def test_index_lookup_analyze(self, index_lookup_result):
        assert index_lookup_result.analyze_index_usage() == "index_with_lookup"

    def test_index_lookup_is_full_scan_false(self, index_lookup_result):
        assert index_lookup_result.is_full_scan is False

    def test_index_lookup_is_index_used_true(self, index_lookup_result):
        assert index_lookup_result.is_index_used is True

    def test_index_lookup_is_covering_index_false(self, index_lookup_result):
        assert index_lookup_result.is_covering_index is False

    # --- covering index ---

    def test_covering_index_analyze(self, covering_index_result):
        assert covering_index_result.analyze_index_usage() == "covering_index"

    def test_covering_index_is_full_scan_false(self, covering_index_result):
        assert covering_index_result.is_full_scan is False

    def test_covering_index_is_index_used_true(self, covering_index_result):
        assert covering_index_result.is_index_used is True

    def test_covering_index_is_covering_index_true(self, covering_index_result):
        assert covering_index_result.is_covering_index is True


# ---------------------------------------------------------------------------
# Index-usage analysis — query plan (SQLiteExplainQueryPlanResult)
# ---------------------------------------------------------------------------

class TestExplainQueryPlanIndexAnalysis:
    """Tests for SQLiteExplainQueryPlanResult.analyze_index_usage() and properties.

    Same schema as TestExplainBytecodeIndexAnalysis; uses EXPLAIN QUERY PLAN.
    """

    @pytest.fixture()
    def indexed_backend(self):
        backend = SQLiteBackend(database=":memory:")
        backend.connect()
        backend.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, total REAL)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        backend.execute(
            "CREATE INDEX idx_orders_status ON orders(status)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        backend.execute(
            "CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, sku TEXT, qty INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        backend.execute(
            "CREATE INDEX idx_items_order_sku ON order_items(order_id, sku)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        yield backend
        backend.disconnect()

    @pytest.fixture()
    def qp_opts(self):
        return ExplainOptions(type=ExplainType.QUERY_PLAN)

    @pytest.fixture()
    def full_scan_result(self, indexed_backend, dialect, qp_opts):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders")
        return indexed_backend.explain(expr, qp_opts)

    @pytest.fixture()
    def index_lookup_result(self, indexed_backend, dialect, qp_opts):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders WHERE status = 'pending'")
        return indexed_backend.explain(expr, qp_opts)

    @pytest.fixture()
    def covering_index_result(self, indexed_backend, dialect, qp_opts):
        expr = RawSQLExpression(dialect, "SELECT sku FROM order_items WHERE order_id = 1")
        return indexed_backend.explain(expr, qp_opts)

    # --- full scan ---

    def test_full_scan_analyze(self, full_scan_result):
        assert full_scan_result.analyze_index_usage() == "full_scan"

    def test_full_scan_is_full_scan_true(self, full_scan_result):
        assert full_scan_result.is_full_scan is True

    def test_full_scan_is_index_used_false(self, full_scan_result):
        assert full_scan_result.is_index_used is False

    def test_full_scan_is_covering_index_false(self, full_scan_result):
        assert full_scan_result.is_covering_index is False

    # --- index with lookup ---

    def test_index_lookup_analyze(self, index_lookup_result):
        assert index_lookup_result.analyze_index_usage() == "index_with_lookup"

    def test_index_lookup_is_full_scan_false(self, index_lookup_result):
        assert index_lookup_result.is_full_scan is False

    def test_index_lookup_is_index_used_true(self, index_lookup_result):
        assert index_lookup_result.is_index_used is True

    def test_index_lookup_is_covering_index_false(self, index_lookup_result):
        assert index_lookup_result.is_covering_index is False

    # --- covering index ---

    def test_covering_index_analyze(self, covering_index_result):
        assert covering_index_result.analyze_index_usage() == "covering_index"

    def test_covering_index_is_full_scan_false(self, covering_index_result):
        assert covering_index_result.is_full_scan is False

    def test_covering_index_is_index_used_true(self, covering_index_result):
        assert covering_index_result.is_index_used is True

    def test_covering_index_is_covering_index_true(self, covering_index_result):
        assert covering_index_result.is_covering_index is True
