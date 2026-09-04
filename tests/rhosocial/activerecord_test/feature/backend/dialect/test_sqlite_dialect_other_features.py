# tests/rhosocial/activerecord_test/feature/backend/dialect/test_sqlite_dialect_other_features.py
"""
Supplementary tests for other SQLiteDialect features
"""

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
        assert dialect.supports_explain_analyze()

    def test_supports_explain_format(self):
        """Test EXPLAIN format support"""
        dialect = SQLiteDialect()

        # Supported formats
        assert dialect.supports_explain_format("TEXT")
        assert dialect.supports_explain_format("text")
        assert dialect.supports_explain_format("DOT")
        assert dialect.supports_explain_format("dot")

        # Unsupported formats
        assert not dialect.supports_explain_format("JSON")
        assert not dialect.supports_explain_format("XML")
        assert not dialect.supports_explain_format("YAML")

    def test_supports_lateral_join(self):
        """Test LATERAL JOIN support - SQLite does not support the LATERAL keyword."""
        dialect = SQLiteDialect()
        assert not dialect.supports_lateral_join()

    def test_supports_for_update_skip_locked(self):
        """Test FOR UPDATE SKIP LOCKED support"""
        dialect = SQLiteDialect()
        assert not dialect.supports_for_update_skip_locked()

    def test_supports_for_update(self):
        """Test FOR UPDATE support - SQLite uses database-level locking, not row-level."""
        dialect = SQLiteDialect()
        assert not dialect.supports_for_update()

    def test_get_upsert_syntax_type(self):
        """Test UPSERT syntax type retrieval"""
        dialect = SQLiteDialect()
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"
