"""The counterpart of :attr:`Database.format_method`.

A database is the outermost container, so there is nothing to qualify it with:
the connection has already selected it. What a dialect may still spell
differently is the name itself -- quoting, reserved words, whatever -- so this
delegates to the shared identifier rules and nothing else.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Database

__all__ = ["DatabaseNameMixin"]


class DatabaseNameMixin(NamespaceMixin):
    """Renders a database as its name."""

    def format_database_object(self, expr: "Database") -> Tuple[str, tuple]:
        """Render *expr* as a database name.

        Args:
            expr: The database being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.
        """
        return self.format_identifier(expr.name), ()
