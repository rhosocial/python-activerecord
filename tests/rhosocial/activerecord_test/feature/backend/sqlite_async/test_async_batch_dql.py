# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_batch_dql.py
"""
Integration tests for execute_batch_dql with real async SQLite backend.

Tests cover:
  - fetchmany pagination with various page_size / row_count combinations
  - Cursor lifecycle: normal consumption, early break, exception
  - Column adapter and column mapping processing
  - DQLExpression type coverage: QueryExpression, WithQueryExpression, SetOperationExpression
"""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, WildcardExpression,
    ComparisonPredicate, SetOperationExpression,
)
from rhosocial.activerecord.backend.expression.statements import QueryExpression
from rhosocial.activerecord.backend.expression.query_sources import (
    WithQueryExpression, CTEExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import (
    WhereClause, OrderByClause, LimitOffsetClause,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

CREATE_ITEMS_SQL = """
    CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    );
"""


def _seed_items_sql(n):
    """Generate INSERT statements for n items."""
    stmts = []
    categories = ["electronics", "books", "clothing"]
    for i in range(n):
        cat = categories[i % len(categories)]
        stmts.append(f"INSERT INTO items (name, category, price) VALUES ('item{i}', '{cat}', {10.0 + i});")
    return "\n".join(stmts)


@pytest_asyncio.fixture
async def async_backend_with_items(async_sqlite_backend):
    """Async SQLite backend with items table + 100 rows."""
    await async_sqlite_backend.executescript(CREATE_ITEMS_SQL)
    await async_sqlite_backend.executescript(_seed_items_sql(100))
    return async_sqlite_backend


@pytest_asyncio.fixture
async def async_backend_with_empty_table(async_sqlite_backend):
    """Async SQLite backend with items table, 0 rows."""
    await async_sqlite_backend.executescript(CREATE_ITEMS_SQL)
    return async_sqlite_backend


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _select_all_expr(dialect, table="items", order_col="id"):
    """Build: SELECT * FROM items ORDER BY id"""
    return QueryExpression(
        dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, table),
        order_by=OrderByClause(dialect, expressions=[(Column(dialect, order_col), "ASC")]),
    )


def _select_where_expr(dialect, category):
    """Build: SELECT * FROM items WHERE category = ? ORDER BY id"""
    return QueryExpression(
        dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, "items"),
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "category"), Literal(dialect, category)),
        ),
        order_by=OrderByClause(dialect, expressions=[(Column(dialect, "id"), "ASC")]),
    )


async def _async_collect_pages(async_iterator):
    """Consume AsyncIterator[BatchDQLResult] into list."""
    pages = []
    async for page in async_iterator:
        pages.append(page)
    return pages


async def _async_count_rows_dql(backend):
    result = await backend.execute(
        "SELECT COUNT(*) as cnt FROM items", None,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    return result.data[0]["cnt"]


# ══════════════════════════════════════════════
# Async: Pagination
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDQLPagination:
    """Async pagination tests."""

    @pytest.mark.parametrize("page_size, expected_pages, last_page_size", [
        pytest.param(25, 4, 25, id="exact_4_pages"),
        pytest.param(30, 4, 10, id="uneven_30_30_30_10"),
        pytest.param(200, 1, 100, id="single_page_oversized"),
        pytest.param(1, 100, 1, id="page_size_1"),
        pytest.param(100, 1, 100, id="exact_one_page"),
        pytest.param(99, 2, 1, id="just_over_one_page"),
    ])
    async def test_page_counts(self, async_backend_with_items, page_size, expected_pages, last_page_size):
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=page_size)
        )

        assert len(pages) == expected_pages
        # Last page size
        assert pages[-1].page_size == last_page_size
        # Total rows
        total = sum(p.page_size for p in pages)
        assert total == 100

    async def test_page_index_increments(self, async_backend_with_items):
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=30)
        )

        assert [p.page_index for p in pages] == [0, 1, 2, 3]

    async def test_has_more_flag(self, async_backend_with_items):
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=30)
        )

        # First 3 pages: has_more=True; last page: has_more=False
        for p in pages[:-1]:
            assert p.has_more is True
        assert pages[-1].has_more is False

    async def test_empty_result_no_yield(self, async_backend_with_empty_table):
        dialect = async_backend_with_empty_table.dialect
        expr = _select_all_expr(dialect)

        pages = await _async_collect_pages(
            async_backend_with_empty_table.execute_batch_dql(expr, page_size=10)
        )

        assert pages == []

    async def test_data_content_correct(self, async_backend_with_items):
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=50)
        )

        first_row = pages[0].data[0]
        assert "id" in first_row
        assert "name" in first_row
        assert "category" in first_row
        assert "price" in first_row
        assert first_row["id"] == 1
        assert first_row["name"] == "item0"

    async def test_filtered_query(self, async_backend_with_items):
        """WHERE clause reduces result set."""
        dialect = async_backend_with_items.dialect
        expr = _select_where_expr(dialect, "electronics")

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=50)
        )

        total = sum(p.page_size for p in pages)
        # 100 items, 3 categories, ~34 electronics
        assert 33 <= total <= 34
        for p in pages:
            for row in p.data:
                assert row["category"] == "electronics"


