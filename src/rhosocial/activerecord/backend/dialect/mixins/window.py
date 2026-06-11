# src/rhosocial/activerecord/backend/dialect/mixins/window.py
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import (
        WindowFunctionCall,
        WindowSpecification,
        WindowFrameSpecification,
        WindowClause,
        WindowDefinition,
    )


class WindowFunctionMixin:
    """Mixin for window function support."""

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported."""
        return False

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported."""
        return False

    def format_window_function_call(self, call: "WindowFunctionCall") -> Tuple[str, tuple]:
        """Format window function call."""
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(self.name, "window functions")

        all_params = []

        # Format function arguments
        arg_parts = []
        for arg in call.args:
            if isinstance(arg, bases.BaseExpression):
                arg_sql, arg_params = arg.to_sql()
                arg_parts.append(arg_sql)
                all_params.extend(arg_params)
            else:
                # Literal value
                arg_parts.append(self.get_parameter_placeholder())
                all_params.append(arg)

        func_sql = f"{call.function_name}({', '.join(arg_parts)})"

        if call.window_spec is None:
            # No window specification
            sql = func_sql
        else:
            if isinstance(call.window_spec, str):
                # Reference to named window
                window_part = self.format_identifier(call.window_spec)
            else:
                # Inline window specification
                window_spec_sql, window_spec_params = self.format_window_specification(call.window_spec)
                window_part = f"({window_spec_sql})" if window_spec_sql else "()"
                all_params.extend(window_spec_params)

            sql = f"{func_sql} OVER {window_part}"

        # Apply type casts if any (before alias)
        if call.cast_types:
            for target_type in call.cast_types:
                sql, all_params_tuple = self.format_cast_expression(sql, target_type, tuple(all_params), None)
                all_params = list(all_params_tuple)

        # Apply alias if any (after type casts)
        if call.alias:
            sql = f"{sql} AS {self.format_identifier(call.alias)}"

        return sql, tuple(all_params)

    def format_window_specification(self, spec: "WindowSpecification") -> Tuple[str, tuple]:
        """Format window specification."""
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(self.name, "window functions")

        all_params = []

        parts = []

        # PARTITION BY
        if spec.partition_by:
            partition_parts = []
            for part in spec.partition_by:
                if isinstance(part, bases.BaseExpression):
                    part_sql, part_params = part.to_sql()
                    partition_parts.append(part_sql)
                    all_params.extend(part_params)
                else:
                    partition_parts.append(self.format_identifier(str(part)))
            parts.append("PARTITION BY " + ", ".join(partition_parts))

        # ORDER BY
        if spec.order_by and spec.order_by.expressions:
            # spec.order_by is now a single OrderByClause, so call its to_sql method
            # The OrderByClause.to_sql() method already includes "ORDER BY" keyword
            clause_sql, clause_params = spec.order_by.to_sql()
            parts.append(clause_sql)
            all_params.extend(clause_params)

        # Frame
        if spec.frame:
            # We need to implement format_window_frame_specification in the mixin
            frame_sql, frame_params = self.format_window_frame_specification(spec.frame)
            parts.append(frame_sql)
            all_params.extend(frame_params)

        # If no window specification components are provided, raise an error
        if not parts:
            raise ValueError("Window specification must have at least one component: PARTITION BY, ORDER BY, or FRAME.")

        return " ".join(parts), tuple(all_params)

    def format_window_frame_specification(self, spec: "WindowFrameSpecification") -> Tuple[str, tuple]:
        """Format window frame specification."""
        if not self.supports_window_frame_clause():
            raise UnsupportedFeatureError(self.name, "window frame specification")

        parts = [spec.frame_type]
        if spec.end_frame:
            parts.append(f"BETWEEN {spec.start_frame} AND {spec.end_frame}")
        else:
            parts.append(spec.start_frame)
        return " ".join(parts), ()

    def format_window_clause(self, clause: "WindowClause") -> Tuple[str, tuple]:
        """Format complete WINDOW clause."""
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(self.name, "WINDOW clause")

        if not clause.definitions:
            raise ValueError("WindowClause must contain at least one window definition.")

        all_params = []
        def_parts = []

        for defn in clause.definitions:
            def_sql, def_params = self.format_window_definition(defn)
            def_parts.append(def_sql)
            all_params.extend(def_params)

        return f"WINDOW {', '.join(def_parts)}", tuple(all_params)

    def format_window_definition(self, spec: "WindowDefinition") -> Tuple[str, tuple]:
        """Format named window definition."""
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(self.name, "window definition")

        spec_sql, spec_params = self.format_window_specification(spec.specification)
        window_def = f"{self.format_identifier(spec.name)} AS ({spec_sql})"
        return window_def, spec_params
