# tests/rhosocial/activerecord_test/feature/backend/dialect/test_returning_protocol.py
"""
Test for ReturningSupport protocol implementation.

This test creates a dialect that does not support RETURNING clauses and verifies that
the corresponding formatting methods raise appropriate errors.
"""
import pytest

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, ReturningMixin, ReturningSupport, UnsupportedFeatureError
)
from rhosocial.activerecord.backend.expression import Column


class NoReturningDialect(SQLDialectBase, ReturningMixin, ReturningSupport):
    """Dialect that does not support RETURNING clauses."""
    
    def supports_returning_clause(self) -> bool:
        return False


def test_no_returning_dialect_does_not_support_features():
    """Test that no-returning dialect properly indicates lack of RETURNING clause features."""
    dialect = NoReturningDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, ReturningSupport)
    assert not dialect.supports_returning_clause()


def test_format_returning_clause_raises_error():
    """Test that format_returning_clause method raises error in no-returning dialect."""
    dialect = NoReturningDialect()
    
    # Create a mock ReturningClause
    class MockReturningClause:
        def __init__(self):
            self.expressions = [Column(dialect, "id"), Column(dialect, "name")]
            self.alias = None
    
    mock_clause = MockReturningClause()
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_returning_clause(mock_clause)