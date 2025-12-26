# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

SQLite is a lightweight database with limited support for advanced SQL features.
This dialect implements only the protocols for features that SQLite actually supports,
based on the SQLite version provided at initialization.
"""
from typing import Any, Dict, List, Optional, Tuple

from rhosocial.activerecord.backend.dialect import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport,
    ReturningSupport,
    JSONSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    WindowFunctionSupport
)
from rhosocial.activerecord.backend.expression import bases
from rhosocial.activerecord.backend.expression.statements import (
    MergeActionType,
    MergeAction,
    MergeExpression,
    CreateViewExpression,
    OnConflictClause,
    AlterTableExpression,
    AddColumn,
    DropColumn,
    AlterColumn
)
from rhosocial.activerecord.backend.expression.advanced_functions import OrderedSetAggregation
from rhosocial.activerecord.backend.expression.graph import GraphVertex, GraphEdge, MatchClause, GraphEdgeDirection
from rhosocial.activerecord.backend.expression.query_sources import JSONTableColumn, JSONTableExpression
from rhosocial.activerecord.backend.expression.query_parts import (
    LimitOffsetClause,
    JoinExpression,
    GroupByHavingClause
)
from rhosocial.activerecord.backend.expression.advanced_functions import WindowFunctionCall


class SQLiteDialect(
    SQLDialectBase,
    CTESupport,
    ReturningSupport,
    JSONSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    WindowFunctionSupport
):
    """
    SQLite dialect implementation that adapts to the SQLite version.

    SQLite features and support based on version:
    - Basic and recursive CTEs (since 3.8.3)
    - Window functions (since 3.25.0)
    - RETURNING clause (since 3.35.0)
    - JSON operations (with JSON1 extension, since 3.38.0)
    - FILTER clause (since 3.10.0)
    """

    def __init__(self, version: Tuple[int, int, int] = (3, 35, 0)):
        """
        Initialize SQLite dialect with specific version.

        Args:
            version: SQLite version tuple (major, minor, patch)
        """
        self.version = version
        super().__init__()

    def get_placeholder(self) -> str:
        """SQLite uses '?' for placeholders."""
        return "?"

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the SQLite version this dialect is configured for."""
        return self.version

    # region Protocol Support Checks based on version
    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since SQLite 3.8.3."""
        return self.version >= (3, 8, 3)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since SQLite 3.8.3."""
        return self.version >= (3, 8, 3)

    def supports_materialized_cte(self) -> bool:
        """SQLite does not support MATERIALIZED hint."""
        return False

    def supports_returning_clause(self) -> bool:
        """RETURNING clause is supported since SQLite 3.35.0."""
        return self.version >= (3, 35, 0)

    def supports_window_functions(self) -> bool:
        """Window functions are supported since SQLite 3.25.0."""
        return self.version >= (3, 25, 0)

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported, since SQLite 3.25.0."""
        return self.version >= (3, 25, 0)

    def supports_filter_clause(self) -> bool:
        """FILTER clause for aggregate functions is supported since SQLite 3.10.0."""
        return self.version >= (3, 10, 0)

    def supports_json_type(self) -> bool:
        """JSON is supported with JSON1 extension."""
        return self.version >= (3, 38, 0)  # JSON1 extension available since 3.38.0

    def get_json_access_operator(self) -> str:
        """SQLite uses '->' for JSON access."""
        return "->"

    def supports_json_table(self) -> bool:
        """SQLite does not directly support JSON_TABLE as a table function."""
        return False

    def supports_ordered_set_aggregation(self) -> bool:
        """SQLite does not support ordered-set aggregate functions (WITHIN GROUP)."""
        return False

    def supports_merge_statement(self) -> bool:
        """SQLite does not support MERGE statements."""
        return False

    def supports_temporal_tables(self) -> bool:
        """SQLite does not support temporal table queries."""
        return False

    def supports_qualify_clause(self) -> bool:
        """SQLite does not support QUALIFY clause."""
        return False

    def supports_for_update_skip_locked(self) -> bool:
        """SQLite does not support FOR UPDATE/FOR SHARE with SKIP LOCKED."""
        return False

    def supports_graph_match(self) -> bool:
        """SQLite does not support graph query MATCH clause."""
        return False
    # endregion

    def format_returning_clause(
        self,
        columns: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format RETURNING clause for SQLite.

        Args:
            columns: List of column names

        Returns:
            Tuple of (SQL string, empty parameters tuple)
        """
        if not self.supports_returning_clause():
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                f"RETURNING clause requires SQLite 3.35.0+, current version is {'.'.join(map(str, self.version))}"
            )
        
        cols = [self.format_identifier(c) for c in columns]
        return f"RETURNING {', '.join(cols)}", ()

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
            raise UnsupportedFeatureError(
                self.name,
                "FILTER clause",
                f"FILTER clause requires SQLite 3.10.0+, current version is {'.'.join(map(str, self.version))}"
            )
        
        return f"FILTER (WHERE {condition_sql})", condition_params

    def format_limit_offset_clause(
        self,
        clause: "LimitOffsetClause"
    ) -> Tuple[str, tuple]:
        """
        Format LIMIT/OFFSET clause with SQLite-specific handling.

        SQLite requires LIMIT when using OFFSET alone, so we use LIMIT -1
        to indicate "no limit" when only OFFSET is specified.

        Args:
            clause: LimitOffsetClause object containing the limit and offset specifications.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Check if we have offset but no limit, which needs special handling in SQLite
        if clause.offset is not None and clause.limit is None:
            return "LIMIT -1 OFFSET ?", (clause.offset,)
        # Otherwise, use the parent implementation
        return super().format_limit_offset_clause(clause)

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

        SQLite does not support JSON_TABLE.
        """
        raise UnsupportedFeatureError(
            self.name,
            "JSON_TABLE function",
            "Consider using json_each() or json_extract() with subqueries or CTEs instead."
        )

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
        Format an ordered-set aggregate function call.

        SQLite does not support ordered-set aggregate functions (WITHIN GROUP).
        """
        raise UnsupportedFeatureError(
            self.name,
            "Ordered-set aggregate functions (WITHIN GROUP)",
            "Consider emulating with window functions or subqueries if possible."
        )

    def format_merge_statement(
        self,
        expr: "MergeExpression"
    ) -> Tuple[str, tuple]:
        """
        Formats a complete MERGE statement from a MergeExpression object.

        SQLite does not support MERGE statements.
        """
        raise UnsupportedFeatureError(
            self.name,
            "MERGE statement",
            "Consider using a combination of INSERT, UPDATE, and DELETE statements."
        )

    def format_temporal_options(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a temporal table clause.

        SQLite does not support temporal tables.
        """
        raise UnsupportedFeatureError(
            self.name,
            "Temporal table queries (FOR SYSTEM_TIME)",
            "Manage historical data through application logic or custom versioning tables."
        )

    def format_qualify_clause(
        self,
        clause: "QualifyClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a QUALIFY clause.

        SQLite does not support QUALIFY clause.
        """
        raise UnsupportedFeatureError(
            self.name,
            "QUALIFY clause",
            "Consider using a CTE or subquery with WHERE clause instead."
        )

    def format_json_expression(
        self,
        column: Any,
        path: str,
        operation: str = "->"
    ) -> Tuple[str, Tuple]:
        """
        Format JSON expression for SQLite with JSON1 extension.

        Args:
            column: Column expression or identifier
            path: JSON path
            operation: JSON operation (e.g., '->', '->>')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if not self.supports_json_type():
            raise UnsupportedFeatureError(
                self.name,
                "JSON operations",
                f"JSON operations require SQLite 3.38.0+, current version is {'.'.join(map(str, self.version))}"
            )

        # Format the column
        if isinstance(column, str):
            col_sql = self.format_identifier(column)
        else:
            col_sql, col_params = column.to_sql()

        # Use the appropriate operator
        sql = f"{col_sql} {operation} ?"
        params = (path,) + (col_params if 'col_params' in locals() else ())

        return sql, params

    def format_join_expression(
        self,
        join_expr: "JoinExpression"
    ) -> Tuple[str, Tuple]:
        """
        Format JOIN expression with SQLite-specific limitations.

        SQLite does not support RIGHT JOIN or FULL OUTER JOIN.
        """
        # Check if the join type is supported by SQLite
        join_type_upper = join_expr.join_type.upper()
        if "RIGHT" in join_type_upper or "FULL" in join_type_upper:
            raise UnsupportedFeatureError(
                self.name,
                join_expr.join_type,
                "SQLite does not support RIGHT JOIN or FULL OUTER JOIN"
            )

        # Delegate to parent implementation for supported joins
        return super().format_join_expression(join_expr)

    def format_alter_table_statement(
        self,
        expr: "AlterTableExpression"
    ) -> Tuple[str, tuple]:
        """
        Format ALTER TABLE statement with SQLite-specific limitations.

        SQLite only supports limited ALTER operations.
        """
        from rhosocial.activerecord.backend.expression.statements import (
            AlterTableActionType,
            AddColumn,
            DropColumn,
            RenameColumn,
            RenameTable
        )

        all_params = []
        parts = [f"ALTER TABLE {self.format_identifier(expr.table_name)}"]

        # Process each action and check if it's supported by SQLite
        action_parts = []
        for action in expr.actions:
            # Check if action type is supported by SQLite
            # SQLite only supports ADD COLUMN, RENAME COLUMN, and RENAME TABLE
            action_type = getattr(action, 'action_type', None)

            # Check if the action is of a type that SQLite doesn't support
            if not isinstance(action, (AddColumn, DropColumn, RenameColumn, RenameTable)):
                action_name = str(type(action).__name__)
                raise UnsupportedFeatureError(
                    self.name,
                    action_name,
                    "SQLite only supports ADD COLUMN, DROP COLUMN, RENAME COLUMN, and RENAME TABLE operations in ALTER TABLE"
                )

            action_sql, action_params = action.to_sql()
            action_parts.append(action_sql)
            all_params.extend(action_params)

        if action_parts:
            parts.append(" " + ", ".join(action_parts))

        return " ".join(parts), tuple(all_params)

    def format_add_column_action(
        self,
        action: "AddColumn"
    ) -> Tuple[str, tuple]:
        """
        Format ADD COLUMN action for SQLite.
        """
        column_sql, column_params = self.format_column_definition(action.column)
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(
        self,
        action: "DropColumn"
    ) -> Tuple[str, tuple]:
        """
        Format DROP COLUMN action for SQLite.

        SQLite does not support DROP COLUMN in older versions.
        """
        # Check if the version supports DROP COLUMN
        # According to SQLite documentation, ALTER TABLE DROP COLUMN was added in version 3.35.0
        if self.version < (3, 35, 0):
            raise UnsupportedFeatureError(
                self.name,
                "DROP COLUMN",
                f"DROP COLUMN requires SQLite 3.35.0+, current version is {'.'.join(map(str, self.version))}"
            )

        if_exists_part = "IF EXISTS " if getattr(action, 'if_exists', False) else ""
        return f"DROP COLUMN {if_exists_part}{self.format_identifier(action.column_name)}", ()

    def format_alter_column_action(
        self,
        action: "AlterColumn"
    ) -> Tuple[str, tuple]:
        """
        Format ALTER COLUMN action for SQLite.

        SQLite does not support standard ALTER COLUMN syntax.
        """
        raise UnsupportedFeatureError(
            self.name,
            "ALTER COLUMN",
            "SQLite does not support ALTER COLUMN. Consider using a table rebuild approach."
        )

    def format_array_expression(
        self,
        operation: str,
        elements: Optional[List["bases.BaseExpression"]],
        base_expr: Optional["bases.BaseExpression"],
        index_expr: Optional["bases.BaseExpression"]
    ) -> Tuple[str, Tuple]:
        """
        Format array expression for SQLite.

        SQLite does not support native array types.
        """
        raise UnsupportedFeatureError(
            self.name,
            "Array operations",
            "SQLite does not support native array types. Consider using JSON or comma-separated values."
        )

    def format_create_view_statement(
        self,
        expr: "CreateViewExpression"
    ) -> Tuple[str, tuple]:
        """
        Format CREATE VIEW statement for SQLite.
        """
        # Basic statement
        replace_part = "OR REPLACE " if expr.replace else ""
        temporary_part = "TEMP " if expr.temporary else ""
        sql_parts = [f"CREATE {replace_part}{temporary_part}VIEW {self.format_identifier(expr.view_name)}"]

        all_params = []

        # Add column aliases if specified
        if expr.column_aliases:
            aliases_str = ", ".join(self.format_identifier(alias) for alias in expr.column_aliases)
            sql_parts.append(f"({aliases_str})")

        # Add AS and the query
        query_sql, query_params = expr.query.to_sql()
        sql_parts.append(f" AS {query_sql}")
        all_params.extend(query_params)

        return " ".join(sql_parts), tuple(all_params)

    def format_case_expression(
        self,
        value_sql: Optional[str],
        value_params: Optional[tuple],
        conditions_results: List[Tuple[str, str, tuple, tuple]],
        else_result_sql: Optional[str],
        else_result_params: Optional[tuple],
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Format CASE expression for SQLite.
        """
        all_params = list(value_params) if value_params else []

        # Validate that there is at least one condition-result pair for a valid CASE expression
        if not conditions_results:
            raise ValueError("CASE expression must have at least one WHEN/THEN condition-result pair.")

        # Build the CASE expression
        parts = ["CASE"]
        if value_sql:
            parts.append(value_sql)

        for condition_sql, result_sql, condition_params, result_params in conditions_results:
            parts.append(f"WHEN {condition_sql} THEN {result_sql}")
            all_params.extend(condition_params)
            all_params.extend(result_params)

        if else_result_sql:
            parts.append(f"ELSE {else_result_sql}")
            all_params.extend(else_result_params)

        parts.append("END")

        case_sql = " ".join(parts)

        # Add alias if provided
        if alias:
            case_sql = f"{case_sql} AS {self.format_identifier(alias)}"

        return case_sql, tuple(all_params)

    def format_binary_arithmetic_expression(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format binary arithmetic expression for SQLite.

        Ensures SQLite-compatible operators and syntax.
        """
        # In SQLite, the % operator is supported directly, unlike some other databases
        sql = f"{left_sql} {op} {right_sql}"
        return sql, left_params + right_params

    def format_identifier(self, identifier: str) -> str:
        """
        Format identifier using SQLite's double quote quoting mechanism.

        Args:
            identifier: Raw identifier string

        Returns:
            Quoted identifier with escaped internal quotes
        """
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def format_function_call(
        self,
        func_name: str,
        args_sql: List[str],
        args_params: List[tuple],
        is_distinct: bool,
        alias: Optional[str] = None,
        filter_sql: Optional[str] = None,
        filter_params: Optional[tuple] = None
    ) -> Tuple[str, Tuple]:
        """
        Format function call with SQLite-specific considerations.
        """
        from rhosocial.activerecord.backend.dialect.protocols import FilterClauseSupport  # Local import to avoid circular dependency

        distinct = "DISTINCT " if is_distinct else ""
        args_sql_str = ", ".join(args_sql)
        func_call_sql = f"{func_name.upper()}({distinct}{args_sql_str})"

        all_params: List[Any] = []
        for param_tuple in args_params:
            all_params.extend(param_tuple)

        # Handle FILTER clause
        if filter_sql:
            if isinstance(self, FilterClauseSupport) and self.supports_filter_clause():
                # Ensure filter_params is a tuple, default to empty tuple if None
                actual_filter_params = filter_params if filter_params is not None else ()
                filter_clause_sql, filter_clause_params = self.format_filter_clause(filter_sql, actual_filter_params)
                func_call_sql += f" {filter_clause_sql}"
                all_params.extend(filter_clause_params)
            else:
                raise UnsupportedFeatureError(
                    self.name,
                    "FILTER clause in aggregate functions",
                    "Use a CASE expression inside the aggregate function instead."
                )

        if alias:
            return f"{func_call_sql} AS {self.format_identifier(alias)}", tuple(all_params)
        return func_call_sql, tuple(all_params)

    def format_group_by_having_clause(
        self,
        clause: "GroupByHavingClause"
    ) -> Tuple[str, tuple]:
        """
        Format combined GROUP BY and HAVING clauses for SQLite.
        """
        all_params = []

        # Process GROUP BY expressions
        group_parts = []
        for expr in clause.group_by:
            expr_sql, expr_params = expr.to_sql()
            group_parts.append(expr_sql)
            all_params.extend(expr_params)

        sql_parts = []
        if group_parts:
            sql_parts.append(f"GROUP BY {', '.join(group_parts)}")

        # Process HAVING condition
        if clause.having:
            having_sql, having_params = clause.having.to_sql()
            sql_parts.append(f"HAVING {having_sql}")
            all_params.extend(having_params)

        return " ".join(sql_parts), tuple(all_params)

    def format_window_function_call(
        self,
        call: "WindowFunctionCall"
    ) -> Tuple[str, tuple]:
        """
        Format window function call for SQLite.

        Requires SQLite 3.25.0+
        """
        if not self.supports_window_functions():
            raise UnsupportedFeatureError(
                self.name,
                "Window functions",
                f"Window functions require SQLite 3.25.0+, current version is {'.'.join(map(str, self.version))}"
            )

        # Delegate to parent implementation since SQLite follows standard syntax
        return super().format_window_function_call(call)

    def format_on_conflict_clause(
        self,
        expr: "OnConflictClause"
    ) -> Tuple[str, tuple]:
        """
        Format ON CONFLICT clause for SQLite.

        SQLite uses ON CONFLICT instead of standard ON DUPLICATE KEY UPDATE.
        """
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

        # Add resolution action
        if expr.do_nothing:
            parts.append("DO NOTHING")
        elif expr.update_assignments:
            # DO UPDATE SET assignments (SQLite's UPSERT)
            update_parts = []
            for col, expr_val in expr.update_assignments.items():
                if isinstance(expr_val, bases.BaseExpression):
                    val_sql, val_params = expr_val.to_sql()
                    update_parts.append(f"{self.format_identifier(col)} = {val_sql}")
                    all_params.extend(val_params)
                else:
                    update_parts.append(f"{self.format_identifier(col)} = {self.get_placeholder()}")
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

    def format_values_expression(
        self,
        values: List[Tuple[Any, ...]],
        alias: str,
        column_names: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format VALUES expression as data source for SQLite.
        """
        all_params: List[Any] = []
        rows_sql = []
        for row in values:
            placeholders = ", ".join([self.get_placeholder()] * len(row))
            rows_sql.append(f"({placeholders})")
            all_params.extend(list(row))  # Convert to list to ensure it's iterable

        values_sql = ", ".join(rows_sql)
        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"

        sql = f"(VALUES {values_sql}) AS {self.format_identifier(alias)}{cols_sql}"
        return sql, tuple(all_params)

    def format_for_update_clause(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE/FOR SHARE clause.

        SQLite does not support FOR UPDATE/FOR SHARE.
        """
        raise UnsupportedFeatureError(
            self.name,
            "FOR UPDATE / FOR SHARE clauses",
            "Implement locking at the application level or use transactions for atomicity."
        )

    def format_match_clause(
        self,
        clause: "MatchClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a MATCH clause.

        SQLite does not support graph query MATCH clause.
        """
        raise UnsupportedFeatureError(
            self.name,
            "Graph query MATCH clause",
            "Implement graph traversal logic in application code or use a graph database."
        )