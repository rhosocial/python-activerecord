# src/rhosocial/activerecord/backend/dialect/mixins/object_view_name.py
"""View naming.

The counterpart of :attr:`View.format_method`, and the only code that turns a
view into SQL. A dialect that spells views differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import View

__all__ = ["ViewNameMixin"]


class ViewNameMixin(NamespaceMixin):
    """Renders a view as its name."""

    def format_view_object(self, expr: "View") -> Tuple[str, tuple]:
        """Render *expr* as a view name.

        Args:
            expr: The view being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The view carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
