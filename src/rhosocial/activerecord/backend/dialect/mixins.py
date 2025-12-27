# src/rhosocial/activerecord/backend/dialect/mixins.py
"""
SQL dialect mixins for protocol implementations.

This module provides mixin classes that implement the functionality
defined in the protocol interfaces. This allows dialects to compose
only the features they support, rather than inheriting all functionality
from a base class.
"""
from typing import Any, List, Optional, Tuple, Dict, TYPE_CHECKING

from .exceptions import UnsupportedFeatureError
from ..expression import bases
from ..expression.statements import ReturningClause

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.advanced_functions import (
        WindowFunctionCall, WindowSpecification, WindowFrameSpecification,
        WindowDefinition, WindowClause
    )
    from ..expression.query_parts import (
        QualifyClause, MatchClause
    )
    from ..expression.graph import GraphEdgeDirection
    from ..expression.functions import FunctionCall
    from ..expression.literals import Literal


class WindowFunctionMixin:
    """Mixin for window function support."""

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported."""
        return False

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported."""
        return False

    def format_window_function_call(
        self,
        call: "WindowFunctionCall"
    ) -> Tuple[str, tuple]:
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
                # We need to implement format_window_specification in the mixin
                window_spec_sql, window_spec_params = self.format_window_specification(call.window_spec)
                window_part = f"({window_spec_sql})" if window_spec_sql else "()"
                all_params.extend(window_spec_params)

            sql = f"{func_sql} OVER {window_part}"

        if call.alias:
            sql = f"{sql} AS {self.format_identifier(call.alias)}"

        return sql, tuple(all_params)

    def format_window_specification(
        self,
        spec: "WindowSpecification"
    ) -> Tuple[str, tuple]:
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
        if spec.order_by:
            order_by_parts = []
            for item in spec.order_by:
                if isinstance(item, tuple):
                    expr, direction = item
                    if isinstance(expr, bases.BaseExpression):
                        expr_sql, expr_params = expr.to_sql()
                        order_by_parts.append(f"{expr_sql} {direction.upper()}")
                        all_params.extend(expr_params)
                    else:
                        order_by_parts.append(f"{self.format_identifier(str(expr))} {direction.upper()}")
                else:
                    if isinstance(item, bases.BaseExpression):
                        expr_sql, expr_params = item.to_sql()
                        order_by_parts.append(expr_sql)
                        all_params.extend(expr_params)
                    else:
                        order_by_parts.append(self.format_identifier(str(item)))
            parts.append("ORDER BY " + ", ".join(order_by_parts))

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

    def format_window_frame_specification(
        self,
        spec: "WindowFrameSpecification"
    ) -> Tuple[str, tuple]:
        """Format window frame specification."""
        if not self.supports_window_frame_clause():
            raise UnsupportedFeatureError(self.name, "window frame specification")

        parts = [spec.frame_type]
        if spec.end_frame:
            parts.append(f"BETWEEN {spec.start_frame} AND {spec.end_frame}")
        else:
            parts.append(spec.start_frame)
        return " ".join(parts), ()

    def format_window_clause(
        self,
        clause: "WindowClause"
    ) -> Tuple[str, tuple]:
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

    def format_window_definition(
        self,
        spec: "WindowDefinition"
    ) -> Tuple[str, tuple]:
        """Format named window definition."""
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(self.name, "window definition")

        spec_sql, spec_params = self.format_window_specification(spec.specification)
        window_def = f"{self.format_identifier(spec.name)} AS ({spec_sql})"
        return window_def, spec_params


