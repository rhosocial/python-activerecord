# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_fts5.py
"""Tests for SQLite FTS5 (Full-Text Search) support."""
import pytest
import sqlite3

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    SQLiteBackend,
    FTS5Support,
    FTS5Mixin,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestFTS5Support:
    """Test FTS5 support detection and protocol."""

    def test_fts5_support_protocol(self):
        """Test that SQLiteDialect implements FTS5Support protocol."""
        dialect = SQLiteDialect()
        assert isinstance(dialect, FTS5Support)

    def test_fts5_mixin_included(self):
        """Test that SQLiteDialect includes FTS5Mixin."""
        dialect = SQLiteDialect()
        assert isinstance(dialect, FTS5Mixin)

    def test_fts5_supported_since_3_9_0(self):
        """Test FTS5 support detection for various versions."""
        # Before FTS5 (3.8.x)
        dialect_old = SQLiteDialect(version=(3, 8, 9))
        assert not dialect_old.supports_fts5()

        # FTS5 introduced in 3.9.0
        dialect_3_9 = SQLiteDialect(version=(3, 9, 0))
        assert dialect_3_9.supports_fts5()

        # Later versions should support FTS5
        dialect_new = SQLiteDialect(version=(3, 35, 0))
        assert dialect_new.supports_fts5()

    def test_fts5_bm25_support(self):
        """Test BM25 ranking function support."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_bm25()

        dialect_old = SQLiteDialect(version=(3, 8, 0))
        assert not dialect_old.supports_fts5_bm25()

    def test_fts5_highlight_support(self):
        """Test highlight() function support."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_highlight()

    def test_fts5_snippet_support(self):
        """Test snippet() function support."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_snippet()

    def test_fts5_offset_support(self):
        """Test offset() function support."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        assert dialect.supports_fts5_offset()


