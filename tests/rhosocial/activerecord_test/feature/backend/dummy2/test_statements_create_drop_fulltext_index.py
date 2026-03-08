# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_drop_fulltext_index.py
"""Tests for CREATE FULLTEXT INDEX and DROP FULLTEXT INDEX statements."""
import pytest
from rhosocial.activerecord.backend.expression.statements import (
    CreateFulltextIndexExpression, DropFulltextIndexExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateFulltextIndexStatements:
    """Tests for CREATE FULLTEXT INDEX statements."""

    def test_basic_create_fulltext_index(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE FULLTEXT INDEX statement."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_articles_content",
            table_name="articles",
            columns=["title", "content"]
        )
        sql, params = create_ft.to_sql()

        assert 'CREATE FULLTEXT INDEX' in sql
        assert '"idx_articles_content"' in sql
        assert 'ON' in sql
        assert '"articles"' in sql
        assert '"title"' in sql
        assert '"content"' in sql
        assert params == ()

    def test_create_fulltext_index_single_column(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX with single column."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_posts_body",
            table_name="posts",
            columns=["body"]
        )
        sql, params = create_ft.to_sql()

        assert 'CREATE FULLTEXT INDEX' in sql
        assert '"idx_posts_body"' in sql
        assert '("body")' in sql
        assert params == ()

    def test_create_fulltext_index_with_parser(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX with parser."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_documents_body",
            table_name="documents",
            columns=["body"],
            parser="ngram"
        )
        sql, params = create_ft.to_sql()

        assert 'CREATE FULLTEXT INDEX' in sql
        assert 'WITH PARSER' in sql
        assert '"ngram"' in sql
        assert params == ()

    def test_create_fulltext_index_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX IF NOT EXISTS."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_content_ft",
            table_name="content",
            columns=["text"],
            if_not_exists=True
        )
        sql, params = create_ft.to_sql()

        assert 'IF NOT EXISTS' in sql
        assert 'CREATE FULLTEXT INDEX' in sql
        assert params == ()

    def test_create_fulltext_index_multiple_columns(self, dummy_dialect: DummyDialect):
        """Tests CREATE FULLTEXT INDEX with multiple columns."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_search",
            table_name="search_table",
            columns=["title", "description", "tags", "content"]
        )
        sql, params = create_ft.to_sql()

        assert '"title"' in sql
        assert '"description"' in sql
        assert '"tags"' in sql
        assert '"content"' in sql
        assert params == ()


class TestDropFulltextIndexStatements:
    """Tests for DROP FULLTEXT INDEX statements."""

    def test_basic_drop_fulltext_index(self, dummy_dialect: DummyDialect):
        """Tests basic DROP FULLTEXT INDEX statement."""
        drop_ft = DropFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_articles_content",
            table_name="articles"
        )
        sql, params = drop_ft.to_sql()

        assert 'DROP INDEX' in sql
        assert '"idx_articles_content"' in sql
        assert 'ON' in sql
        assert '"articles"' in sql
        assert params == ()

    def test_drop_fulltext_index_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP FULLTEXT INDEX IF EXISTS."""
        drop_ft = DropFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_old_ft",
            table_name="old_table",
            if_exists=True
        )
        sql, params = drop_ft.to_sql()

        assert 'DROP INDEX' in sql
        assert 'IF EXISTS' in sql
        assert '"idx_old_ft"' in sql
        assert params == ()

    def test_drop_fulltext_index_without_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP FULLTEXT INDEX without IF EXISTS."""
        drop_ft = DropFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_content",
            table_name="posts"
        )
        sql, params = drop_ft.to_sql()

        assert 'DROP INDEX "idx_content"' in sql
        assert 'ON "posts"' in sql
        assert 'IF EXISTS' not in sql
        assert params == ()


class TestFulltextIndexRoundtrip:
    """Tests for FULLTEXT index creation and deletion roundtrip."""

    def test_fulltext_index_roundtrip(self, dummy_dialect: DummyDialect):
        """Tests creating and dropping a FULLTEXT index."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_test_ft",
            table_name="test_table",
            columns=["content"]
        )
        create_sql, create_params = create_ft.to_sql()

        drop_ft = DropFulltextIndexExpression(
            dummy_dialect,
            index_name="idx_test_ft",
            table_name="test_table"
        )
        drop_sql, drop_params = drop_ft.to_sql()

        assert 'CREATE FULLTEXT INDEX "idx_test_ft"' in create_sql
        assert 'DROP INDEX "idx_test_ft"' in drop_sql
        assert create_params == ()
        assert drop_params == ()

    @pytest.mark.parametrize("index_name,expected_identifier", [
        pytest.param("simple_ft", '"simple_ft"', id="simple_name"),
        pytest.param("ft_with_underscores", '"ft_with_underscores"', id="underscore_name"),
        pytest.param("FtWithCamelCase", '"FtWithCamelCase"', id="camelcase_name"),
        pytest.param("ft-with-hyphens", '"ft-with-hyphens"', id="hyphen_name"),
    ])
    def test_create_fulltext_index_various_names(self, dummy_dialect: DummyDialect, index_name, expected_identifier):
        """Tests CREATE FULLTEXT INDEX with various index name formats."""
        create_ft = CreateFulltextIndexExpression(
            dummy_dialect,
            index_name=index_name,
            table_name="articles",
            columns=["content"]
        )
        sql, params = create_ft.to_sql()

        assert f'CREATE FULLTEXT INDEX {expected_identifier}' in sql
        assert params == ()