class CTEMixin:
    """Mixin for Common Table Expression (CTE) support."""
    
    def supports_basic_cte(self) -> bool:
        """Whether basic CTEs are supported."""
        return False

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported."""
        return False

    def supports_materialized_cte(self) -> bool:
        """Whether MATERIALIZED hint is supported."""
        return False


class AdvancedGroupingMixin:
    """Mixin for advanced grouping operations (ROLLUP, CUBE, GROUPING SETS)."""
    
    def supports_rollup(self) -> bool:
        """Whether ROLLUP is supported."""
        return False

    def supports_cube(self) -> bool:
        """Whether CUBE is supported."""
        return False

    def supports_grouping_sets(self) -> bool:
        """Whether GROUPING SETS are supported."""
        return False

    def format_grouping_expression(
        self,
        operation: str,
        expressions: List["bases.BaseExpression"]
    ) -> Tuple[str, tuple]:
        """
        Formats a grouping expression (ROLLUP, CUBE, GROUPING SETS).

        Args:
            operation: The grouping operation ('ROLLUP', 'CUBE', or 'GROUPING SETS').
            expressions: List of expressions to group by.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        # Check feature support based on operation type
        if operation.upper() == "ROLLUP":
            if not self.supports_rollup():
                raise UnsupportedFeatureError(self.name, "ROLLUP")
        elif operation.upper() == "CUBE":
            if not self.supports_cube():
                raise UnsupportedFeatureError(self.name, "CUBE")
        elif operation.upper() == "GROUPING SETS":
            if not self.supports_grouping_sets():
                raise UnsupportedFeatureError(self.name, "GROUPING SETS")

        all_params = []
        if operation.upper() == "GROUPING SETS":
            # For GROUPING SETS, expressions is a list of lists
            sets_parts = []
            for expr_list in expressions:
                expr_parts = []
                for expr in expr_list:
                    expr_sql, expr_params = expr.to_sql()
                    expr_parts.append(expr_sql)
                    all_params.extend(expr_params)
                sets_parts.append(f"({', '.join(expr_parts)})")
            inner_expr = ", ".join(sets_parts)
            sql = f"{operation.upper()}({inner_expr})"
        else:
            # For ROLLUP and CUBE, expressions is a simple list
            expr_parts = []
            for expr in expressions:
                expr_sql, expr_params = expr.to_sql()
                expr_parts.append(expr_sql)
                all_params.extend(expr_params)
            inner_expr = ", ".join(expr_parts)
            sql = f"{operation.upper()}({inner_expr})"

        return sql, tuple(all_params)