class TestFTS5Tokenizers:
    """Test FTS5 tokenizer support."""

    def test_basic_tokenizers(self):
        """Test basic tokenizer availability."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        tokenizers = dialect.get_supported_fts5_tokenizers()
        assert 'unicode61' in tokenizers
        assert 'ascii' in tokenizers
        assert 'porter' in tokenizers

    def test_trigram_tokenizer_since_3_34_0(self):
        """Test trigram tokenizer availability since 3.34.0."""
        # Before 3.34.0
        dialect_old = SQLiteDialect(version=(3, 33, 0))
        tokenizers_old = dialect_old.get_supported_fts5_tokenizers()
        assert 'trigram' not in tokenizers_old

        # 3.34.0 and later
        dialect_new = SQLiteDialect(version=(3, 34, 0))
        tokenizers_new = dialect_new.get_supported_fts5_tokenizers()
        assert 'trigram' in tokenizers_new


class TestFTS5CreateVirtualTable:
    """Test FTS5 virtual table creation."""

    def test_basic_fts5_table(self):
        """Test basic FTS5 virtual table creation."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_create_virtual_table(
            'documents',
            ['title', 'content']
        )
        assert 'CREATE VIRTUAL TABLE' in sql
        assert '"documents"' in sql
        assert 'USING fts5' in sql
        assert '"title"' in sql
        assert '"content"' in sql
        assert params == ()

    def test_fts5_table_with_tokenizer(self):
        """Test FTS5 table with tokenizer."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_create_virtual_table(
            'documents',
            ['title', 'content'],
            tokenizer='porter'
        )
        assert "tokenize='porter'" in sql

    def test_fts5_table_with_tokenizer_options(self):
        """Test FTS5 table with tokenizer options."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_create_virtual_table(
            'documents',
            ['title', 'content'],
            tokenizer='unicode61',
            tokenizer_options={'remove_diacritics': 1}
        )
        assert "tokenize='unicode61 remove_diacritics 1'" in sql

    def test_fts5_table_with_prefix(self):
        """Test FTS5 table with prefix indexing."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_create_virtual_table(
            'documents',
            ['title', 'content'],
            prefix=[2, 3]
        )
        assert "prefix='2 3'" in sql

    def test_fts5_table_with_content(self):
        """Test FTS5 table with external content."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_create_virtual_table(
            'documents_fts',
            ['title', 'content'],
            content='documents'
        )
        assert "content='documents'" in sql

    def test_fts5_table_with_content_rowid(self):
        """Test FTS5 table with content_rowid option."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_create_virtual_table(
            'documents_fts',
            ['title', 'content'],
            content='documents',
            content_rowid='doc_id'
        )
        assert "content_rowid='doc_id'" in sql

    def test_fts5_table_unsupported_version(self):
        """Test FTS5 table creation with unsupported version raises error."""
        dialect = SQLiteDialect(version=(3, 8, 0))
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_fts5_create_virtual_table('documents', ['title'])
        assert 'FTS5' in str(exc_info.value)


class TestFTS5MatchExpression:
    """Test FTS5 MATCH expression formatting."""

    def test_basic_match(self):
        """Test basic MATCH expression."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_match_expression(
            'documents',
            'sqlite AND database'
        )
        assert '"documents" MATCH ?' in sql
        assert params == ('sqlite AND database',)

    def test_match_with_columns(self):
        """Test MATCH expression with specific columns."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_match_expression(
            'documents',
            'sqlite',
            columns=['title']
        )
        assert '"documents" MATCH ?' in sql
        assert '{title:}' in params[0]

    def test_match_with_multiple_columns(self):
        """Test MATCH expression with multiple columns."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_match_expression(
            'documents',
            'sqlite',
            columns=['title', 'content']
        )
        assert '{title: OR content:}' in params[0]

    def test_negated_match(self):
        """Test negated MATCH expression."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_match_expression(
            'documents',
            'sqlite',
            negate=True
        )
        assert '"documents" NOT MATCH ?' in sql
        assert params == ('sqlite',)


class TestFTS5RankExpression:
    """Test FTS5 ranking expression formatting."""

    def test_default_rank(self):
        """Test default bm25() rank expression."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_rank_expression('documents')
        assert 'bm25("documents")' in sql
        assert params == ()

    def test_rank_with_weights(self):
        """Test bm25() with column weights."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_rank_expression(
            'documents',
            weights=[10.0, 1.0]
        )
        assert 'bm25("documents", 10.0, 1.0)' in sql

    def test_rank_with_bm25_params(self):
        """Test bm25() with BM25 parameters."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_rank_expression(
            'documents',
            bm25_params={'k1': 1.5, 'b': 0.75}
        )
        assert "bm25(\"documents\", 'k1', 1.5, 'b', 0.75)" in sql

    def test_rank_with_weights_and_params(self):
        """Test bm25() with both weights and BM25 parameters."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_rank_expression(
            'documents',
            weights=[5.0, 1.0],
            bm25_params={'k1': 1.2}
        )
        assert 'bm25("documents", 5.0, 1.0' in sql
        assert "'k1', 1.2" in sql


class TestFTS5HighlightExpression:
    """Test FTS5 highlight() expression formatting."""

    def test_basic_highlight(self):
        """Test basic highlight() expression."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_highlight_expression(
            'documents',
            'content',
            'sqlite'
        )
        assert 'highlight(' in sql
        assert len(params) == 3

    def test_highlight_custom_markers(self):
        """Test highlight() with custom markers."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_highlight_expression(
            'documents',
            'content',
            'sqlite',
            prefix_marker='<mark>',
            suffix_marker='</mark>'
        )
        assert '<mark>' in params
        assert '</mark>' in params


class TestFTS5SnippetExpression:
    """Test FTS5 snippet() expression formatting."""

    def test_basic_snippet(self):
        """Test basic snippet() expression."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_snippet_expression(
            'documents',
            'content',
            'sqlite'
        )
        assert 'snippet(' in sql
        assert len(params) == 5

    def test_snippet_custom_options(self):
        """Test snippet() with custom options."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_snippet_expression(
            'documents',
            'content',
            'sqlite',
            prefix_marker='<em>',
            suffix_marker='</em>',
            context_tokens=15,
            ellipsis='[...]'
        )
        assert '<em>' in params
        assert '</em>' in params
        assert '[...]' in params


class TestFTS5DropVirtualTable:
    """Test FTS5 virtual table drop."""

    def test_drop_fts5_table(self):
        """Test dropping FTS5 virtual table."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_drop_virtual_table('documents')
        assert 'DROP TABLE "documents"' in sql
        assert params == ()

    def test_drop_fts5_table_if_exists(self):
        """Test dropping FTS5 virtual table with IF EXISTS."""
        dialect = SQLiteDialect(version=(3, 9, 0))
        sql, params = dialect.format_fts5_drop_virtual_table(
            'documents',
            if_exists=True
        )
        assert 'DROP TABLE IF EXISTS "documents"' in sql
        assert params == ()


