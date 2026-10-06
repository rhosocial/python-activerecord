"""The counterpart of :attr:`Schema.format_method`.

A schema is the inner namespace, so its name is where a relation's ``schema.``
goes -- and nothing precedes it, because the catalog is the connection's
business rather than part of the name. That falls out of the object's own slots:
a schema carries no outer level to render, so the qualified name is the name.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Schema

__all__ = ["SchemaNameMixin"]


class SchemaNameMixin(NamespaceMixin):
    """Renders a schema as its name."""

    def format_schema_object(self, expr: "Schema") -> Tuple[str, tuple]:
        """Render *expr* as a schema name.

        Args:
            expr: The schema being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
