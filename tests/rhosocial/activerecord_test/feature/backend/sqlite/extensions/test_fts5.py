# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_fts5.py
"""Tests for SQLite FTS5 (Full-Text Search) support.

Two test categories:
1. Expression construction tests — cover all legal parameter combinations,
   edge cases, and error conditions for 100% expression class coverage.
2. Real-world scenario tests — demonstrate FTS5 in action with SQLiteBackend.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    SQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
    SQLiteMatchPredicate,
)
from rhosocial.activerecord.backend.impl.sqlite.protocols import (
    SQLiteFTS5Support,
    SQLiteVirtualTableSupport,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


# =============================================================================
# Part 1: Expression Construction Tests — FTS5 support & capability
# =============================================================================

class TestFTS5Support:
    """FTS5 support detection — covers all capability check methods."""

    def test_implements_protocol(self):
        dialect = SQLiteDialect()
        assert isinstance(dialect, SQLiteVirtualTableSupport)
        assert isinstance(dialect, SQLiteFTS5Support)

    def test_supports_fts5_version_boundary(self):
        assert not SQLiteDialect(version=(3, 8, 9)).supports_fts5()
        assert SQLiteDialect(version=(3, 9, 0)).supports_fts5()
        assert SQLiteDialect(version=(3, 35, 0)).supports_fts5()
        assert SQLiteDialect(version=(9, 9, 9)).supports_fts5()

    def test_supports_fts5_compile_options(self):
        dialect = SQLiteDialect(version=(3, 8, 0))
        dialect.set_runtime_param("compile_options", {"ENABLE_FTS5": True})
        assert dialect.supports_fts5()
        dialect.set_runtime_param("compile_options", {})
        assert not dialect.supports_fts5()

    def test_bm25_support(self):
        assert SQLiteDialect(version=(3, 9, 0)).supports_fts5_bm25()
        assert not SQLiteDialect(version=(3, 8, 0)).supports_fts5_bm25()

    def test_highlight_support(self):
        assert SQLiteDialect(version=(3, 9, 0)).supports_fts5_highlight()
        assert not SQLiteDialect(version=(3, 8, 0)).supports_fts5_highlight()

    def test_snippet_support(self):
        assert SQLiteDialect(version=(3, 9, 0)).supports_fts5_snippet()
        assert not SQLiteDialect(version=(3, 8, 0)).supports_fts5_snippet()


class TestFTS5Tokenizers:
    """FTS5 tokenizer support — version-gated."""

    def test_basic_tokenizers_always_present(self):
        tokenizers = SQLiteDialect(version=(3, 9, 0)).get_supported_fts5_tokenizers()
        assert "unicode61" in tokenizers
        assert "ascii" in tokenizers
        assert "porter" in tokenizers
        assert "trigram" not in tokenizers

    def test_trigram_since_3_34_0(self):
        assert "trigram" not in SQLiteDialect(version=(3, 33, 0)).get_supported_fts5_tokenizers()
        assert "trigram" in SQLiteDialect(version=(3, 34, 0)).get_supported_fts5_tokenizers()


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteFTS5CreateVirtualTable
# =============================================================================

class TestSQLiteFTS5CreateVirtualTableConstruction:
    """100% coverage of SQLiteFTS5CreateVirtualTable construction and format_*."""

    def test_basic(self):
        sql, params = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="documents", columns=["title", "content"]
        ).to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "documents" USING fts5("title", "content")'
        assert params == ()

    def test_single_column(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["a"]
        ).to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "t" USING fts5("a")'

    def test_empty_columns(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=[]
        ).to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "t" USING fts5()'

    def test_with_tokenizer(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="articles", columns=["body"], tokenizer="porter"
        ).to_sql()
        assert "tokenize='porter'" in sql

    def test_with_tokenizer_options(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["c"],
            tokenizer="unicode61", tokenizer_options={"remove_diacritics": 1}
        ).to_sql()
        assert "tokenize='unicode61 remove_diacritics 1'" in sql

    def test_with_multiple_tokenizer_options(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["c"],
            tokenizer="unicode61",
            tokenizer_options={"remove_diacritics": 1, "tokenchars": 1}
        ).to_sql()
        assert "tokenize='unicode61 remove_diacritics 1 tokenchars 1'" in sql

    def test_tokenize_overrides_tokenizer(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["c"],
            tokenizer="porter", tokenize="unicode61 remove_diacritics 1"
        ).to_sql()
        assert "tokenize='unicode61 remove_diacritics 1'" in sql
        assert "porter" not in sql

    def test_with_prefix(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["c"], prefix=[2, 3]
        ).to_sql()
        assert "prefix='2 3'" in sql

    def test_with_single_prefix(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["c"], prefix=[3]
        ).to_sql()
        assert "prefix='3'" in sql

    def test_with_content_table(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t_fts", columns=["title", "body"], content="t"
        ).to_sql()
        assert "content='t'" in sql

    def test_with_content_rowid(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t_fts", columns=["title"],
            content="t", content_rowid="row_id"
        ).to_sql()
        assert "content='t'" in sql
        assert "content_rowid='row_id'" in sql

    def test_all_options_combined(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t_fts", columns=["title", "body"],
            tokenizer="porter", prefix=[2], content="t", content_rowid="rid"
        ).to_sql()
        assert "tokenize='porter'" in sql
        assert "prefix='2'" in sql
        assert "content='t'" in sql
        assert "content_rowid='rid'" in sql

    def test_special_chars_in_values(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table="t", columns=["col"],
            content="it's", tokenizer="porter"
        ).to_sql()
        assert "content='it''s'" in sql  # single quote escaped

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 9, 0)),
            table='my"table', columns=["col"]
        ).to_sql()
        assert '"my""table"' in sql  # double quote escaped by format_identifier

    def test_unsupported_version_raises_error(self):
        expr = SQLiteFTS5CreateVirtualTable(
            SQLiteDialect(version=(3, 8, 0)),
            table="t", columns=["c"]
        )
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "FTS5" in str(exc.value)

    def test_no_side_effects_between_expressions(self):
        dialect = SQLiteDialect(version=(3, 9, 0))
        e1 = SQLiteFTS5CreateVirtualTable(dialect, table="t1", columns=["a"])
        e2 = SQLiteFTS5CreateVirtualTable(dialect, table="t2", columns=["b", "c"], tokenizer="porter")
        sql1, _ = e1.to_sql()
        sql2, _ = e2.to_sql()
        assert '"t1"' in sql1 and '"t2"' in sql2
        assert "porter" not in sql1 and "porter" in sql2


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteMatchPredicate
# =============================================================================

class TestSQLiteMatchPredicateConstruction:
    """100% coverage of SQLiteMatchPredicate construction and format_*."""

    def test_basic(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python"
        ).to_sql()
        assert sql == '"docs" MATCH ?'
        assert params == ("python",)

    def test_with_compound_query(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python AND sqlite"
        ).to_sql()
        assert params == ("python AND sqlite",)

    def test_with_single_column(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python", columns=["title"]
        ).to_sql()
        assert sql == '"docs" MATCH ?'
        assert params[0] == "title:python"

    def test_with_multiple_columns(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python", columns=["title", "body"]
        ).to_sql()
        assert params[0] == "title:python OR body:python"

    def test_with_empty_columns(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python", columns=[]
        ).to_sql()
        assert params == ("python",)  # empty columns = search all

    def test_special_chars_in_query(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="it's \"quoted\""
        ).to_sql()
        assert params == ("it's \"quoted\"",)  # query is parameterized, no escaping needed

    def test_empty_query(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query=""
        ).to_sql()
        assert params == ("",)

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table='my"table', query="python"
        ).to_sql()
        assert '"my""table" MATCH ?' in sql  # quoted via format_identifier

    def test_negate_raises_value_error(self):
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            SQLiteMatchPredicate(
                SQLiteDialect(version=(3, 9, 0)),
                table="docs", query="python", negate=True
            ).to_sql()


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteFTS5RankExpression
# =============================================================================

class TestSQLiteFTS5RankExpressionConstruction:
    """100% coverage of SQLiteFTS5RankExpression construction and format_*."""

    def test_default(self):
        sql, params = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs"
        ).to_sql()
        assert sql == 'bm25("docs")'
        assert params == ()

    def test_with_weights(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", weights=[10.0, 1.0, 0.5]
        ).to_sql()
        assert 'bm25("docs", 10.0, 1.0, 0.5)' in sql

    def test_with_single_weight(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", weights=[5.0]
        ).to_sql()
        assert 'bm25("docs", 5.0)' in sql

    def test_with_empty_weights(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", weights=[]
        ).to_sql()
        assert 'bm25("docs")' in sql

    def test_with_bm25_params(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", bm25_params={"k1": 1.5, "b": 0.75}
        ).to_sql()
        assert "'k1', 1.5" in sql
        assert "'b', 0.75" in sql

    def test_with_empty_bm25_params(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", bm25_params={}
        ).to_sql()
        assert 'bm25("docs")' in sql

    def test_with_weights_and_params(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", weights=[5.0, 1.0], bm25_params={"k1": 1.2}
        ).to_sql()
        assert 'bm25("docs", 5.0, 1.0' in sql
        assert "'k1', 1.2" in sql

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteFTS5RankExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table='my"table'
        ).to_sql()
        assert '"my""table"' in sql


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteFTS5HighlightExpression
# =============================================================================

class TestSQLiteFTS5HighlightExpressionConstruction:
    """100% coverage of SQLiteFTS5HighlightExpression construction and format_*."""

    def test_default_markers(self):
        sql, params = SQLiteFTS5HighlightExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="title"
        ).to_sql()
        assert 'highlight("docs", "title", ?, ?)' in sql
        assert params == ("<b>", "</b>")

    def test_custom_markers(self):
        sql, params = SQLiteFTS5HighlightExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="title",
            prefix_marker="<em>", suffix_marker="</em>"
        ).to_sql()
        assert params == ("<em>", "</em>")

    def test_empty_markers(self):
        sql, params = SQLiteFTS5HighlightExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="title",
            prefix_marker="", suffix_marker=""
        ).to_sql()
        assert params == ("", "")

    def test_special_chars_in_markers(self):
        sql, params = SQLiteFTS5HighlightExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="title",
            prefix_marker="<<", suffix_marker=">>"
        ).to_sql()
        assert params == ("<<", ">>")

    def test_special_chars_in_column_name(self):
        sql, _ = SQLiteFTS5HighlightExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column='"col"'
        ).to_sql()
        assert '"""col"""' in sql


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteFTS5SnippetExpression
# =============================================================================

class TestSQLiteFTS5SnippetExpressionConstruction:
    """100% coverage of SQLiteFTS5SnippetExpression construction and format_*."""

    def test_default(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body"
        ).to_sql()
        assert 'snippet("docs", "body", ?, ?, ?, ?)' in sql
        assert params == ("<b>", "</b>", "...", 10)

    def test_custom_all_options(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body",
            prefix_marker="<mark>", suffix_marker="</mark>",
            context_tokens=20, ellipsis="[...]"
        ).to_sql()
        assert params == ("<mark>", "</mark>", "[...]", 20)

    def test_zero_context_tokens(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body",
            context_tokens=0
        ).to_sql()
        assert params[3] == 0

    def test_large_context_tokens(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body",
            context_tokens=999
        ).to_sql()
        assert params[3] == 999

    def test_custom_ellipsis(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body",
            ellipsis="---"
        ).to_sql()
        assert params[2] == "---"

    def test_empty_ellipsis(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body",
            ellipsis=""
        ).to_sql()
        assert params[2] == ""

    def test_empty_prefix_suffix_markers(self):
        sql, params = SQLiteFTS5SnippetExpression(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", column="body",
            prefix_marker="", suffix_marker=""
        ).to_sql()
        assert params[:2] == ("", "")


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteMatchPredicate
# =============================================================================

class TestMatchPredicateConstruction:
    """SQLiteMatchPredicate expression class coverage."""

    def test_basic(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python"
        ).to_sql()
        assert sql == '"docs" MATCH ?'
        assert params == ("python",)

    def test_with_columns(self):
        sql, params = SQLiteMatchPredicate(
            SQLiteDialect(version=(3, 9, 0)),
            table="docs", query="python", columns=["title", "body"]
        ).to_sql()
        assert sql == '"docs" MATCH ?'

    def test_negate_raises_value_error(self):
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            SQLiteMatchPredicate(
                SQLiteDialect(version=(3, 9, 0)),
                table="docs", query="python", negate=True
            ).to_sql()


class TestFormatMatchPredicate:
    """dialect.format_match_predicate method coverage."""

    def _make_expr(self, dialect, table="docs", query="python", columns=None, negate=False):
        return SQLiteMatchPredicate(dialect, table=table, query=query, columns=columns, negate=negate)

    def test_basic(self):
        d = SQLiteDialect(version=(3, 9, 0))
        sql, params = d.format_match_predicate(self._make_expr(d))
        assert sql == '"docs" MATCH ?'
        assert params == ("python",)

    def test_with_columns(self):
        d = SQLiteDialect(version=(3, 9, 0))
        sql, params = d.format_match_predicate(
            self._make_expr(d, columns=["title"])
        )
        assert sql == '"docs" MATCH ?'

    def test_multiple_columns(self):
        d = SQLiteDialect(version=(3, 9, 0))
        sql, params = d.format_match_predicate(
            self._make_expr(d, columns=["title", "body"])
        )
        assert sql == '"docs" MATCH ?'

    def test_negate_raises_value_error(self):
        d = SQLiteDialect(version=(3, 9, 0))
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            d.format_match_predicate(self._make_expr(d, negate=True))


# =============================================================================
# Part 2: Real-World Scenario Tests — FTS5 with SQLiteBackend
# =============================================================================

class TestFTS5Scenario:
    """Real FTS5 scenarios executed against an in-memory SQLite backend.

    These tests demonstrate how users would combine FTS5 expression
    objects with backend execution for full-text search.
    """

    @pytest.fixture
    def backend(self):
        b = SQLiteBackend(database=":memory:")
        b.connect()
        b.introspect_and_adapt()
        yield b
        b.disconnect()

    def test_create_and_search(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not available")

        sql, _ = SQLiteFTS5CreateVirtualTable(
            dialect, table="articles", columns=["title", "body"]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute("INSERT INTO articles VALUES (?, ?)", ("A", "hello world"), options=insert)
        backend.execute("INSERT INTO articles VALUES (?, ?)", ("B", "hello python"), options=insert)
        backend.execute("INSERT INTO articles VALUES (?, ?)", ("C", "sqlite database"), options=insert)

        rows = backend.fetch_all("SELECT title FROM articles WHERE articles MATCH ?", ("hello",))
        assert len(rows) == 2

    def test_bm25_ranking(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not available")

        sql, _ = SQLiteFTS5CreateVirtualTable(
            dialect, table="docs", columns=["title", "body"]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute("INSERT INTO docs VALUES (?, ?)", ("A", "python python python"), options=insert)
        backend.execute("INSERT INTO docs VALUES (?, ?)", ("B", "python"), options=insert)

        rows = backend.fetch_all(
            "SELECT title, bm25(docs) AS rank FROM docs WHERE docs MATCH ? ORDER BY rank",
            ("python",)
        )
        assert len(rows) == 2
        assert rows[0]["title"] == "A"  # higher frequency = better rank (lower score)

    def test_porter_tokenizer(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not available")

        sql, _ = SQLiteFTS5CreateVirtualTable(
            dialect, table="posts", columns=["content"], tokenizer="porter"
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute("INSERT INTO posts VALUES (?)", ("running jumps",), options=insert)

        rows = backend.fetch_all("SELECT content FROM posts WHERE posts MATCH ?", ("run",))
        assert len(rows) == 1

    def test_unicode61_diacritics(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not available")

        sql, _ = SQLiteFTS5CreateVirtualTable(
            dialect, table="texts", columns=["content"],
            tokenizer="unicode61", tokenizer_options={"remove_diacritics": 1}
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute("INSERT INTO texts VALUES (?)", ("café",), options=insert)

        rows = backend.fetch_all("SELECT content FROM texts WHERE texts MATCH ?", ("cafe",))
        assert len(rows) == 1

    def test_prefix_indexing(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not available")

        sql, _ = SQLiteFTS5CreateVirtualTable(
            dialect, table="prefixes", columns=["content"], prefix=[2, 3]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute("INSERT INTO prefixes VALUES (?)", ("hello world",), options=insert)

        rows = backend.fetch_all("SELECT content FROM prefixes WHERE prefixes MATCH ?", ("he*",))
        assert len(rows) == 1

    def test_drop_virtual_table(self, backend):
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not available")

        sql, _ = SQLiteFTS5CreateVirtualTable(
            dialect, table="tmp", columns=["x"]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        rows = backend.fetch_all("SELECT name FROM sqlite_master WHERE name='tmp'")
        assert len(rows) == 1

        dialect.format_drop_virtual_table("tmp")
        drop_sql, _ = dialect.format_drop_virtual_table("tmp")
        backend.execute(drop_sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        rows = backend.fetch_all("SELECT name FROM sqlite_master WHERE name='tmp'")
        assert len(rows) == 0