class TestFTS5Integration:
    """Integration tests for FTS5 with SQLite backend."""

    @pytest.fixture
    def backend(self):
        """Create in-memory SQLite backend."""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()
        yield backend
        backend.disconnect()

    def test_fts5_table_creation_and_search(self, backend):
        """Test creating FTS5 table and performing search."""
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        # Create FTS5 virtual table
        sql, _ = dialect.format_fts5_create_virtual_table(
            'documents',
            ['title', 'content']
        )
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Insert test data
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO documents(title, content) VALUES (?, ?)",
            ('SQLite Guide', 'SQLite is a powerful embedded database'),
            options=insert_options
        )
        backend.execute(
            "INSERT INTO documents(title, content) VALUES (?, ?)",
            ('Python Tutorial', 'Learn Python programming from basics'),
            options=insert_options
        )

        # Perform full-text search
        results = backend.fetch_all(
            "SELECT title, content FROM documents WHERE documents MATCH ?",
            ('database',)
        )
        assert len(results) == 1
        assert results[0]['title'] == 'SQLite Guide'

    def test_fts5_bm25_ranking(self, backend):
        """Test BM25 ranking with FTS5."""
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        # Create FTS5 virtual table
        sql, _ = dialect.format_fts5_create_virtual_table(
            'articles',
            ['title', 'body']
        )
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Insert test data
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO articles(title, body) VALUES (?, ?)",
            ('Database Design', 'database database database design'),
            options=insert_options
        )
        backend.execute(
            "INSERT INTO articles(title, body) VALUES (?, ?)",
            ('Introduction', 'database introduction'),
            options=insert_options
        )

        # Search with ranking
        results = backend.fetch_all(
            "SELECT title, bm25(articles) as rank FROM articles "
            "WHERE articles MATCH ? ORDER BY rank",
            ('database',)
        )
        assert len(results) == 2
        # The article with more 'database' occurrences should rank higher
        assert results[0]['title'] == 'Database Design'

    def test_fts5_tokenizer_porter(self, backend):
        """Test FTS5 with Porter stemmer tokenizer."""
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        # Create FTS5 table with Porter stemmer
        sql, _ = dialect.format_fts5_create_virtual_table(
            'posts',
            ['content'],
            tokenizer='porter'
        )
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Insert test data
        backend.execute(
            "INSERT INTO posts(content) VALUES (?)",
            ('running jumps swimming',),
            options=ExecutionOptions(stmt_type=StatementType.INSERT)
        )

        # Search with stemmed query
        results = backend.fetch_all(
            "SELECT content FROM posts WHERE posts MATCH ?",
            ('run jump swim',)
        )
        assert len(results) == 1

    def test_fts5_unicode61_tokenizer_options(self, backend):
        """Test FTS5 with unicode61 tokenizer options."""
        dialect = backend.dialect
        if not dialect.supports_fts5():
            pytest.skip("FTS5 not supported in this SQLite version")

        # Create FTS5 table with unicode61 and remove_diacritics
        sql, _ = dialect.format_fts5_create_virtual_table(
            'texts',
            ['content'],
            tokenizer='unicode61',
            tokenizer_options={'remove_diacritics': 1}
        )
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Insert text with diacritics
        backend.execute(
            "INSERT INTO texts(content) VALUES (?)",
            ('café résumé',),
            options=ExecutionOptions(stmt_type=StatementType.INSERT)
        )

        # Search without diacritics should match
        results = backend.fetch_all(
            "SELECT content FROM texts WHERE texts MATCH ?",
            ('cafe',)
        )
        assert len(results) == 1
