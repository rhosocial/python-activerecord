# src/rhosocial/activerecord/backend/dialect/mixins/object_materialized_view_name.py
"""MaterializedView naming.

The counterpart of :attr:`MaterializedView.format_method`, and the only code that turns a
materialized view into SQL. A dialect that spells materialized views differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import MaterializedView

__all__ = ["MaterializedViewNameMixin"]


class MaterializedViewNameMixin(NamespaceMixin):
    """Renders a materialized view as its name."""

    def format_materialized_view_object(self, expr: "MaterializedView") -> Tuple[str, tuple]:
        """Render *expr* as a materialized view name.

        Args:
            expr: The materialized view being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The materialized view carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
