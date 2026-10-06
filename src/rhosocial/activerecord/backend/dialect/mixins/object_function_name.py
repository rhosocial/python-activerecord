# src/rhosocial/activerecord/backend/dialect/mixins/object_function_name.py
"""Function naming.

The counterpart of :attr:`Function.format_method`, and the only code that turns a
function into SQL. A dialect that spells functions differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Function

__all__ = ["FunctionNameMixin"]


class FunctionNameMixin(NamespaceMixin):
    """Renders a function as its name."""

    def format_function_object(self, expr: "Function") -> Tuple[str, tuple]:
        """Render *expr* as a function name.

        Args:
            expr: The function being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The function carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
