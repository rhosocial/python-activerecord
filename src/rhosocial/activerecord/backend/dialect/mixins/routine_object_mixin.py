# .../mixins/routine_object_mixin.py
"""Object-naming mixin. Members/order/signature mirror the protocol."""

from typing import Tuple
from .schema_namespace import NamespaceMixin
from ...expression.objects import Function
from ...expression.objects import Procedure

class RoutineObjectMixin:
    def format_function_object(self, expr: "Function") -> "Tuple[str, tuple]":
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

    def format_procedure_object(self, expr: "Procedure") -> "Tuple[str, tuple]":
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
