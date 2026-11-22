# src/rhosocial/activerecord/backend/dialect/mixins/drop_view_mixin.py
"""Per-statement mixin for DropViewSupport. Members/order/signature mirror the protocol."""

from typing import Any, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table, View

class DropViewMixin:
    def supports_drop_view(self) -> bool:
            """Whether DROP VIEW is supported (defaults to True)."""
            return True

    def supports_if_exists_view(self) -> bool:
            """Whether DROP VIEW IF EXISTS is supported (defaults to False)."""
            return False

    def supports_cascade_view(self) -> bool:
            """Whether DROP VIEW CASCADE is supported (defaults to False)."""
            return False

    def supports_restrict_view(self) -> bool:
            """Whether DROP VIEW RESTRICT is supported (defaults to False)."""
            return False

    def format_drop_view_statement(self, expr: "DropViewStatement") -> Tuple[str, tuple]:
            """Format a DROP VIEW statement.

            Args:
                expr: The DropViewStatement to render.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is always empty.

            Raises:
                TypeError: ``DropViewStatement.view`` is not a View. Another object
                kind would have had its own name rendered as the view's.
                UnsupportedFeatureError: If the dialect does not support
                    IF EXISTS or CASCADE for DROP VIEW.
            """
            if not isinstance(expr.view, View):
                raise TypeError(
                    f"DropViewStatement.view must be a View, "
                    f"got {type(expr.view).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            if expr.if_exists and not self.supports_if_exists_view():
                raise UnsupportedFeatureError(
                    self.name, "DROP VIEW IF EXISTS",
                    f"{self.name} does not support DROP VIEW IF EXISTS."
                )
            if expr.cascade and not self.supports_cascade_view():
                raise UnsupportedFeatureError(
                    self.name, "DROP VIEW CASCADE",
                    f"{self.name} does not support DROP VIEW CASCADE."
                )
            if expr.restrict and not self.supports_restrict_view():
                raise UnsupportedFeatureError(
                    self.name, "DROP VIEW RESTRICT",
                    f"{self.name} does not support DROP VIEW RESTRICT."
                )
            if_exists_part = "IF EXISTS " if expr.if_exists else ""
            if expr.cascade:
                behavior_part = " CASCADE"
            elif expr.restrict:
                behavior_part = " RESTRICT"
            else:
                behavior_part = ""
            sql = f"DROP VIEW {if_exists_part}{expr.view.to_sql()[0]}{behavior_part}"
            return sql.strip(), ()
