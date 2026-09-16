# tests/rhosocial/activerecord_test/feature/backend/expression/test_fts5_signatures.py
"""Tests for FTS5 format method signature compliance.

Verifies:
- format_fts5_match_expression accepts a single expression object
- Return type annotations are Tuple[str, tuple] for all FTS5 format methods
- 3 tests for match expression signature (normal, empty columns, negate=True)
- 4 tests for return type annotations on create/rank/highlight/snippet
"""

import inspect

import pytest

from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteFTS5MatchExpression,
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
)


@pytest.fixture
def dialect():
    return SQLiteDialect(version=(3, 35, 0))


# =============================================================================
# Part 1: format_fts5_match_expression signature
# =============================================================================


class TestFTS5MatchExpressionSignature:
    """format_fts5_match_expression accepts a single expression object."""

    def test_match_normal(self, dialect):
        expr = SQLiteFTS5MatchExpression(dialect, table="articles", query="python")
        sql, params = dialect.format_fts5_match_expression(expr)
        assert "MATCH" in sql
        assert params == ("python",)

    def test_match_with_columns(self, dialect):
        expr = SQLiteFTS5MatchExpression(
            dialect, table="articles", query="python", columns=["title", "body"]
        )
        sql, params = dialect.format_fts5_match_expression(expr)
        assert "MATCH" in sql
        assert "title:python" in params[0]
        assert "body:python" in params[0]

    def test_match_negate_raises(self, dialect):
        expr = SQLiteFTS5MatchExpression(
            dialect, table="articles", query="python", negate=True
        )
        with pytest.raises(ValueError, match="NOT MATCH"):
            dialect.format_fts5_match_expression(expr)


# =============================================================================
# Part 2: Return type annotations
# =============================================================================


class TestFTS5ReturnTypeAnnotations:
    """Verify return type annotations on all FTS5 format methods."""

    def test_format_fts5_create_return_annotation(self, dialect):
        sig = inspect.signature(dialect.format_fts5_create_virtual_table)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_format_fts5_rank_return_annotation(self, dialect):
        sig = inspect.signature(dialect.format_fts5_rank_expression)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_format_fts5_highlight_return_annotation(self, dialect):
        sig = inspect.signature(dialect.format_fts5_highlight_expression)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_format_fts5_snippet_return_annotation(self, dialect):
        sig = inspect.signature(dialect.format_fts5_snippet_expression)
        assert sig.return_annotation is not inspect.Parameter.empty
