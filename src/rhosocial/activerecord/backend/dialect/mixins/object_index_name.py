# src/rhosocial/activerecord/backend/dialect/mixins/object_index_name.py
"""Index naming.

The counterpart of :attr:`Index.format_method`, and the only code that turns a
index into SQL. A dialect that spells indexes differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Index

__all__ = ["IndexNameMixin"]


class IndexNameMixin(NamespaceMixin):
    """Renders a index as its name."""

    def format_index_object(self, expr: "Index") -> Tuple[str, tuple]:
        """Render *expr* as an index name.

        Args:
            expr: The index being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The index carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
