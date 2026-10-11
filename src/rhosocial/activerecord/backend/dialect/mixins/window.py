# src/rhosocial/activerecord/backend/dialect/mixins/window.py
"""Window function and WINDOW clause formatting for the dialect layer.

Provides capability probes and SQL rendering for window specifications,
frames, and named window definitions. Function *calls* with an ``OVER``
clause are rendered by :meth:`FunctionCallMixin.format_function_call`, which
composes this module's specification formatters; there is no separate
window-call formatter.
"""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import (
        WindowSpecification,
        WindowFrameSpecification,
        WindowClause,
        WindowDefinition,
    )


class WindowFunctionMixin:
    """Mixin providing window function and WINDOW clause support."""

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported.

        Defaults to False; dialects that support them override this.
        """
        return False

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported.

        Defaults to False; dialects that support them override this.
        """
        return False

    def format_window_specification(self, spec: "WindowSpecification") -> Tuple[str, tuple]:
        """Format a window specification (PARTITION BY / ORDER BY / frame).

        Args:
            spec: WindowSpecification exposing ``partition_by``,
                ``order_by``, and ``frame``.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If window functions are unsupported.
            ValueError: If the specification has no components.
        """
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
        """Format a window frame specification.

        Args:
            spec: WindowFrameSpecification exposing ``frame_type``,
                ``start_frame``, and ``end_frame``.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If frame clauses are unsupported.
        """
        if not self.supports_window_frame_clause():
            raise UnsupportedFeatureError(self.name, "window frame specification")

        parts = [spec.frame_type]
        if spec.end_frame:
            parts.append(f"BETWEEN {spec.start_frame} AND {spec.end_frame}")
        else:
            parts.append(spec.start_frame)
        return " ".join(parts), ()

    def format_window_clause(self, clause: "WindowClause") -> Tuple[str, tuple]:
        """Format a complete WINDOW clause.

        Args:
            clause: WindowClause exposing ``definitions``.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If window functions are unsupported.
            ValueError: If the clause has no window definitions.
        """
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
        """Format a named window definition.

        Args:
            spec: WindowDefinition exposing ``name`` and ``specification``.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If window functions are unsupported.
        """
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(self.name, "window definition")

        spec_sql, spec_params = self.format_window_specification(spec.specification)
        window_def = f"{self.format_identifier(spec.name)} AS ({spec_sql})"
        return window_def, spec_params
