# tests/rhosocial/activerecord_test/feature/backend/query/test_explain_backend_async.py
"""Async twin of test_explain_backend.py: AsyncSQLiteBackend.explain() returns the same typed result structure as sync."""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.explain import (
    BaseExplainResult,
    AsyncExplainBackendProtocol,
    AsyncExplainBackendMixin,
)
from rhosocial.activerecord.backend.expression.core import TableExpression, WildcardExpression
from rhosocial.activerecord.backend.expression.statements import (
    ExplainOptions,
    ExplainType,
    QueryExpression,
)
from rhosocial.activerecord.backend.impl.sqlite import (
    AsyncSQLiteBackend,
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


@pytest_asyncio.fixture()
async def async_backend():
    """In-memory AsyncSQLiteBackend with a single test table."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    await backend.execute(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    yield backend
    await backend.disconnect()


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


class TestAsyncMixinAndProtocol:
    @pytest.mark.asyncio
    async def test_sync_backend_is_mixin_instance(self, async_backend):
        assert isinstance(async_backend, AsyncExplainBackendMixin)

    @pytest.mark.asyncio
    async def test_sync_backend_satisfies_protocol(self, async_backend):
        assert isinstance(async_backend, AsyncExplainBackendProtocol)

    def test_async_backend_class_is_mixin_instance(self):
        try:
            from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend as Impl
        except ImportError:
            pytest.skip("aiosqlite not installed")
        assert issubclass(Impl, AsyncExplainBackendMixin)


# ---------------------------------------------------------------------------
# EXPLAIN (bytecode) tests
# ---------------------------------------------------------------------------


class TestAsyncExplainBytecode:
    @pytest.mark.asyncio
    async def test_returns_sqlite_explain_result(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert isinstance(result, SQLiteExplainResult)

    @pytest.mark.asyncio
    async def test_result_is_base_explain_result(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert isinstance(result, BaseExplainResult)

    @pytest.mark.asyncio
    async def test_rows_are_sqlite_explain_row(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert len(result.rows) > 0
        for row in result.rows:
            assert isinstance(row, SQLiteExplainRow)

    @pytest.mark.asyncio
    async def test_row_fields_types(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        row = result.rows[0]
        assert isinstance(row.addr, int)
        assert isinstance(row.opcode, str)
        assert isinstance(row.p1, int)
        assert isinstance(row.p2, int)
        assert isinstance(row.p3, int)
        assert row.p4 is None or isinstance(row.p4, str)
        assert isinstance(row.p5, int)
        assert row.comment is None or isinstance(row.comment, str)

    @pytest.mark.asyncio
    async def test_sql_field_starts_with_explain(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert result.sql.upper().startswith("EXPLAIN ")
        assert "QUERY PLAN" not in result.sql.upper()

    @pytest.mark.asyncio
    async def test_raw_rows_matches_rows(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert len(result.raw_rows) == len(result.rows)

    @pytest.mark.asyncio
    async def test_duration_is_non_negative(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr)
        assert result.duration >= 0.0

    @pytest.mark.asyncio
    async def test_explicit_none_options(self, async_backend, query_expr):
        result = await async_backend.explain(query_expr, None)
        assert isinstance(result, SQLiteExplainResult)

    @pytest.mark.asyncio
    async def test_first_opcode_is_init(self, async_backend, query_expr):
        """SQLite always starts bytecode programs with the Init opcode."""
        result = await async_backend.explain(query_expr)
        assert result.rows[0].opcode == "Init"


# ---------------------------------------------------------------------------
# EXPLAIN QUERY PLAN tests
# ---------------------------------------------------------------------------


class TestAsyncExplainQueryPlan:
    @pytest.fixture()
    def qp_options(self):
        return ExplainOptions(type=ExplainType.QUERY_PLAN)

    @pytest.mark.asyncio
    async def test_returns_sqlite_explain_query_plan_result(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        assert isinstance(result, SQLiteExplainQueryPlanResult)

    @pytest.mark.asyncio
    async def test_result_is_base_explain_result(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        assert isinstance(result, BaseExplainResult)

    @pytest.mark.asyncio
    async def test_rows_are_sqlite_query_plan_row(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        assert len(result.rows) > 0
        for row in result.rows:
            assert isinstance(row, SQLiteExplainQueryPlanRow)

    @pytest.mark.asyncio
    async def test_row_fields_types(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        row = result.rows[0]
        assert isinstance(row.id, int)
        assert isinstance(row.parent, int)
        assert isinstance(row.notused, int)
        assert isinstance(row.detail, str)

    @pytest.mark.asyncio
    async def test_detail_contains_scan_or_search(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        assert any(kw in row.detail.upper() for row in result.rows for kw in ("SCAN", "SEARCH", "USE"))

    @pytest.mark.asyncio
    async def test_sql_field_starts_with_explain_query_plan(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        assert result.sql.upper().startswith("EXPLAIN QUERY PLAN ")

    @pytest.mark.asyncio
    async def test_raw_rows_matches_rows(self, async_backend, query_expr, qp_options):
        result = await async_backend.explain(query_expr, qp_options)
        assert len(result.raw_rows) == len(result.rows)


# ---------------------------------------------------------------------------
# Async backend tests
# ---------------------------------------------------------------------------


class TestAsyncAsyncExplain:
    @pytest_asyncio.fixture()
    async def async_backend(self):
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


class TestAsyncExplainBytecodeIndexAnalysis:
    """Tests for SQLiteExplainResult.analyze_index_usage() via AsyncSQLiteBackend.

    The in-memory backend is set up with:
    - A table ``orders`` with an index on ``status``.
    - A table ``order_items`` with an index on ``(order_id, sku)``.

    Full-scan baseline: SELECT * FROM orders (no WHERE clause).
    Index-with-lookup:  SELECT * FROM orders WHERE status = ?
    Covering-index:     SELECT sku FROM order_items WHERE order_id = ?
    """

    @pytest_asyncio.fixture()
    async def indexed_backend(self):
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        await backend.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, total REAL)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "CREATE INDEX idx_orders_status ON orders(status)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, sku TEXT, qty INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "CREATE INDEX idx_items_order_sku ON order_items(order_id, sku)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        yield backend
        await backend.disconnect()

    @pytest_asyncio.fixture()
    async def full_scan_result(self, indexed_backend, dialect):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders")
        return await indexed_backend.explain(expr)

    @pytest_asyncio.fixture()
    async def index_lookup_result(self, indexed_backend, dialect):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders WHERE status = 'pending'")
        return await indexed_backend.explain(expr)

    @pytest_asyncio.fixture()
    async def covering_index_result(self, indexed_backend, dialect):
        expr = RawSQLExpression(dialect, "SELECT sku FROM order_items WHERE order_id = 1")
        return await indexed_backend.explain(expr)

    # --- full scan ---

    @pytest.mark.asyncio
    async def test_full_scan_analyze(self, full_scan_result):
        assert full_scan_result.analyze_index_usage() == "full_scan"

    @pytest.mark.asyncio
    async def test_full_scan_is_full_scan_true(self, full_scan_result):
        assert full_scan_result.is_full_scan is True

    @pytest.mark.asyncio
    async def test_full_scan_is_index_used_false(self, full_scan_result):
        assert full_scan_result.is_index_used is False

    @pytest.mark.asyncio
    async def test_full_scan_is_covering_index_false(self, full_scan_result):
        assert full_scan_result.is_covering_index is False

    # --- index with lookup ---

    @pytest.mark.asyncio
    async def test_index_lookup_analyze(self, index_lookup_result):
        assert index_lookup_result.analyze_index_usage() == "index_with_lookup"

    @pytest.mark.asyncio
    async def test_index_lookup_is_full_scan_false(self, index_lookup_result):
        assert index_lookup_result.is_full_scan is False

    @pytest.mark.asyncio
    async def test_index_lookup_is_index_used_true(self, index_lookup_result):
        assert index_lookup_result.is_index_used is True

    @pytest.mark.asyncio
    async def test_index_lookup_is_covering_index_false(self, index_lookup_result):
        assert index_lookup_result.is_covering_index is False

    # --- covering index ---

    @pytest.mark.asyncio
    async def test_covering_index_analyze(self, covering_index_result):
        assert covering_index_result.analyze_index_usage() == "covering_index"

    @pytest.mark.asyncio
    async def test_covering_index_is_full_scan_false(self, covering_index_result):
        assert covering_index_result.is_full_scan is False

    @pytest.mark.asyncio
    async def test_covering_index_is_index_used_true(self, covering_index_result):
        assert covering_index_result.is_index_used is True

    @pytest.mark.asyncio
    async def test_covering_index_is_covering_index_true(self, covering_index_result):
        assert covering_index_result.is_covering_index is True


# ---------------------------------------------------------------------------
# Index-usage analysis — query plan (SQLiteExplainQueryPlanResult)
# ---------------------------------------------------------------------------


class TestAsyncExplainQueryPlanIndexAnalysis:
    """Tests for SQLiteExplainQueryPlanResult.analyze_index_usage() via AsyncSQLiteBackend (EXPLAIN QUERY PLAN)."""

    @pytest_asyncio.fixture()
    async def indexed_backend(self):
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        await backend.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, total REAL)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "CREATE INDEX idx_orders_status ON orders(status)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, sku TEXT, qty INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "CREATE INDEX idx_items_order_sku ON order_items(order_id, sku)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        yield backend
        await backend.disconnect()

    @pytest.fixture()
    def qp_opts(self):
        return ExplainOptions(type=ExplainType.QUERY_PLAN)

    @pytest_asyncio.fixture()
    async def full_scan_result(self, indexed_backend, dialect, qp_opts):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders")
        return await indexed_backend.explain(expr, qp_opts)

    @pytest_asyncio.fixture()
    async def index_lookup_result(self, indexed_backend, dialect, qp_opts):
        expr = RawSQLExpression(dialect, "SELECT * FROM orders WHERE status = 'pending'")
        return await indexed_backend.explain(expr, qp_opts)

    @pytest_asyncio.fixture()
    async def covering_index_result(self, indexed_backend, dialect, qp_opts):
        expr = RawSQLExpression(dialect, "SELECT sku FROM order_items WHERE order_id = 1")
        return await indexed_backend.explain(expr, qp_opts)

    # --- full scan ---

    @pytest.mark.asyncio
    async def test_full_scan_analyze(self, full_scan_result):
        assert full_scan_result.analyze_index_usage() == "full_scan"

    @pytest.mark.asyncio
    async def test_full_scan_is_full_scan_true(self, full_scan_result):
        assert full_scan_result.is_full_scan is True

    @pytest.mark.asyncio
    async def test_full_scan_is_index_used_false(self, full_scan_result):
        assert full_scan_result.is_index_used is False

    @pytest.mark.asyncio
    async def test_full_scan_is_covering_index_false(self, full_scan_result):
        assert full_scan_result.is_covering_index is False

    # --- index with lookup ---

    @pytest.mark.asyncio
    async def test_index_lookup_analyze(self, index_lookup_result):
        assert index_lookup_result.analyze_index_usage() == "index_with_lookup"

    @pytest.mark.asyncio
    async def test_index_lookup_is_full_scan_false(self, index_lookup_result):
        assert index_lookup_result.is_full_scan is False

    @pytest.mark.asyncio
    async def test_index_lookup_is_index_used_true(self, index_lookup_result):
        assert index_lookup_result.is_index_used is True

    @pytest.mark.asyncio
    async def test_index_lookup_is_covering_index_false(self, index_lookup_result):
        assert index_lookup_result.is_covering_index is False

    # --- covering index ---

    @pytest.mark.asyncio
    async def test_covering_index_analyze(self, covering_index_result):
        assert covering_index_result.analyze_index_usage() == "covering_index"

    @pytest.mark.asyncio
    async def test_covering_index_is_full_scan_false(self, covering_index_result):
        assert covering_index_result.is_full_scan is False

    @pytest.mark.asyncio
    async def test_covering_index_is_index_used_true(self, covering_index_result):
        assert covering_index_result.is_index_used is True

    @pytest.mark.asyncio
    async def test_covering_index_is_covering_index_true(self, covering_index_result):
        assert covering_index_result.is_covering_index is True
