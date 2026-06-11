# src/rhosocial/activerecord/backend/dialect/mixins/returning.py
from typing import Tuple, TYPE_CHECKING

from ...expression.statements import ReturningClause


class ReturningMixin:
    """Mixin for RETURNING clause support."""

    def supports_returning_insert(self) -> bool:
        """Whether RETURNING clause is supported for INSERT statements."""
        return False

    def supports_returning_update(self) -> bool:
        """Whether RETURNING clause is supported for UPDATE statements."""
        return False

    def supports_returning_delete(self) -> bool:
        """Whether RETURNING clause is supported for DELETE statements."""
        return False

    def supports_returning_clause(self) -> bool:
        """Whether RETURNING clause is generally supported.
        Default is AND of all DML-specific returning support flags.
        """
        return (
            self.supports_returning_insert() and self.supports_returning_update() and self.supports_returning_delete()
        )

    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, Tuple]:
        """
        Format a RETURNING clause.

        Args:
            clause: ReturningClause object containing expressions to return

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        all_params = []
        expr_parts = []
        for expr in clause.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"

        # Add alias if provided
        if clause.alias:
            returning_sql += f" AS {self.format_identifier(clause.alias)}"

        return returning_sql, tuple(all_params)
