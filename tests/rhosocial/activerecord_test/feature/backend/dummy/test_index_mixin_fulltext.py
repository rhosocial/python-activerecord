# tests/rhosocial/activerecord_test/feature/backend/dummy/test_index_mixin_fulltext.py
"""Tests for IndexMixin fulltext format methods."""
import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestIndexMixinFulltextFormatMethods:
    """Tests for IndexMixin fulltext-related format methods."""

    def test_format_fulltext_match_natural_language(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST in natural language mode."""
        sql, params = dummy_dialect.format_fulltext_match(
            columns=["title", "content"],
            search_term="database"
        )

        assert 'MATCH("title", "content")' in sql
        assert 'AGAINST' in sql
        assert 'NATURAL LANGUAGE MODE' in sql
        assert params == ("database",)

    def test_format_fulltext_match_boolean_mode(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST in boolean mode."""
        sql, params = dummy_dialect.format_fulltext_match(
            columns=["content"],
            search_term="+python -java",
            mode="BOOLEAN"
        )

        assert 'MATCH("content")' in sql
        assert 'AGAINST' in sql
        assert 'BOOLEAN MODE' in sql
        assert params == ("+python -java",)

    def test_format_fulltext_match_query_expansion(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST with query expansion."""
        sql, params = dummy_dialect.format_fulltext_match(
            columns=["title"],
            search_term="database",
            mode="QUERY EXPANSION"
        )

        assert 'MATCH("title")' in sql
        assert 'AGAINST' in sql
        assert 'QUERY EXPANSION' in sql
        assert params == ("database",)

    def test_format_fulltext_match_with_query_expansion(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH ... AGAINST with 'WITH QUERY EXPANSION' mode string."""
        sql, params = dummy_dialect.format_fulltext_match(
            columns=["content"],
            search_term="search",
            mode="WITH QUERY EXPANSION"
        )

        assert 'MATCH("content")' in sql
        assert 'QUERY EXPANSION' in sql
        assert params == ("search",)

    def test_format_create_fulltext_index_basic(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX basic statement."""
        sql, params = dummy_dialect.format_create_fulltext_index(
            index_name="idx_articles_content",
            table_name="articles",
            columns=["title", "content"]
        )

        assert 'CREATE FULLTEXT INDEX' in sql
        assert '"idx_articles_content"' in sql
        assert 'ON' in sql
        assert '"articles"' in sql
        assert '"title"' in sql
        assert '"content"' in sql
        assert params == ()

    def test_format_create_fulltext_index_with_parser(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX with parser."""
        sql, params = dummy_dialect.format_create_fulltext_index(
            index_name="idx_content_ft",
            table_name="documents",
            columns=["content"],
            parser="ngram"
        )

        assert 'CREATE FULLTEXT INDEX' in sql
        assert 'WITH PARSER' in sql
        assert '"ngram"' in sql
        assert params == ()

    def test_format_fulltext_match_multiple_columns(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH with multiple columns."""
        sql, params = dummy_dialect.format_fulltext_match(
            columns=["title", "description", "tags"],
            search_term="python programming"
        )

        assert '"title"' in sql
        assert '"description"' in sql
        assert '"tags"' in sql
        assert 'MATCH' in sql
        assert params == ("python programming",)

    def test_format_fulltext_match_single_column(self, dummy_dialect: DummyDialect):
        """Tests FULLTEXT MATCH with single column."""
        sql, params = dummy_dialect.format_fulltext_match(
            columns=["content"],
            search_term="test"
        )

        assert 'MATCH("content")' in sql
        assert 'AGAINST' in sql
        assert params == ("test",)

    def test_format_create_fulltext_index_single_column(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX with single column."""
        sql, params = dummy_dialect.format_create_fulltext_index(
            index_name="idx_body_ft",
            table_name="posts",
            columns=["body"]
        )

        assert 'CREATE FULLTEXT INDEX' in sql
        assert '("body")' in sql
        assert params == ()
