# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_other_features.py
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
        """Test EXPLAIN format support is one switch per format"""
        dialect = SQLiteDialect()

        # Supported format
        assert dialect.supports_explain_format_text()

        # Unsupported formats
        assert not dialect.supports_explain_format_json()
        assert not dialect.supports_explain_format_xml()
        assert not dialect.supports_explain_format_yaml()
        assert not dialect.supports_explain_format_tree()
        assert not dialect.supports_explain_format_traditional()

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
        assert dialect.suggest_upsert_syntax_type().syntax == "ON CONFLICT"
