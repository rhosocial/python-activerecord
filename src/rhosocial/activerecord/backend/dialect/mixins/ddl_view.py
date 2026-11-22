# src/rhosocial/activerecord/backend/dialect/mixins/ddl_view.py
"""Composition base for ViewMixin. Feature groups live in per-statement mixins."""

from typing import Any, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table, View
from .create_view_mixin import CreateViewMixin
from .drop_view_mixin import DropViewMixin
from .materialized_view_mixin import MaterializedViewMixin

class ViewMixin(CreateViewMixin, DropViewMixin, MaterializedViewMixin):
    """Composition of CreateViewMixin, DropViewMixin, MaterializedViewMixin. No own members."""
    pass

class TruncateMixin:
    """Format TRUNCATE statements.

    Basic TRUNCATE is supported by default; optional modifiers (RESTART
    IDENTITY, CASCADE) default to unsupported and are overridden as needed.
    """

    def supports_truncate(self) -> bool:
        """Whether TRUNCATE is supported (defaults to True)."""
        return True

    def supports_truncate_table_keyword(self) -> bool:
        """Whether the TABLE keyword is supported (defaults to True)."""
        return True

    def supports_truncate_restart_identity(self) -> bool:
        """Whether RESTART IDENTITY is supported (defaults to False)."""
        return False

    def supports_truncate_cascade(self) -> bool:
        """Whether the CASCADE option is supported (defaults to False)."""
        return False

    def supports_truncate_restrict(self) -> bool:
        """Whether the RESTRICT option is supported (defaults to False)."""
        return False

    def format_truncate_statement(self, expr: "TruncateStatement") -> Tuple[str, tuple]:
        """Format a TRUNCATE statement.

        Args:
            expr: The TruncateStatement to render.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``TruncateStatement.table`` is not a Table. Another object
            kind would have had its own name rendered after TRUNCATE.
            UnsupportedFeatureError: If the dialect does not support TRUNCATE,
                or does not support RESTART IDENTITY or CASCADE for TRUNCATE.
        """
        if not isinstance(expr.table, Table):
            raise TypeError(
                f"TruncateStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_truncate():
            raise UnsupportedFeatureError(
                self.name, "TRUNCATE",
                f"{self.name} does not support TRUNCATE.",
            )
        if (expr.restart_identity or expr.continue_identity) and not self.supports_truncate_restart_identity():
            feature = (
                "TRUNCATE RESTART IDENTITY"
                if expr.restart_identity
                else "TRUNCATE CONTINUE IDENTITY"
            )
            raise UnsupportedFeatureError(
                self.name, feature,
                f"{self.name} does not support TRUNCATE with identity continuation."
            )
        if expr.cascade and not self.supports_truncate_cascade():
            raise UnsupportedFeatureError(
                self.name, "TRUNCATE CASCADE",
                f"{self.name} does not support TRUNCATE with CASCADE."
            )
        if expr.restrict and not self.supports_truncate_restrict():
            raise UnsupportedFeatureError(
                self.name, "TRUNCATE RESTRICT",
                f"{self.name} does not support TRUNCATE with RESTRICT."
            )
        table_sql = expr.table.to_sql()[0]
        sql = f"TRUNCATE TABLE {table_sql}"
        if expr.restart_identity:
            sql += " RESTART IDENTITY"
        elif expr.continue_identity:
            sql += " CONTINUE IDENTITY"
        if expr.cascade:
            sql += " CASCADE"
        elif expr.restrict:
            sql += " RESTRICT"
        return sql, ()
