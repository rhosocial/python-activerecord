# src/rhosocial/activerecord/backend/dialect/mixins/object_table_name.py
"""Table naming.

The counterpart of :attr:`Table.format_method`, and the only code that turns a
table into SQL. A dialect that spells tables differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Table

__all__ = ["TableNameMixin"]


class TableNameMixin(NamespaceMixin):
    """Renders a table as its name."""

    def format_table_object(self, expr: "Table") -> Tuple[str, tuple]:
        """Render *expr* as a table name.

        Args:
            expr: The table being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The table carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
