# src/rhosocial/activerecord/backend/dialect/mixins/drop_routine_mixin.py
"""Per-statement mixin for DropRoutineSupport. Members/order/signature mirror the protocol."""

from typing import Any, Dict, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Function

class DropRoutineMixin:
    def supports_drop_function(self) -> bool:
            """Whether DROP FUNCTION is supported (defaults to False)."""
            return False

    def supports_drop_function_if_exists(self) -> bool:
            """Whether DROP FUNCTION IF EXISTS is supported (defaults to False)."""
            return False

    def supports_drop_function_cascade(self) -> bool:
            """Whether DROP FUNCTION CASCADE is supported (defaults to False)."""
            return False

    def supports_drop_function_restrict(self) -> bool:
            """Whether DROP FUNCTION RESTRICT is supported (defaults to False)."""
            return False

    def format_drop_function_statement(self, expr: "DropFunctionStatement") -> Tuple[str, tuple]:
            """Format a DROP FUNCTION statement per SQL/PSM.

            Args:
                expr: The DropFunctionStatement to render.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is always empty.

            Raises:
                TypeError: ``DropFunctionStatement.function`` is not a Function.
                Another object kind would have had its own name rendered as the
                function's.
                UnsupportedFeatureError: If the dialect does not support functions.
            """
            if not isinstance(expr.function, Function):
                raise TypeError(
                    f"DropFunctionStatement.function must be a Function, "
                    f"got {type(expr.function).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_function():
                raise UnsupportedFeatureError(self.name, "functions")

            parts = ["DROP FUNCTION"]

            if expr.if_exists:
                if not self.supports_drop_function_if_exists():
                    raise UnsupportedFeatureError(
                        self.name, "DROP FUNCTION IF EXISTS",
                        f"{self.name} does not support DROP FUNCTION IF EXISTS."
                    )
                parts.append("IF EXISTS")

            parts.append(expr.function.to_sql()[0])

            if expr.parameters:
                param_types = ", ".join(expr.parameters)
                parts.append(f"({param_types})")

            if expr.cascade:
                if not self.supports_drop_function_cascade():
                    raise UnsupportedFeatureError(
                        self.name, "DROP FUNCTION CASCADE",
                        f"{self.name} does not support DROP FUNCTION CASCADE."
                    )
                parts.append("CASCADE")
            elif expr.restrict:
                if not self.supports_drop_function_restrict():
                    raise UnsupportedFeatureError(
                        self.name, "DROP FUNCTION RESTRICT",
                        f"{self.name} does not support DROP FUNCTION RESTRICT."
                    )
                parts.append("RESTRICT")

            return " ".join(parts), ()
