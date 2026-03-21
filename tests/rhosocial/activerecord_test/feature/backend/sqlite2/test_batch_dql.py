# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_batch_dql.py
"""
Integration tests for execute_batch_dql with real SQLite backend.

Tests cover:
  - fetchmany pagination with various page_size / row_count combinations
  - Cursor lifecycle: normal consumption, early break, exception
  - Column adapter and column mapping processing
  - DQLExpression type coverage: QueryExpression, WithQueryExpression, SetOperationExpression

For async tests, see sqlite_async/test_batch_dql.py.
"""
import pytest

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


@pytest.fixture
def backend_with_items(sqlite_backend):
    """SQLite backend with items table + 100 rows."""
    sqlite_backend.executescript(CREATE_ITEMS_SQL)
    sqlite_backend.executescript(_seed_items_sql(100))
    return sqlite_backend


@pytest.fixture
def backend_with_empty_table(sqlite_backend):
    """SQLite backend with items table, 0 rows."""
    sqlite_backend.executescript(CREATE_ITEMS_SQL)
    return sqlite_backend


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


def _collect_pages(iterator):
    """Consume Iterator[BatchDQLResult] into list."""
    return list(iterator)


# ══════════════════════════════════════════════
# Sync: Pagination
# ══════════════════════════════════════════════

class TestBatchDQLPagination:
    """Tests fetchmany pagination behavior."""

    @pytest.mark.parametrize("page_size, expected_pages, last_page_size", [
        pytest.param(25, 4, 25, id="exact_4_pages"),
        pytest.param(30, 4, 10, id="uneven_30_30_30_10"),
        pytest.param(200, 1, 100, id="single_page_oversized"),
        pytest.param(1, 100, 1, id="page_size_1"),
        pytest.param(100, 1, 100, id="exact_one_page"),
        pytest.param(99, 2, 1, id="just_over_one_page"),
    ])
    def test_page_counts(self, backend_with_items, page_size, expected_pages, last_page_size):
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=page_size)
        )

        assert len(pages) == expected_pages
        # Last page size
        assert pages[-1].page_size == last_page_size
        # Total rows
        total = sum(p.page_size for p in pages)
        assert total == 100

    def test_page_index_increments(self, backend_with_items):
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=30)
        )

        assert [p.page_index for p in pages] == [0, 1, 2, 3]

    def test_has_more_flag(self, backend_with_items):
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=30)
        )

        # First 3 pages: has_more=True; last page: has_more=False
        for p in pages[:-1]:
            assert p.has_more is True
        assert pages[-1].has_more is False

    def test_empty_result_no_yield(self, backend_with_empty_table):
        dialect = backend_with_empty_table.dialect
        expr = _select_all_expr(dialect)

        pages = _collect_pages(
            backend_with_empty_table.execute_batch_dql(expr, page_size=10)
        )

        assert pages == []

    def test_data_content_correct(self, backend_with_items):
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=50)
        )

        first_row = pages[0].data[0]
        assert "id" in first_row
        assert "name" in first_row
        assert "category" in first_row
        assert "price" in first_row
        assert first_row["id"] == 1
        assert first_row["name"] == "item0"

    def test_filtered_query(self, backend_with_items):
        """WHERE clause reduces result set."""
        dialect = backend_with_items.dialect
        expr = _select_where_expr(dialect, "electronics")

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=50)
        )

        total = sum(p.page_size for p in pages)
        # 100 items, 3 categories, ~34 electronics
        assert 33 <= total <= 34
        for p in pages:
            for row in p.data:
                assert row["category"] == "electronics"


# ══════════════════════════════════════════════
# Sync: Cursor lifecycle
# ══════════════════════════════════════════════

class TestBatchDQLCursorLifecycle:
    """Tests that cursor is properly closed in all scenarios."""

    def test_normal_consume_then_new_query(self, backend_with_items):
        """After full consumption, backend should accept new queries."""
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=50)
        )
        assert len(pages) == 2

        # New query should work fine (no dangling cursor)
        result = backend_with_items.execute(
            "SELECT COUNT(*) as cnt FROM items", None,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["cnt"] == 100

    def test_early_break_then_new_query(self, backend_with_items):
        """After break, cursor should be closed via generator finally."""
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        consumed = 0
        for page in backend_with_items.execute_batch_dql(expr, page_size=10):
            consumed += 1
            if consumed == 2:
                break
        assert consumed == 2

        # New query should work (cursor was cleaned up)
        result = backend_with_items.execute(
            "SELECT COUNT(*) as cnt FROM items", None,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["cnt"] == 100

    def test_immediate_break(self, backend_with_items):
        """Break before consuming any page."""
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        for page in backend_with_items.execute_batch_dql(expr, page_size=10):
            break  # Immediately

        # Backend still usable
        assert _count_rows_dql(backend_with_items) == 100

    def test_exception_in_consumer(self, backend_with_items):
        """Consumer raises — cursor should still be cleaned up."""
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)

        with pytest.raises(RuntimeError, match="test error"):
            for page in backend_with_items.execute_batch_dql(expr, page_size=10):
                raise RuntimeError("test error")

        # Backend still usable
        assert _count_rows_dql(backend_with_items) == 100


def _count_rows_dql(backend):
    result = backend.execute(
        "SELECT COUNT(*) as cnt FROM items", None,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    return result.data[0]["cnt"]


# ══════════════════════════════════════════════
# Sync: DQLExpression type coverage
# ══════════════════════════════════════════════

class TestBatchDQLExpressionTypes:
    """Tests that all DQLExpression variants work with execute_batch_dql."""

    def test_query_expression(self, backend_with_items):
        """Basic QueryExpression."""
        dialect = backend_with_items.dialect
        expr = _select_all_expr(dialect)
        pages = _collect_pages(
            backend_with_items.execute_batch_dql(expr, page_size=50)
        )
        assert sum(p.page_size for p in pages) == 100

    def test_with_query_expression_cte(self, backend_with_items):
        """WithQueryExpression (CTE)."""
        dialect = backend_with_items.dialect

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

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(with_expr, page_size=20)
        )

        total = sum(p.page_size for p in pages)
        assert total > 0
        for p in pages:
            for row in p.data:
                assert row["price"] > 50.0

    def test_set_operation_expression(self, backend_with_items):
        """SetOperationExpression (UNION)."""
        dialect = backend_with_items.dialect

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

        pages = _collect_pages(
            backend_with_items.execute_batch_dql(union_expr, page_size=20)
        )

        total = sum(p.page_size for p in pages)
        # electronics (~34) + books (~33) = ~67
        assert 65 <= total <= 68
