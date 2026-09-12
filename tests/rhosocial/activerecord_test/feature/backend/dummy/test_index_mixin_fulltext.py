# tests/rhosocial/activerecord_test/feature/backend/dummy/test_index_mixin_fulltext.py
"""Tests for IndexMixin fulltext format methods."""

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.statements.fulltext_match import FulltextMatchExpression


class TestIndexMixinFulltextFormatMethods:
    """Tests for IndexMixin fulltext-related format methods."""

    def test_format_fulltext_match_natural_language(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST in natural language mode."""
        expr = FulltextMatchExpression(dummy_dialect, columns=["title", "content"], search_term="database")
        sql, params = dummy_dialect.format_fulltext_match(expr)

        assert 'MATCH("title", "content")' in sql
        assert "AGAINST" in sql
        assert "NATURAL LANGUAGE MODE" in sql
        assert params == ("database",)

    def test_format_fulltext_match_boolean_mode(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST in boolean mode."""
        expr = FulltextMatchExpression(
            dummy_dialect, columns=["content"], search_term="+python -java", mode="BOOLEAN"
        )
        sql, params = dummy_dialect.format_fulltext_match(expr)

        assert 'MATCH("content")' in sql
        assert "AGAINST" in sql
        assert "BOOLEAN MODE" in sql
        assert params == ("+python -java",)

    def test_format_fulltext_match_query_expansion(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST with query expansion."""
        expr = FulltextMatchExpression(
            dummy_dialect, columns=["title"], search_term="database", mode="QUERY EXPANSION"
        )
        sql, params = dummy_dialect.format_fulltext_match(expr)

        assert 'MATCH("title")' in sql
        assert "AGAINST" in sql
        assert "QUERY EXPANSION" in sql
        assert params == ("database",)

    def test_format_fulltext_match_with_query_expansion(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST with 'WITH QUERY EXPANSION' mode string."""
        expr = FulltextMatchExpression(
            dummy_dialect, columns=["content"], search_term="search", mode="WITH QUERY EXPANSION"
        )
        sql, params = dummy_dialect.format_fulltext_match(expr)

        assert 'MATCH("content")' in sql
        assert "QUERY EXPANSION" in sql
        assert params == ("search",)

    def test_format_fulltext_match_multiple_columns(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH with multiple columns."""
        expr = FulltextMatchExpression(
            dummy_dialect, columns=["title", "description", "tags"], search_term="python programming"
        )
        sql, params = dummy_dialect.format_fulltext_match(expr)

        assert '"title"' in sql
        assert '"description"' in sql
        assert '"tags"' in sql
        assert "MATCH" in sql
        assert params == ("python programming",)

    def test_format_fulltext_match_single_column(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH with single column."""
        expr = FulltextMatchExpression(dummy_dialect, columns=["content"], search_term="test")
        sql, params = dummy_dialect.format_fulltext_match(expr)

        assert 'MATCH("content")' in sql
        assert "AGAINST" in sql
        assert params == ("test",)
