# src/rhosocial/activerecord/backend/dialect/mixins/function.py
import re
from typing import Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateFunctionExpression,
        DropFunctionExpression,
    )


class FunctionMixin:
    """Mixin for function DDL support (SQL/PSM)."""

    def supports_function(self) -> bool:
        return False

    def supports_create_function(self) -> bool:
        return False

    def supports_drop_function(self) -> bool:
        return False

    def supports_function_or_replace(self) -> bool:
        return False

    def supports_function_parameters(self) -> bool:
        return False

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        Default implementation returns empty dict. Subclasses should override
        to provide actual function list from both core and backend-specific sources.

        Returns:
            Dict mapping function names to True/False. Default: empty dict.
        """
        return {}

    def format_create_function_statement(self, expr: "CreateFunctionExpression") -> Tuple[str, tuple]:
        """Format CREATE FUNCTION statement per SQL/PSM."""
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_function():
            raise UnsupportedFeatureError(self.name, "functions")

        parts = ["CREATE FUNCTION"]

        if expr.or_replace and self.supports_function_or_replace():
            parts.insert(1, "OR REPLACE")

        parts.append(self.format_identifier(expr.function_name))

        if expr.parameters and self.supports_function_parameters():
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

    def format_drop_function_statement(self, expr: "DropFunctionExpression") -> Tuple[str, tuple]:
        """Format DROP FUNCTION statement per SQL/PSM."""
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_function():
            raise UnsupportedFeatureError(self.name, "functions")

        parts = ["DROP FUNCTION"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.function_name))

        if expr.parameters:
            param_types = ", ".join(expr.parameters)
            parts.append(f"({param_types})")

        if expr.cascade:
            parts.append("CASCADE")

        return " ".join(parts), ()
