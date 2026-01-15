# src/rhosocial/activerecord/backend/dialect/mixins.py
"""
SQL dialect mixins for protocol implementations.

This module provides mixin classes that implement the functionality
defined in the protocol interfaces. This allows dialects to compose
only the features they support, rather than inheriting all functionality
from a base class.
"""
from typing import Any, List, Optional, Tuple, Dict, Union, TYPE_CHECKING

from .exceptions import UnsupportedFeatureError
from ..expression import bases
from ..expression.statements import ReturningClause

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.advanced_functions import (
        WindowFunctionCall, WindowSpecification, WindowFrameSpecification,
        WindowDefinition, WindowClause
    )
    from ..expression.query_parts import (
        QualifyClause, JoinExpression, OrderByClause
    )
    from ..expression.graph import GraphEdgeDirection, MatchClause


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

    def format_cte(
            self,
            name: str,
            query_sql: str,
            columns: Optional[List[str]] = None,
            materialized: Optional[bool] = None,
            dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a single CTE definition."""
        materialized_hint = ""
        if materialized is not None:
            materialized_hint = "MATERIALIZED " if materialized else "NOT MATERIALIZED "

        name_part = self.format_identifier(name)
        columns_part = f" ({', '.join(self.format_identifier(c) for c in columns)})" if columns else ""
        return f"{name_part}{columns_part} AS {materialized_hint}({query_sql})"

    def format_with_query(
            self,
            cte_sql_parts: List[str],
            main_query_sql: str,
            dialect_options: Optional[Dict[str, Any]] = None,
            has_recursive: bool = False  # Added parameter to indicate if any CTE is recursive
    ) -> str:
        """Format a complete query with WITH clause."""
        if not cte_sql_parts:
            return main_query_sql
        with_clause = self._format_with_clause(cte_sql_parts, has_recursive)
        return f"{with_clause} {main_query_sql}"

    def _format_with_clause(self, ctes_sql: List[str], has_recursive: bool = False) -> str:
        """Helper to format complete WITH clause from list of CTE definitions."""
        if not ctes_sql:
            return ""
        recursive_str = "RECURSIVE " if has_recursive else ""
        return f"WITH {recursive_str}{', '.join(ctes_sql)}"


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

    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
        """Format ON CONFLICT clause."""
        all_params = []

        # Start with ON CONFLICT
        parts = ["ON CONFLICT"]

        # Add conflict target if specified
        if expr.conflict_target:
            target_parts = []
            for target in expr.conflict_target:
                if isinstance(target, str):
                    # Column name as string
                    target_parts.append(self.format_identifier(target))
                elif hasattr(target, 'to_sql'):
                    # Column expression
                    target_sql, target_params = target.to_sql()
                    target_parts.append(target_sql)
                    all_params.extend(target_params)
                else:
                    # Other types - format as identifier
                    target_parts.append(self.format_identifier(str(target)))

            if target_parts:
                parts.append(f"({', '.join(target_parts)})")

        # Add DO NOTHING or DO UPDATE
        if expr.do_nothing:
            parts.append("DO NOTHING")
        elif expr.update_assignments:
            # DO UPDATE SET assignments
            update_parts = []
            for col, expr_val in expr.update_assignments.items():
                if isinstance(expr_val, bases.BaseExpression):
                    val_sql, val_params = expr_val.to_sql()
                    update_parts.append(f"{self.format_identifier(col)} = {val_sql}")
                    all_params.extend(val_params)
                else:
                    update_parts.append(f"{self.format_identifier(col)} = {self.get_parameter_placeholder()}")
                    all_params.append(expr_val)

            parts.append(f"DO UPDATE SET {', '.join(update_parts)}")

            # Add WHERE clause if specified
            if expr.update_where:
                where_sql, where_params = expr.update_where.to_sql()
                parts.append(f"WHERE {where_sql}")
                all_params.extend(where_params)
        else:
            # Default to DO NOTHING if no action specified
            parts.append("DO NOTHING")

        return " ".join(parts), tuple(all_params)


class LateralJoinMixin:
    """Mixin for LATERAL join support."""

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        return False

    def format_lateral_expression(
            self,
            expr_sql: str,
            expr_params: Tuple[Any, ...],
            alias: Optional[str],
            join_type: str
    ) -> Tuple[str, Tuple]:
        """Format LATERAL expression."""
        if alias is not None:
            sql = f"{join_type.upper()} JOIN LATERAL {expr_sql} AS {self.format_identifier(alias)}"
        else:
            sql = f"{join_type.upper()} JOIN LATERAL {expr_sql}"
        return sql, expr_params

    def format_table_function_expression(
            self,
            func_name: str,
            args_sql: List[str],
            args_params: Tuple[Any, ...],
            alias: Optional[str],
            column_names: Optional[List[str]]
    ) -> Tuple[str, Tuple]:
        """Format table-valued function expression."""
        args_str = ", ".join(args_sql)

        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"

        if alias is not None:
            sql = f"{func_name.upper()}({args_str}) AS {self.format_identifier(alias)}{cols_sql}"
        else:
            sql = f"{func_name.upper()}({args_str}){cols_sql}"
        return sql, args_params


class JoinMixin:
    """Mixin for JOIN clause support."""

    def supports_inner_join(self) -> bool:
        """Whether INNER JOIN is supported. Defaults to True."""
        return True

    def supports_left_join(self) -> bool:
        """Whether LEFT JOIN is supported. Defaults to True."""
        return True

    def supports_right_join(self) -> bool:
        """Whether RIGHT JOIN is supported. Defaults to False."""
        return False

    def supports_full_join(self) -> bool:
        """Whether FULL JOIN is supported. Defaults to False."""
        return False

    def supports_cross_join(self) -> bool:
        """Whether CROSS JOIN is supported. Defaults to True."""
        return True

    def supports_natural_join(self) -> bool:
        """Whether NATURAL JOIN is supported. Defaults to True."""
        return True

    def format_join_expression(self, join_expr: "JoinExpression") -> Tuple[str, Tuple]:
        """
        Generic implementation for formatting a JOIN expression.
        This method validates support for the given join type using protocol methods.
        """
        from ..expression import QueryExpression, JoinExpression
        join_type_upper = join_expr.join_type.upper()

        # Use split to handle cases like "LEFT OUTER JOIN"
        join_type_keyword = join_type_upper.split()[0]

        # Check for feature support
        if join_type_keyword == "INNER" and not self.supports_inner_join():
            raise UnsupportedFeatureError(self.name, "INNER JOIN")
        elif join_type_keyword == "LEFT" and not self.supports_left_join():
            raise UnsupportedFeatureError(self.name, "LEFT JOIN")
        elif join_type_keyword == "RIGHT" and not self.supports_right_join():
            raise UnsupportedFeatureError(self.name, "RIGHT JOIN")
        elif join_type_keyword == "FULL" and not self.supports_full_join():
            raise UnsupportedFeatureError(self.name, "FULL JOIN")
        elif join_type_keyword == "CROSS" and not self.supports_cross_join():
            raise UnsupportedFeatureError(self.name, "CROSS JOIN")

        if join_expr.natural and not self.supports_natural_join():
            raise UnsupportedFeatureError(self.name, "NATURAL JOIN")

        all_params = []

        # Format left and right sides of the join
        left_sql, left_params = join_expr.left_table.to_sql()
        if isinstance(join_expr.left_table, (QueryExpression, JoinExpression)):
            left_sql = f"({left_sql})"
        all_params.extend(left_params)

        right_sql, right_params = join_expr.right_table.to_sql()
        if isinstance(join_expr.right_table, (QueryExpression, JoinExpression)):
            right_sql = f"({right_sql})"
        all_params.extend(right_params)

        # Build the join clause
        join_parts = [left_sql]

        if join_expr.natural:
            join_parts.append("NATURAL")

        join_parts.append(join_type_upper)
        join_parts.append(right_sql)

        # Handle ON or USING clause, which are not used with NATURAL JOIN
        if not join_expr.natural:
            if join_expr.condition:
                cond_sql, cond_params = join_expr.condition.to_sql()
                join_parts.append(f"ON {cond_sql}")
                all_params.extend(cond_params)
            elif join_expr.using:
                using_cols = ", ".join(self.format_identifier(col) for col in join_expr.using)
                join_parts.append(f"USING ({using_cols})")
            elif "CROSS" not in join_type_upper:
                raise ValueError(f"{join_type_upper} requires a condition or USING clause.")

        sql = " ".join(join_parts)

        # Add alias for the joined result if provided
        if join_expr.alias:
            sql = f"({sql}) AS {self.format_identifier(join_expr.alias)}"

        return sql, tuple(all_params)


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

    def format_array_expression(
            self,
            operation: str,
            elements: Optional[List["bases.BaseExpression"]],
            base_expr: Optional["bases.BaseExpression"],
            index_expr: Optional["bases.BaseExpression"],
            alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format array expression."""
        all_params = ()

        if operation.upper() == "CONSTRUCTOR" and elements is not None:
            element_parts = []
            all_params = []
            for elem in elements:
                elem_sql, elem_params = elem.to_sql()
                element_parts.append(elem_sql)
                all_params.extend(elem_params)
            sql = f"ARRAY[{', '.join(element_parts)}]"
            all_params = tuple(all_params)
        elif operation.upper() == "ACCESS" and base_expr and index_expr:
            base_sql, base_params = base_expr.to_sql()
            index_sql, index_params = index_expr.to_sql()
            sql = f"({base_sql}[{index_sql}])"
            all_params = base_params + index_params
        else:
            # Default case for unsupported operations
            sql = "ARRAY[]"

        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"

        return sql, all_params


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

    def format_json_expression(
            self,
            column: Union["bases.BaseExpression", str],
            path: str,
            operation: str,
            alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format JSON expression."""
        if isinstance(column, bases.BaseExpression):
            col_sql, col_params = column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(column)), ()
        sql = f"({col_sql} {operation} ?)"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, col_params + (path,)

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
        if alias is not None:
            sql = f"JSON_TABLE({json_col_sql}, '{path}' {columns_sql}) AS {self.format_identifier(alias)}"
        else:
            sql = f"JSON_TABLE({json_col_sql}, '{path}' {columns_sql})"
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

    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
        """Format EXPLAIN statement."""
        statement_sql, statement_params = expr.statement.to_sql()
        options = expr.options
        if options is None:
            return f"EXPLAIN {statement_sql}", statement_params

        parts = ["EXPLAIN"]
        # Import here to avoid circular imports
        from ..expression.statements import ExplainType
        # Determine if ANALYZE should be included based on the type field
        # If type is ANALYZE, or if the boolean analyze field is True
        if (hasattr(options, 'type') and options.type == ExplainType.ANALYZE) or options.analyze:
            parts.append("ANALYZE")
        if options.format:
            parts.append(f"FORMAT {options.format.value.upper()}")
        # Only show costs=False if it's explicitly set to False, since True is default
        if not options.costs:
            parts.append("COSTS OFF")
        if options.buffers:
            parts.append("BUFFERS")
        if options.timing and options.analyze:
            parts.append("TIMING ON")
        if options.verbose:
            parts.append("VERBOSE")
        if options.settings:
            parts.append("SETTINGS")  # PostgreSQL-specific option, not SQL standard
        if options.wal:
            parts.append("WAL")  # PostgreSQL-specific option, not SQL standard

        return f"{' '.join(parts)} {statement_sql}", statement_params


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
            aggregation: "OrderedSetAggregation"
    ) -> Tuple[str, Tuple]:
        """
        Formats an ordered-set aggregate function call.

        Args:
            aggregation: OrderedSetAggregation object to format

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_ordered_set_aggregation():
            raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions")

        # Format function arguments
        func_args_sql, func_args_params = [], []
        for arg in aggregation.args:
            arg_sql, arg_params = arg.to_sql()
            func_args_sql.append(arg_sql)
            func_args_params.extend(arg_params)

        # Get the ORDER BY SQL from the OrderByClause object
        order_by_sql, order_by_params = aggregation.order_by.to_sql()
        sql = f"{aggregation.func_name.upper()}({', '.join(func_args_sql)}) WITHIN GROUP ({order_by_sql})"
        if aggregation.alias:
            sql = f"{sql} AS {self.format_identifier(aggregation.alias)}"
        return sql, tuple(func_args_params) + order_by_params


class MergeMixin:
    """Mixin for MERGE statement support."""

    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        return False

    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
        """Format MERGE statement."""
        all_params: List[Any] = []
        target_sql, target_params = expr.target_table.to_sql()
        all_params.extend(target_params)
        source_sql, source_params = expr.source.to_sql()
        all_params.extend(source_params)
        on_sql, on_params = expr.on_condition.to_sql()
        all_params.extend(on_params)

        merge_sql_parts = [f"MERGE INTO {target_sql}", f"USING {source_sql}", f"ON {on_sql}"]

        # Import here to avoid circular imports
        from ..expression.statements import MergeActionType

        for action in expr.when_matched:
            action_sql_parts = []
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                action_sql_parts.append(f"WHEN MATCHED AND {cond_sql}")
                all_params.extend(cond_params)
            else:
                action_sql_parts.append("WHEN MATCHED")

            if action.action_type == MergeActionType.UPDATE:
                assignments = []
                for col, as_expr in action.assignments.items():
                    as_sql, as_params = as_expr.to_sql()
                    assignments.append(f"{self.format_identifier(col)} = {as_sql}")
                    all_params.extend(as_params)
                action_sql_parts.append(f"THEN UPDATE SET {', '.join(assignments)}")
            elif action.action_type == MergeActionType.DELETE:
                action_sql_parts.append("THEN DELETE")
            merge_sql_parts.append(" ".join(action_sql_parts))

        for action in expr.when_not_matched:
            action_sql_parts = []
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                action_sql_parts.append(f"WHEN NOT MATCHED AND {cond_sql}")
                all_params.extend(cond_params)
            else:
                action_sql_parts.append("WHEN NOT MATCHED")

            if action.action_type == MergeActionType.INSERT:
                insert_cols, insert_vals = [], []
                for col, val_expr in action.assignments.items():
                    insert_cols.append(self.format_identifier(col))
                    val_sql, val_params = val_expr.to_sql()
                    insert_vals.append(val_sql)
                    all_params.extend(val_params)
                if insert_cols:
                    action_sql_parts.append(f"THEN INSERT ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})")
                else:
                    action_sql_parts.append("THEN INSERT DEFAULT VALUES")
            merge_sql_parts.append(" ".join(action_sql_parts))

        # Handle WHEN NOT MATCHED BY SOURCE clauses
        for action in expr.when_not_matched_by_source:
            action_sql_parts = []
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                action_sql_parts.append(f"WHEN NOT MATCHED BY SOURCE AND {cond_sql}")
                all_params.extend(cond_params)
            else:
                action_sql_parts.append("WHEN NOT MATCHED BY SOURCE")

            if action.action_type == MergeActionType.UPDATE:
                assignments = []
                for col, as_expr in action.assignments.items():
                    as_sql, as_params = as_expr.to_sql()
                    assignments.append(f"{self.format_identifier(col)} = {as_sql}")
                    all_params.extend(as_params)
                action_sql_parts.append(f"THEN UPDATE SET {', '.join(assignments)}")
            elif action.action_type == MergeActionType.DELETE:
                action_sql_parts.append("THEN DELETE")
            merge_sql_parts.append(" ".join(action_sql_parts))

        return " ".join(merge_sql_parts), tuple(all_params)


class TemporalTableMixin:
    """Mixin for temporal table support."""

    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported."""
        return False

    def format_temporal_options(
            self,
            options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """Format temporal table options."""
        if not options:
            raise ValueError(
                "Temporal options cannot be empty. If no temporal options are needed, don't call format_temporal_options.")
        sql_parts, params = ["FOR SYSTEM_TIME"], []
        # Add temporal options to SQL parts based on the options provided
        for key, value in options.items():
            sql_parts.append(f"{key.upper()} ?")
            params.append(value)
        return " ".join(sql_parts), tuple(params)


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

    def format_for_update_clause(
            self,
            clause: "ForUpdateClause"
    ) -> Tuple[str, tuple]:
        """Default implementation for FOR UPDATE clause."""
        all_params = []
        sql_parts = ["FOR UPDATE"]

        # Handle OF columns if specified
        if clause.of_columns:
            of_parts = []
            for col in clause.of_columns:
                if isinstance(col, str):
                    of_parts.append(self.format_identifier(col))
                elif hasattr(col, 'to_sql'):  # BaseExpression
                    col_sql, col_params = col.to_sql()
                    of_parts.append(col_sql)
                    all_params.extend(col_params)
            if of_parts:
                sql_parts.append(f"OF {', '.join(of_parts)}")

        # Handle NOWAIT/SKIP LOCKED options
        if clause.nowait:
            sql_parts.append("NOWAIT")
        elif clause.skip_locked:
            sql_parts.append("SKIP LOCKED")

        return " ".join(sql_parts), tuple(all_params)