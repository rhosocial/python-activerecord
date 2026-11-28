# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/expressions/test_expr_traversal.py
"""SQLite-specific expression rendering that needs a real SQLite dialect.

Only the negated MATCH predicate lives here: it is checked purely by rendering,
never by serializing, so it is not part of the expression round-trip coverage.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.predicates.predicates import SQLiteMatchPredicate


@pytest.fixture
def sqlite_dialect():
    """Provides a SQLiteDialect instance."""
    return SQLiteDialect(version=(3, 53, 0))


class TestSQLiteSpecificExpressionTraversal:
    """Test SQLite-specific expressions."""

    def test_match_predicate_negated_raises_error(self, sqlite_dialect):
        """Negated MATCH predicate raises ValueError in FTS5."""
        expr = SQLiteMatchPredicate(sqlite_dialect, table="docs", query="python", negate=True)
        with pytest.raises(ValueError, match="FTS5 does not support NOT MATCH"):
            expr.to_sql()
