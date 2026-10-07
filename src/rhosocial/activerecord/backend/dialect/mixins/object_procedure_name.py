# src/rhosocial/activerecord/backend/dialect/mixins/object_procedure_name.py
"""Procedure naming.

The counterpart of :attr:`Procedure.format_method`, and the only code that turns a
procedure into SQL. A dialect that spells procedures differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Procedure

__all__ = ["ProcedureNameMixin"]


class ProcedureNameMixin(NamespaceMixin):
    """Renders a procedure as its name."""

    def format_procedure_object(self, expr: "Procedure") -> Tuple[str, tuple]:
        """Render *expr* as a procedure name.

        Args:
            expr: The procedure being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The procedure carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