# ══════════════════════════════════════════════
# Async: Cursor lifecycle
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDQLCursorLifecycle:
    """Async cursor lifecycle tests."""

    async def test_normal_consume_then_new_query(self, async_backend_with_items):
        """After full consumption, backend should accept new queries."""
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=50)
        )
        assert len(pages) == 2

        # New query should work fine (no dangling cursor)
        result = await async_backend_with_items.execute(
            "SELECT COUNT(*) as cnt FROM items", None,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["cnt"] == 100

    async def test_early_break_then_new_query(self, async_backend_with_items):
        """After break, cursor should be closed via generator finally."""
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        consumed = 0
        async for page in async_backend_with_items.execute_batch_dql(expr, page_size=10):
            consumed += 1
            if consumed == 2:
                break
        assert consumed == 2

        # New query should work (cursor was cleaned up)
        result = await async_backend_with_items.execute(
            "SELECT COUNT(*) as cnt FROM items", None,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["cnt"] == 100

    async def test_immediate_break(self, async_backend_with_items):
        """Break before consuming any page."""
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        async for page in async_backend_with_items.execute_batch_dql(expr, page_size=10):
            break  # Immediately

        # Backend still usable
        assert await _async_count_rows_dql(async_backend_with_items) == 100

    async def test_exception_in_consumer(self, async_backend_with_items):
        """Consumer raises — cursor should still be cleaned up."""
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)

        with pytest.raises(RuntimeError, match="test error"):
            async for page in async_backend_with_items.execute_batch_dql(expr, page_size=10):
                raise RuntimeError("test error")

        # Backend still usable
        assert await _async_count_rows_dql(async_backend_with_items) == 100


# ══════════════════════════════════════════════
# Async: DQLExpression types
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDQLExpressionTypes:
    """Async expression type tests."""

    async def test_query_expression(self, async_backend_with_items):
        """Basic QueryExpression."""
        dialect = async_backend_with_items.dialect
        expr = _select_all_expr(dialect)
        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(expr, page_size=50)
        )
        assert sum(p.page_size for p in pages) == 100

    async def test_with_query_expression_cte(self, async_backend_with_items):
        """WithQueryExpression (CTE)."""
        dialect = async_backend_with_items.dialect

        # WITH expensive AS (SELECT * FROM items WHERE price > 50)
        # SELECT * FROM expensive ORDER BY id
        cte_query = QueryExpression(
            dialect,
            select=[WildcardExpression(dialect)],
            from_=TableExpression(dialect, "items"),
            where=WhereClause(
                dialect,
                condition=ComparisonPredicate(dialect, ">", Column(dialect, "price"), Literal(dialect, 50.0)),
            ),
        )
        cte = CTEExpression(dialect, name="expensive", query=cte_query)

        main_query = QueryExpression(
            dialect,
            select=[WildcardExpression(dialect)],
            from_=TableExpression(dialect, "expensive"),
            order_by=OrderByClause(dialect, expressions=[(Column(dialect, "id"), "ASC")]),
        )

        with_expr = WithQueryExpression(dialect, ctes=[cte], main_query=main_query)

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(with_expr, page_size=20)
        )

        total = sum(p.page_size for p in pages)
        assert total > 0
        for p in pages:
            for row in p.data:
                assert row["price"] > 50.0

    async def test_set_operation_expression(self, async_backend_with_items):
        """SetOperationExpression (UNION)."""
        dialect = async_backend_with_items.dialect

        left = QueryExpression(
            dialect,
            select=[Column(dialect, "name"), Column(dialect, "price")],
            from_=TableExpression(dialect, "items"),
            where=WhereClause(
                dialect,
                condition=ComparisonPredicate(dialect, "=", Column(dialect, "category"), Literal(dialect, "electronics")),
            ),
        )
        right = QueryExpression(
            dialect,
            select=[Column(dialect, "name"), Column(dialect, "price")],
            from_=TableExpression(dialect, "items"),
            where=WhereClause(
                dialect,
                condition=ComparisonPredicate(dialect, "=", Column(dialect, "category"), Literal(dialect, "books")),
            ),
        )
        union_expr = SetOperationExpression(dialect, left=left, right=right, operation="UNION ALL")

        pages = await _async_collect_pages(
            async_backend_with_items.execute_batch_dql(union_expr, page_size=20)
        )

        total = sum(p.page_size for p in pages)
        # electronics (~34) + books (~33) = ~67
        assert 65 <= total <= 68
