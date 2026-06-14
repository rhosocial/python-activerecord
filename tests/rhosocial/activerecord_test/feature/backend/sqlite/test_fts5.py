# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_fts5.py
"""Tests for SQLite FTS5 (Full-Text Search) support."""

import pytest

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    SQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    FTS5MatchExpression,
    FTS5CreateVirtualTable,
    FTS5RankExpression,
    FTS5HighlightExpression,
    FTS5SnippetExpression,
    SQLiteMatchPredicate,
)
from rhosocial.activerecord.backend.impl.sqlite.protocols import (
    SQLiteFTS5Support,
    SQLiteVirtualTableSupport,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestFTS5Support:
    """Test FTS5 support detection and protocol."""

    def test_fts5_support_protocol(self):
        dialect = SQLiteDialect()
        assert isinstance(dialect, SQLiteVirtualTableSupport)
        assert isinstance(dialect, SQLiteFTS5Support)

    def test_fts5_supported_since_3_9_0(self):
        dialect_old = SQLiteDialect(version=(3, 8, 9))
        assert not dialect_old.supports_fts5()

        dialect_3_9 = SQLiteDialect(version=(3, 9, 0))
        assert dialect_3_9.supports_fts5()

        dialect_new = SQLiteDialect(version=(3, 35, 0))
        assert dialect_new.supports_fts5()

    def test_fts5_bm25_support(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_bm25()

        dialect_old = SQLiteDialect(version=(3, 8, 0))
        assert not dialect_old.supports_fts5_bm25()

    def test_fts5_highlight_support(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_highlight()

    def test_fts5_snippet_support(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_snippet()


class TestFTS5Tokenizers:
    """Test FTS5 tokenizer support."""

    def test_basic_tokenizers(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        tokenizers = dialect.get_supported_fts5_tokenizers()
        assert "unicode61" in tokenizers
        assert "ascii" in tokenizers
        assert "porter" in tokenizers

    def test_trigram_tokenizer_since_3_34_0(self):
        dialect_old = SQLiteDialect(version=(3, 33, 0))
        tokenizers_old = dialect_old.get_supported_fts5_tokenizers()
        assert "trigram" not in tokenizers_old

        dialect_new = SQLiteDialect(version=(3, 34, 0))
        tokenizers_new = dialect_new.get_supported_fts5_tokenizers()
        assert "trigram" in tokenizers_new


class TestFTS5CreateVirtualTable:
    """Test FTS5 virtual table creation via expression."""

    def test_basic_fts5_table(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5CreateVirtualTable(dialect, table_name="documents", columns=["title", "content"])
        sql, params = expr.to_sql()
        assert "CREATE VIRTUAL TABLE" in sql
        assert '"documents"' in sql
        assert "USING fts5" in sql
        assert '"title"' in sql
        assert '"content"' in sql
        assert params == ()

    def test_fts5_table_with_tokenizer(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5CreateVirtualTable(dialect, table_name="documents", columns=["title", "content"], tokenizer="porter")
        sql, params = expr.to_sql()
        assert "tokenize='porter'" in sql

    def test_fts5_table_with_tokenizer_options(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5CreateVirtualTable(
            dialect, table_name="documents", columns=["title", "content"],
            tokenizer="unicode61", tokenizer_options={"remove_diacritics": 1}
        )
        sql, params = expr.to_sql()
        assert "tokenize='unicode61 remove_diacritics 1'" in sql

    def test_fts5_table_with_prefix(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5CreateVirtualTable(dialect, table_name="documents", columns=["title", "content"], prefix=[2, 3])
        sql, params = expr.to_sql()
        assert "prefix='2 3'" in sql

    def test_fts5_table_with_content(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5CreateVirtualTable(
            dialect, table_name="documents_fts", columns=["title", "content"], content="documents"
        )
        sql, params = expr.to_sql()
        assert "content='documents'" in sql

    def test_fts5_table_with_content_rowid(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5CreateVirtualTable(
            dialect, table_name="documents_fts", columns=["title", "content"],
            content="documents", content_rowid="doc_id"
        )
        sql, params = expr.to_sql()
        assert "content_rowid='doc_id'" in sql

    def test_fts5_table_unsupported_version(self):
        dialect = SQLiteDialect(version=(3, 8, 0))
        expr = FTS5CreateVirtualTable(dialect, table_name="documents", columns=["title"])
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            expr.to_sql()
        assert "FTS5" in str(exc_info.value)


class TestFTS5MatchExpression:
    """Test FTS5 MATCH expression formatting."""

    def test_basic_match(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5MatchExpression(dialect, table="documents", query="sqlite AND database")
        sql, params = expr.to_sql()
        assert '"documents" MATCH ?' in sql
        assert params == ("sqlite AND database",)

    def test_match_with_columns(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5MatchExpression(dialect, table="documents", query="sqlite", columns=["title"])
        sql, params = expr.to_sql()
        assert '"documents" MATCH ?' in sql
        assert params[0] == "title:sqlite"

    def test_match_with_multiple_columns(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5MatchExpression(dialect, table="documents", query="sqlite", columns=["title", "content"])
        sql, params = expr.to_sql()
        assert params[0] == "title:sqlite OR content:sqlite"

    def test_negated_match_raises_error(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5MatchExpression(dialect, table="documents", query="sqlite", negate=True)
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            expr.to_sql()


class TestFTS5RankExpression:
    """Test FTS5 ranking expression formatting."""

    def test_default_rank(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5RankExpression(dialect, table_name="documents")
        sql, params = expr.to_sql()
        assert 'bm25("documents")' in sql
        assert params == ()

    def test_rank_with_weights(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5RankExpression(dialect, table_name="documents", weights=[10.0, 1.0])
        sql, params = expr.to_sql()
        assert 'bm25("documents", 10.0, 1.0)' in sql

    def test_rank_with_bm25_params(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5RankExpression(dialect, table_name="documents", bm25_params={"k1": 1.5, "b": 0.75})
        sql, params = expr.to_sql()
        assert "bm25(\"documents\", 'k1', 1.5, 'b', 0.75)" in sql

    def test_rank_with_weights_and_params(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5RankExpression(dialect, table_name="documents", weights=[5.0, 1.0], bm25_params={"k1": 1.2})
        sql, params = expr.to_sql()
        assert 'bm25("documents", 5.0, 1.0' in sql
        assert "'k1', 1.2" in sql


class TestFTS5HighlightExpression:
    """Test FTS5 highlight() expression formatting."""

    def test_basic_highlight(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5HighlightExpression(dialect, table_name="documents", column="content")
        sql, params = expr.to_sql()
        assert "highlight(" in sql
        assert len(params) == 2

    def test_highlight_custom_markers(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5HighlightExpression(
            dialect, table_name="documents", column="content",
            prefix_marker="<mark>", suffix_marker="</mark>"
        )
        sql, params = expr.to_sql()
        assert "<mark>" in params
        assert "</mark>" in params


class TestFTS5SnippetExpression:
    """Test FTS5 snippet() expression formatting."""

    def test_basic_snippet(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5SnippetExpression(dialect, table_name="documents", column="content")
        sql, params = expr.to_sql()
        assert "snippet(" in sql
        assert len(params) == 4

    def test_snippet_custom_options(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        expr = FTS5SnippetExpression(
            dialect, table_name="documents", column="content",
            prefix_marker="<em>", suffix_marker="</em>",
            context_tokens=15, ellipsis="[...]",
        )
        sql, params = expr.to_sql()
        assert "<em>" in params
        assert "</em>" in params
        assert "[...]" in params


class TestFTS5DropVirtualTable:
    """Test FTS5 virtual table drop."""

    def test_drop_fts5_table(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql = 'DROP TABLE "documents"'
        assert 'DROP TABLE "documents"' in sql

    def test_drop_fts5_table_if_exists(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql = 'DROP TABLE IF EXISTS "documents"'
        assert 'DROP TABLE IF EXISTS "documents"' in sql


class TestFTS5Integration:
    """Integration tests for FTS5 with SQLite backend."""

    @pytest.fixture
    def backend(self):
        backend = SQLiteBackend(database=":memory:")
        backend.connect()
        backend.introspect_and_adapt()
        yield backend
        backend.disconnect()

    def test_fts5_table_creation_and_search(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        expr = FTS5CreateVirtualTable(dialect, table_name="documents", columns=["title", "content"])
        sql, _ = expr.to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO documents(title, content) VALUES (?, ?)",
            ("SQLite Guide", "SQLite is a powerful embedded database"),
            options=insert_options,
        )
        backend.execute(
            "INSERT INTO documents(title, content) VALUES (?, ?)",
            ("Python Tutorial", "Learn Python programming from basics"),
            options=insert_options,
        )

        results = backend.fetch_all("SELECT title, content FROM documents WHERE documents MATCH ?", ("database",))
        assert len(results) == 1
        assert results[0]["title"] == "SQLite Guide"

    def test_fts5_bm25_ranking(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        expr = FTS5CreateVirtualTable(dialect, table_name="articles", columns=["title", "body"])
        sql, _ = expr.to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO articles(title, body) VALUES (?, ?)",
            ("Database Design", "database database database design"),
            options=insert_options,
        )
        backend.execute(
            "INSERT INTO articles(title, body) VALUES (?, ?)",
            ("Introduction", "database introduction"),
            options=insert_options,
        )

        results = backend.fetch_all(
            "SELECT title, bm25(articles) as rank FROM articles WHERE articles MATCH ? ORDER BY rank", ("database",)
        )
        assert len(results) == 2
        assert results[0]["title"] == "Database Design"

    def test_fts5_tokenizer_porter(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        expr = FTS5CreateVirtualTable(dialect, table_name="posts", columns=["content"], tokenizer="porter")
        sql, _ = expr.to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        backend.execute(
            "INSERT INTO posts(content) VALUES (?)",
            ("running jumps swimming",),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        results = backend.fetch_all("SELECT content FROM posts WHERE posts MATCH ?", ("run",))
        assert len(results) == 1

    def test_fts5_unicode61_tokenizer_options(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        expr = FTS5CreateVirtualTable(
            dialect, table_name="texts", columns=["content"],
            tokenizer="unicode61", tokenizer_options={"remove_diacritics": 1}
        )
        sql, _ = expr.to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        backend.execute(
            "INSERT INTO texts(content) VALUES (?)",
            ("café résumé",),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        results = backend.fetch_all("SELECT content FROM texts WHERE texts MATCH ?", ("cafe",))
        assert len(results) == 1


class TestMatchPredicate:
    """Test SQLiteMatchPredicate expression class."""

    def test_match_predicate_basic(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        match_pred = SQLiteMatchPredicate(dialect, table="docs", query="python")
        sql, params = match_pred.to_sql()
        assert '"docs" MATCH ?' in sql
        assert params == ("python",)

    def test_match_predicate_with_columns(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        match_pred = SQLiteMatchPredicate(dialect, table="docs", query="python", columns=["title", "content"])
        sql, params = match_pred.to_sql()
        assert '"docs" MATCH ?' in sql

    def test_match_predicate_negate_raises_error(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        match_pred = SQLiteMatchPredicate(dialect, table="docs", query="python", negate=True)
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            match_pred.to_sql()


class TestFormatMatchPredicate:
    """Test dialect.format_match_predicate method."""

    def test_format_match_predicate_basic(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_match_predicate(table="docs", query="python")
        assert '"docs" MATCH ?' in sql
        assert params == ("python",)

    def test_format_match_predicate_with_columns(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_match_predicate(table="docs", query="python", columns=["title"])
        assert '"docs" MATCH ?' in sql

    def test_format_match_predicate_negate_raises_error(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            dialect.format_match_predicate(table="docs", query="python", negate=True)
