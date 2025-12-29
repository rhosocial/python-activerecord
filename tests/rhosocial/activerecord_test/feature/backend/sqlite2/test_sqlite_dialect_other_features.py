# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_dialect_other_features.py
"""
Supplementary tests for other SQLiteDialect features
"""
import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class TestSQLiteDialectOtherFeatures:
    """Test other SQLiteDialect features"""

    def test_get_parameter_placeholder(self):
        """Test parameter placeholder retrieval"""
        dialect = SQLiteDialect()
        assert dialect.get_parameter_placeholder() == "?"
        # Position parameter doesn't affect SQLite's placeholder
        assert dialect.get_parameter_placeholder(0) == "?"
        assert dialect.get_parameter_placeholder(10) == "?"

    def test_get_server_version(self):
        """Test server version retrieval"""
        dialect = SQLiteDialect((3, 25, 1))
        assert dialect.get_server_version() == (3, 25, 1)

    def test_supports_explain_analyze(self):
        """Test EXPLAIN ANALYZE support"""
        dialect = SQLiteDialect()
        assert dialect.supports_explain_analyze() == True

    def test_supports_explain_format(self):
        """Test EXPLAIN format support"""
        dialect = SQLiteDialect()

        # Supported formats
        assert dialect.supports_explain_format("TEXT") == True
        assert dialect.supports_explain_format("text") == True
        assert dialect.supports_explain_format("DOT") == True
        assert dialect.supports_explain_format("dot") == True

        # Unsupported formats
        assert dialect.supports_explain_format("JSON") == False
        assert dialect.supports_explain_format("XML") == False
        assert dialect.supports_explain_format("YAML") == False

    def test_supports_lateral_join(self):
        """Test LATERAL JOIN support"""
        dialect = SQLiteDialect()
        assert dialect.supports_lateral_join() == True

    def test_supports_for_update_skip_locked(self):
        """Test FOR UPDATE SKIP LOCKED support"""
        dialect = SQLiteDialect()
        assert dialect.supports_for_update_skip_locked() == False

    def test_get_upsert_syntax_type(self):
        """Test UPSERT syntax type retrieval"""
        dialect = SQLiteDialect()
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"