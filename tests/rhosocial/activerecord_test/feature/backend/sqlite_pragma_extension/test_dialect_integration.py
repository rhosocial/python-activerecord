# tests/rhosocial/activerecord_test/feature/backend/sqlite_pragma_extension/test_dialect_integration.py
"""
Tests for SQLite Dialect integration with Extension and Pragma frameworks.
"""
import pytest

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    ExtensionType,
    PragmaCategory,
)


class TestSQLiteDialectExtensionIntegration:
    """Test SQLiteDialect extension integration."""

    def test_dialect_has_extension_support(self):
        """Test that dialect has extension support methods."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        assert hasattr(dialect, 'detect_extensions')
        assert hasattr(dialect, 'is_extension_available')
        assert hasattr(dialect, 'get_extension_info')
        assert hasattr(dialect, 'check_extension_feature')

    def test_dialect_detect_extensions(self):
        """Test dialect extension detection."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        extensions = dialect.detect_extensions()
        
        assert isinstance(extensions, dict)
        assert 'fts5' in extensions

    def test_dialect_fts5_available(self):
        """Test FTS5 availability through dialect."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        # FTS5 is available since 3.9.0
        assert dialect.is_extension_available('fts5') is True

    def test_dialect_fts5_not_available_old_version(self):
        """Test FTS5 not available in old version."""
        dialect = SQLiteDialect(version=(3, 8, 0))
        
        # FTS5 requires 3.9.0+
        assert dialect.is_extension_available('fts5') is False

    def test_dialect_check_extension_feature(self):
        """Test extension feature checking through dialect."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        # Basic FTS5 features
        assert dialect.check_extension_feature('fts5', 'full_text_search') is True
        assert dialect.check_extension_feature('fts5', 'bm25_ranking') is True

    def test_dialect_fts5_methods(self):
        """Test FTS5-specific methods."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        assert dialect.supports_fts5() is True
        assert dialect.supports_fts5_bm25() is True
        assert dialect.supports_fts5_highlight() is True

    def test_dialect_get_supported_fts5_tokenizers(self):
        """Test getting supported FTS5 tokenizers."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        tokenizers = dialect.get_supported_fts5_tokenizers()
        assert 'unicode61' in tokenizers
        assert 'ascii' in tokenizers
        assert 'porter' in tokenizers


class TestSQLiteDialectPragmaIntegration:
    """Test SQLiteDialect pragma integration."""

    def test_dialect_has_pragma_support(self):
        """Test that dialect has pragma support methods."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        assert hasattr(dialect, 'get_pragma_info')
        assert hasattr(dialect, 'get_pragma_sql')
        assert hasattr(dialect, 'set_pragma_sql')
        assert hasattr(dialect, 'is_pragma_available')
        assert hasattr(dialect, 'get_pragmas_by_category')
        assert hasattr(dialect, 'get_all_pragma_infos')

    def test_dialect_get_pragma_info(self):
        """Test getting pragma info through dialect."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        info = dialect.get_pragma_info('foreign_keys')
        assert info is not None
        assert info.name == 'foreign_keys'

    def test_dialect_get_pragma_sql(self):
        """Test generating pragma SQL through dialect."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql = dialect.get_pragma_sql('foreign_keys')
        assert sql == 'PRAGMA foreign_keys'

    def test_dialect_get_pragma_sql_with_argument(self):
        """Test generating pragma SQL with argument."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql = dialect.get_pragma_sql('table_info', argument='users')
        assert 'table_info' in sql
        assert 'users' in sql

    def test_dialect_set_pragma_sql(self):
        """Test generating pragma set SQL."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql = dialect.set_pragma_sql('foreign_keys', 1)
        assert 'foreign_keys' in sql
        assert '1' in sql

    def test_dialect_is_pragma_available(self):
        """Test pragma availability check."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        # Common pragmas available since early versions
        assert dialect.is_pragma_available('foreign_keys') is True
        assert dialect.is_pragma_available('journal_mode') is True

    def test_dialect_get_pragmas_by_category(self):
        """Test getting pragmas by category."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        config_pragmas = dialect.get_pragmas_by_category(PragmaCategory.CONFIGURATION)
        assert len(config_pragmas) > 0
        
        # All should be configuration pragmas
        for p in config_pragmas:
            assert p.category == PragmaCategory.CONFIGURATION

    def test_dialect_get_all_pragma_infos(self):
        """Test getting all pragma infos."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        all_pragmas = dialect.get_all_pragma_infos()
        assert isinstance(all_pragmas, dict)
        assert len(all_pragmas) > 0


class TestSQLiteDialectFTS5Formatting:
    """Test FTS5 SQL formatting methods."""

    def test_format_fts5_create_virtual_table(self):
        """Test formatting FTS5 CREATE VIRTUAL TABLE."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql, params = dialect.format_fts5_create_virtual_table(
            table_name='articles_fts',
            columns=['title', 'content', 'author']
        )
        
        assert 'articles_fts' in sql
        assert 'fts5' in sql
        assert len(params) == 0

    def test_format_fts5_create_virtual_table_with_tokenizer(self):
        """Test formatting FTS5 with tokenizer."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql, params = dialect.format_fts5_create_virtual_table(
            table_name='articles_fts',
            columns=['title', 'content'],
            tokenizer='porter'
        )
        
        assert 'tokenize' in sql
        assert 'porter' in sql

    def test_format_fts5_match_expression(self):
        """Test formatting FTS5 MATCH expression."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql, params = dialect.format_fts5_match_expression(
            table_name='articles_fts',
            query='python programming'
        )
        
        assert 'MATCH' in sql or 'match' in sql.lower()
        assert len(params) > 0

    def test_format_fts5_rank_expression(self):
        """Test formatting FTS5 bm25 rank expression."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql, params = dialect.format_fts5_rank_expression(
            table_name='articles_fts'
        )
        
        assert 'bm25' in sql.lower()

    def test_format_fts5_drop_virtual_table(self):
        """Test formatting DROP TABLE for FTS5."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql, params = dialect.format_fts5_drop_virtual_table(
            table_name='articles_fts'
        )
        
        assert 'DROP TABLE' in sql
        assert 'articles_fts' in sql

    def test_format_fts5_drop_virtual_table_if_exists(self):
        """Test formatting DROP TABLE IF EXISTS for FTS5."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        
        sql, params = dialect.format_fts5_drop_virtual_table(
            table_name='articles_fts',
            if_exists=True
        )
        
        assert 'IF EXISTS' in sql
