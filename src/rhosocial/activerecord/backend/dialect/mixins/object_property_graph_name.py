"""The counterpart of :attr:`PropertyGraph.format_method`.

A property graph is a named catalogue entry that a relation may be qualified by,
so it is spelled the way any such name is spelled: the namespace levels first,
then the name. There is nothing graph-specific about the spelling itself, which
is why this is the same shape as every other object-naming mixin -- a dialect
that spells graph names differently overrides this method and nothing else.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import PropertyGraph

__all__ = ["PropertyGraphNameMixin"]


class PropertyGraphNameMixin(NamespaceMixin):
    """Renders a property graph as its name."""

    def format_property_graph_object(self, expr: "PropertyGraph") -> Tuple[str, tuple]:
        """Render *expr* as a property graph name.

        Args:
            expr: The property graph being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)