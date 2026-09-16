# src/rhosocial/activerecord/backend/dialect/mixins/collation.py
"""Dialect mixin for expression-level COLLATE support."""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.collation import CollateExpression


class CollationMixin:
    """Mixin adding support for expression-level ``COLLATE`` clauses.

    Provides a hook for validating collation names and rendering the
    ``<expr> COLLATE <collation>`` form.
    """

    def supports_collate_expression(self) -> bool:
        """Whether expression-level COLLATE is supported.

        Defaults to False.
        """
        return False

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate a collation expression and return its SQL representation.

        Args:
            expr: CollateExpression whose collation name should be validated.

        Returns:
            SQL string for the validated collation name.

        Raises:
            UnsupportedFeatureError: If the dialect cannot validate collation
                names.
        """
        raise UnsupportedFeatureError(self.name, "COLLATE collation validation")

    def format_collate_expression(self, expr: "CollateExpression") -> Tuple[str, tuple]:
        """Format expression-level COLLATE (plus outer alias).

        Args:
            expr: CollateExpression object to format.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support COLLATE
                expressions, or if the collation name is invalid.
        """
        if not self.supports_collate_expression():
            raise UnsupportedFeatureError(self.name, "COLLATE expression")
        expression_sql, params = expr.expression.to_sql()
        collation_sql = self.validate_collation_name(expr)
        sql = f"{expression_sql} COLLATE {collation_sql}"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params
