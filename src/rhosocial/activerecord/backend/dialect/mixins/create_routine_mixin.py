# src/rhosocial/activerecord/backend/dialect/mixins/create_routine_mixin.py
"""Per-statement mixin for CreateRoutineSupport. Members/order/signature mirror the protocol."""

import re
from typing import Any, Dict, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Function

class CreateRoutineMixin:
    def supports_function(self) -> bool:
            """Whether user-defined functions are supported (defaults to False)."""
            return False

    def supports_create_function(self) -> bool:
            """Whether CREATE FUNCTION is supported (defaults to False)."""
            return False

    def supports_function_or_replace(self) -> bool:
            """Whether CREATE OR REPLACE FUNCTION is supported (defaults to False)."""
            return False

    def supports_function_parameters(self) -> bool:
            """Whether function parameter lists are supported (defaults to False)."""
            return False

    def format_create_function_statement(self, expr: "CreateFunctionStatement") -> Tuple[str, tuple]:
            """Format a CREATE FUNCTION statement per SQL/PSM.

            Args:
                expr: The CreateFunctionStatement to render.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is always empty.

            Raises:
                TypeError: ``CreateFunctionStatement.function`` is not a Function.
                Another object kind would have had its own name rendered as the
                function's.
                UnsupportedFeatureError: If the dialect does not support functions.
                ValueError: If a parameter or return type contains invalid
                    characters.
            """
            if not isinstance(expr.function, Function):
                raise TypeError(
                    f"CreateFunctionStatement.function must be a Function, "
                    f"got {type(expr.function).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_function():
                raise UnsupportedFeatureError(self.name, "functions")

            parts = ["CREATE FUNCTION"]

            if expr.or_replace:
                if not self.supports_function_or_replace():
                    raise UnsupportedFeatureError(
                        self.name, "CREATE OR REPLACE FUNCTION",
                        f"{self.name} does not support CREATE OR REPLACE FUNCTION."
                    )
                parts.insert(1, "OR REPLACE")

            parts.append(expr.function.to_sql()[0])

            if expr.parameters:
                if not self.supports_function_parameters():
                    raise UnsupportedFeatureError(
                        self.name, "CREATE FUNCTION parameters",
                        f"{self.name} does not support CREATE FUNCTION parameters."
                    )
                param_strs = []
                for p in expr.parameters:
                    name = p.get("name", "")
                    param_type = p.get("type", "")
                    if name and param_type:
                        # Validate parameter name and type.
                        param_name = self.format_identifier(name)
                        if not re.fullmatch(r"[A-Za-z0-9\s(),]+", param_type):
                            raise ValueError(f"Invalid parameter type '{param_type}'")
                        param_strs.append(f"{param_name} {param_type}")
                    elif param_type:
                        param_strs.append(param_type)
                parts.append(f"({', '.join(param_strs)})")
            else:
                parts.append("()")

            if expr.returns:
                # Validate return type.
                if not re.fullmatch(r"[A-Za-z0-9\s(),]+", expr.returns):
                    raise ValueError(f"Invalid return type '{expr.returns}'")
                parts.append(f"RETURNS {expr.returns}")

            if expr.language:
                parts.append(f"LANGUAGE {expr.language}")

            if expr.body:
                parts.append("AS")
                parts.append(f"$${expr.body}$$")

            return " ".join(parts), ()
