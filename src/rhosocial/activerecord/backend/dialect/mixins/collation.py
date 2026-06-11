# src/rhosocial/activerecord/backend/dialect/mixins/collation.py
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.collation import CollateExpression


class CollationMixin:
    """Mixin for expression-level COLLATE support."""

    def supports_collate_expression(self) -> bool:
        """Whether expression-level COLLATE is supported."""
        return False

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate a collation expression and return its SQL representation."""
        raise UnsupportedFeatureError(self.name, "COLLATE collation validation")

    def format_collate_expression(self, expr: "CollateExpression") -> Tuple[str, tuple]:
        """Format expression-level COLLATE."""
        if not self.supports_collate_expression():
            raise UnsupportedFeatureError(self.name, "COLLATE expression")
        expression_sql, params = expr.expression.to_sql()
        collation_sql = self.validate_collation_name(expr)
        return f"{expression_sql} COLLATE {collation_sql}", params
