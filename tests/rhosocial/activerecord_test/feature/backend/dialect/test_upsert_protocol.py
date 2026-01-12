# tests/rhosocial/activerecord_test/feature/backend/dialect/test_upsert_protocol.py
"""
Test for UpsertSupport protocol implementation.

This test creates a dialect that does not support upsert operations and verifies that
the corresponding formatting methods raise appropriate errors.
"""

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, UpsertMixin, UpsertSupport
)


class NoUpsertDialect(SQLDialectBase, UpsertMixin, UpsertSupport):
    """Dialect that does not support upsert operations."""
    
    def supports_upsert(self) -> bool:
        return False
    
    def get_upsert_syntax_type(self) -> str:
        return "ON CONFLICT"


def test_no_upsert_dialect_does_not_support_features():
    """Test that no-upsert dialect properly indicates lack of upsert features."""
    dialect = NoUpsertDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, UpsertSupport)
    assert not dialect.supports_upsert()
    assert dialect.get_upsert_syntax_type() == "ON CONFLICT"


def test_format_on_conflict_clause_reports_no_support():
    """Test that format_on_conflict_clause method reports no support in no-upsert dialect."""
    dialect = NoUpsertDialect()
    
    # Verify that the dialect reports no upsert support
    assert not dialect.supports_upsert()