class ReturningMixin:
    """Mixin for RETURNING clause support."""
    
    def supports_returning_clause(self) -> bool:
        """Whether RETURNING clause is supported."""
        return False

    def format_returning_clause(
            self,
            clause: "ReturningClause"
    ) -> Tuple[str, Tuple]:
        """
        Format a RETURNING clause.

        Args:
            clause: ReturningClause object containing expressions to return

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if not self.supports_returning_clause():
            raise UnsupportedFeatureError(self.name, "RETURNING clause")

        all_params = []
        expr_parts = []
        for expr in clause.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"

        # Add alias if provided
        if clause.alias:
            returning_sql += f" AS {self.format_identifier(clause.alias)}"

        return returning_sql, tuple(all_params)


class UpsertMixin:
    """Mixin for UPSERT operation support."""
    
    def supports_upsert(self) -> bool:
        """Whether UPSERT is supported."""
        return False

    def get_upsert_syntax_type(self) -> str:
        """
        Get UPSERT syntax type.

        Returns:
            'ON CONFLICT' (PostgreSQL) or 'ON DUPLICATE KEY' (MySQL)
        """
        return "ON CONFLICT"


class LateralJoinMixin:
    """Mixin for LATERAL join support."""
    
    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        return False


class ArrayMixin:
    """Mixin for array type support."""
    
    def supports_array_type(self) -> bool:
        """Whether array types are supported."""
        return False

    def supports_array_constructor(self) -> bool:
        """Whether ARRAY constructor is supported."""
        return False

    def supports_array_access(self) -> bool:
        """Whether array subscript access is supported."""
        return False


class JSONMixin:
    """Mixin for JSON type support."""
    
    def supports_json_type(self) -> bool:
        """Whether JSON type is supported."""
        return False

    def get_json_access_operator(self) -> str:
        """
        Get JSON access operator.

        Returns:
            '->' (PostgreSQL/MySQL/SQLite) or other dialect-specific operator
        """
        return "->"

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE function is supported."""
        return False

    def format_json_table_expression(
        self,
        json_col_sql: str,
        path: str,
        columns: List[Dict[str, Any]],
        alias: Optional[str],
        params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a JSON_TABLE expression.

        Args:
            json_col_sql: SQL for the JSON column/expression.
            path: The JSON path expression.
            columns: A list of dictionaries, each defining a column.
            alias: The alias for the resulting table.
            params: Parameters for the JSON column expression.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_json_table():
            raise UnsupportedFeatureError(self.name, "JSON_TABLE function")
        
        cols_defs = [f"{col['name']} {col['type']} PATH '{col['path']}'" for col in columns]
        columns_sql = f"COLUMNS({', '.join(cols_defs)})"
        sql = f"JSON_TABLE({json_col_sql}, '{path}' {columns_sql}) AS {self.format_identifier(alias) if alias else alias}"
        return sql, params


class ExplainMixin:
    """Mixin for EXPLAIN statement support."""
    
    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        return False

    def supports_explain_format(self, format_type: str) -> bool:
        """
        Check if specific EXPLAIN format is supported.

        Args:
            format_type: Format type (e.g., 'JSON', 'XML', 'YAML')

        Returns:
            True if format is supported
        """
        return False


class GraphMixin:
    """Mixin for graph query (MATCH) support."""
    
    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        return False

    def format_graph_vertex(
        self,
        variable: str,
        table: str
    ) -> Tuple[str, tuple]:
        """
        Formats a graph vertex expression.

        Args:
            variable: The vertex variable name.
            table: The vertex table name.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")
        
        sql = f"({variable} IS {self.format_identifier(table)})"
        return sql, ()

    def format_graph_edge(
        self,
        variable: str,
        table: str,
        direction: "GraphEdgeDirection"
    ) -> Tuple[str, tuple]:
        """
        Formats a graph edge expression.

        Args:
            variable: The edge variable name.
            table: The edge table name.
            direction: The edge direction.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")
        
        from ..expression.graph import GraphEdgeDirection  # Import here to avoid circular import

        # For different directions, construct the correct syntax
        if direction == GraphEdgeDirection.RIGHT:
            # Right-directed: -[var IS table]->
            sql = f"-[{variable} IS {self.format_identifier(table)}]->"
        elif direction == GraphEdgeDirection.LEFT:
            # Left-directed: <-[var IS table]-
            sql = f"<-[{variable} IS {self.format_identifier(table)}]-"
        elif direction == GraphEdgeDirection.ANY:
            # Bidirectional: <-[var IS table]->
            sql = f"<-[{variable} IS {self.format_identifier(table)}]->"
        else:  # GraphEdgeDirection.NONE (undirected)
            # Undirected: -[var IS table]-
            sql = f"-[{variable} IS {self.format_identifier(table)}]-"

        return sql, ()

    def format_match_clause(
        self,
        clause: "MatchClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a MATCH clause.

        Args:
            clause: MatchClause object containing the match expression

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")
        
        # This method is called from MatchClause.to_sql(), so we need to format the MATCH clause
        # with the path components from the clause
        path_sql, all_params = [], []
        for part in clause.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)

        match_sql = f"MATCH {' '.join(path_sql)}"
        return match_sql, tuple(all_params)


class FilterClauseMixin:
    """Mixin for aggregate FILTER clause support."""
    
    def supports_filter_clause(self) -> bool:
        """Whether FILTER (WHERE ...) clause is supported in aggregate functions."""
        return False

    def format_filter_clause(
        self,
        condition_sql: str,
        condition_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format a FILTER (WHERE ...) clause.

        Args:
            condition_sql: SQL string for the WHERE condition.
            condition_params: Parameters for the WHERE condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        if not self.supports_filter_clause():
            raise UnsupportedFeatureError(self.name, "FILTER clause in aggregate functions")
        
        return f"FILTER (WHERE {condition_sql})", condition_params


class OrderedSetAggregationMixin:
    """Mixin for ordered-set aggregate function support (WITHIN GROUP (ORDER BY ...))."""
    
    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        return False

    def format_ordered_set_aggregation(
        self,
        func_name: str,
        func_args_sql: List[str],
        func_args_params: tuple,
        order_by_sql: List[str],
        order_by_params: tuple,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Formats an ordered-set aggregate function call.

        Args:
            func_name: The name of the aggregate function.
            func_args_sql: List of SQL strings for the function's arguments.
            func_args_params: Parameters for the function's arguments.
            order_by_sql: List of SQL strings for the ORDER BY expressions.
            order_by_params: Parameters for the ORDER BY expressions.
            alias: Optional alias for the result.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_ordered_set_aggregation():
            raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions")
        
        args_str = ", ".join(func_args_sql)
        order_by_str = ", ".join(order_by_sql)
        sql = f"{func_name.upper()}({args_str}) WITHIN GROUP (ORDER BY {order_by_str})"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, func_args_params + order_by_params


class MergeMixin:
    """Mixin for MERGE statement support."""
    
    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        return False


class TemporalTableMixin:
    """Mixin for temporal table support."""
    
    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported."""
        return False


class QualifyClauseMixin:
    """Mixin for QUALIFY clause support."""

    def supports_qualify_clause(self) -> bool:
        """Whether QUALIFY clause is supported."""
        return False

    def format_qualify_clause(
        self,
        clause: "QualifyClause"
    ) -> Tuple[str, tuple]:
        """Format QUALIFY clause."""
        if not self.supports_qualify_clause():
            raise UnsupportedFeatureError(self.name, "QUALIFY clause")

        condition_sql, condition_params = clause.condition.to_sql()
        return f"QUALIFY {condition_sql}", condition_params


class LockingMixin:
    """Mixin for locking clause support."""
    
    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        return False