# src/rhosocial/activerecord/backend/dialect/mixins/object_type_name.py
"""Type naming.

The counterpart of :attr:`Type.format_method`, and the only code that turns a
type into SQL. A dialect that spells types differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Type

__all__ = ["TypeNameMixin"]


class TypeNameMixin(NamespaceMixin):
    """Renders a type as its name."""

    def format_type_object(self, expr: "Type") -> Tuple[str, tuple]:
        """Render *expr* as a type name.

        Args:
            expr: The type being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The type carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
