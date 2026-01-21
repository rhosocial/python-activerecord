# src/rhosocial/activerecord/backend/dialect/base.py
"""
SQL dialect abstract base classes and common implementations.

This module defines the core dialect interfaces and provides default
implementations for standard SQL features.
"""
from typing import Any, List, Optional, Tuple, Union, TYPE_CHECKING

from .exceptions import ProtocolNotImplementedError, UnsupportedFeatureError
from ..expression import bases, ForUpdateClause
from ..expression.statements import QueryExpression, ColumnDefinition

if TYPE_CHECKING:
    from ..expression.statements import (
        # DML Statements
        QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
        CreateTableExpression, DropTableExpression,
        AlterTableExpression, CreateViewExpression, DropViewExpression,
        # Alter Table Actions
        AddColumn, DropColumn, AlterColumn, AddIndex, DropIndex, AddTableConstraint, DropTableConstraint,
        RenameColumn, RenameTable,
        # Constraints
        TableConstraintType
    )
    from ..expression.query_parts import (
        WhereClause, GroupByHavingClause, LimitOffsetClause, OrderByClause
    )


class SQLDialectBase:
    """
    Abstract base class for SQL dialects.

    This class defines the core interface that all database dialects must implement.
    It only includes standard SQL features that all databases should support.
    Database-specific features are declared through Protocol implementations.

    Design principles:
    1. Only define core SQL methods (supported by all databases)
    2. No database-specific functionality in the base class
    3. Subclasses declare additional capabilities via Protocols
    """

    # region Core & General
    def __init__(self) -> None:
        """Initialize SQL dialect."""
        # Add strict validation flag with default as True for safety
        self.strict_validation = True

    @property
    def name(self) -> str:
        """
        Get dialect name for error messages.

        Returns:
            Dialect name (class name without 'Dialect' suffix)
        """
        return self.__class__.__name__.replace("Dialect", "")

    def get_parameter_placeholder(self, position: int = 0) -> str:
        """
        Get parameter placeholder with position.

        For dialects using positional placeholders, position is ignored.

        Args:
            position: Parameter position (1-indexed)

        Returns:
            Placeholder string
        """
        return "?"
    # endregion Core & General

    # region Full Statement Formatting
    # region DML Statements
    def require_protocol(
        self,
        protocol_type: type,
        feature_name: str,
        required_by: str
    ) -> None:
        """
        Check if dialect implements a required protocol.

        Args:
            protocol_type: Protocol class (e.g., WindowFunctionSupport)
            feature_name: Feature name for error message
            required_by: Component name requiring the protocol

        Raises:
            ProtocolNotImplementedError: If protocol is not implemented
        """
        if not isinstance(self, protocol_type):
            raise ProtocolNotImplementedError(
                dialect_name=self.name,
                protocol_name=protocol_type.__name__,
                required_by=required_by
            )

    def check_feature_support(
        self,
        check_method: str,
        feature_name: str,
        suggestion: Optional[str] = None
    ) -> None:
        """
        Check if dialect supports a specific feature.

        Args:
            check_method: Method name to call (e.g., 'supports_rollup')
            feature_name: Feature name for error message
            suggestion: Optional suggestion for alternative approach

        Raises:
            UnsupportedFeatureError: If feature is not supported
        """
        is_supported = False
        if hasattr(self, check_method):
            is_supported = getattr(self, check_method)()

        if not is_supported:
            raise UnsupportedFeatureError(
                dialect_name=self.name,
                feature_name=feature_name,
                suggestion=suggestion
            )
    # endregion Utilities

    # region Full Statement Formatting
    # region DML Statements
    def format_identifier(self, identifier: str) -> str:
        """
        Format identifier using SQL standard double quotes.

        Args:
            identifier: Raw identifier

        Returns:
            Quoted identifier with escaped internal quotes
        """
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def format_column(
        self,
        name: str,
        table: Optional[str] = None,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format column reference."""
        if table:
            col_sql = f'{self.format_identifier(table)}.{self.format_identifier(name)}'
        else:
            col_sql = self.format_identifier(name)

        if alias:
            return f"{col_sql} AS {self.format_identifier(alias)}", ()
        return col_sql, ()

    def format_wildcard(
        self,
        table: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format wildcard expression (* or table.*)."""
        if table:
            wildcard_sql = f'{self.format_identifier(table)}.*'
        else:
            wildcard_sql = '*'

        return wildcard_sql, ()

    def supports_explicit_inner_join(self) -> bool:
        """
        Determines whether the dialect should explicitly use 'INNER JOIN' instead of just 'JOIN'.

        Most SQL dialects treat 'JOIN' and 'INNER JOIN' as equivalent, but some users or
        specific database configurations may prefer explicit 'INNER' keyword.

        Returns:
            bool: True if the dialect should use 'INNER JOIN', False for just 'JOIN' (default)
        """
        return False  # Default to minimal form: JOIN instead of INNER JOIN

    def format_table(
        self,
        table_name: str,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format table reference."""
        table_sql = self.format_identifier(table_name)
        if alias:
            return f"{table_sql} AS {self.format_identifier(alias)}", ()
        return table_sql, ()

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
        """Format function call."""
        distinct = "DISTINCT " if is_distinct else ""
        args_sql_str = ", ".join(args_sql)
        func_call_sql = f"{func_name.upper()}({distinct}{args_sql_str})"

        all_params: List[Any] = []
        for param_tuple in args_params:
            all_params.extend(param_tuple)

        # Handle FILTER clause - this requires the FilterClauseMixin
        if filter_sql:
            # Check if the dialect supports filter clause
            from .protocols import FilterClauseSupport
            if isinstance(self, FilterClauseSupport):
                if hasattr(self, 'supports_filter_clause') and self.supports_filter_clause():
                    # If the dialect supports filter clause, it should have the format_filter_clause method
                    if hasattr(self, 'format_filter_clause'):
                        # Ensure filter_params is a tuple, default to empty tuple if None
                        actual_filter_params = filter_params if filter_params is not None else ()
                        filter_clause_sql, filter_clause_params = self.format_filter_clause(filter_sql, actual_filter_params)
                        func_call_sql += f" {filter_clause_sql}"
                        all_params.extend(filter_clause_params)
                    else:
                        # If the method doesn't exist despite protocol implementation, raise error
                        raise UnsupportedFeatureError(
                            self.name,
                            "FILTER clause in aggregate functions",
                            "Dialect implements FilterClauseSupport but missing format_filter_clause method."
                        )
                else:
                    raise UnsupportedFeatureError(
                        self.name,
                        "FILTER clause in aggregate functions",
                        "Use a CASE expression inside the aggregate function instead."
                    )
            else:
                # If the dialect doesn't implement FilterClauseSupport, raise error
                raise UnsupportedFeatureError(
                    self.name,
                    "FILTER clause in aggregate functions",
                    "Use a CASE expression inside the aggregate function instead."
                )

        if alias:
            return f"{func_call_sql} AS {self.format_identifier(alias)}", tuple(all_params)
        return func_call_sql, tuple(all_params)

    def format_comparison_predicate(
        self,
        op: str,
        left: "bases.BaseExpression",
        right: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        # If the right operand is a QueryExpression, wrap its SQL in parentheses
        if isinstance(right, QueryExpression):
            right_sql = f"({right_sql})"
        sql = f"{left_sql} {op} {right_sql}"
        return sql, left_params + right_params

    def format_logical_predicate(
        self,
        op: str,
        *predicates: "bases.SQLPredicate"
    ) -> Tuple[str, Tuple]:
        """Format logical predicate (AND, OR, NOT)."""
        if op.upper() == "NOT" and len(predicates) == 1:
            sql, params = predicates[0].to_sql()
            return f"NOT ({sql})", params # KEEP () here for NOT
        else:
            parts = []
            all_params: List[Any] = []
            for predicate in predicates:
                sql, params = predicate.to_sql()
                parts.append(sql) # Removed () around sql
                all_params.extend(params)
            sql = f" {op} ".join(parts)
            return sql, tuple(all_params) # Removed outer () here

    def format_in_predicate(
        self,
        expr: "bases.BaseExpression",
        values: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format IN predicate."""
        expr_sql, expr_params = expr.to_sql()
        values_sql, values_params = values.to_sql()
        sql = f"{expr_sql} IN {values_sql}"
        return sql, expr_params + values_params

    def format_in_predicate_with_literal_values(
        self,
        expr: "bases.BaseExpression",
        literal_values: tuple
    ) -> Tuple[str, Tuple]:
        """Format IN predicate with literal values."""
        expr_sql, expr_params = expr.to_sql()
        if not literal_values:  # Handle empty list case for IN ()
            values_sql = "()"
            values_params = ()
        else:
            placeholders = ", ".join([self.get_parameter_placeholder()] * len(literal_values))
            values_sql = f"({placeholders})"
            values_params = tuple(literal_values)  # Convert to tuple to ensure correct type
        sql = f"{expr_sql} IN {values_sql}"
        return sql, expr_params + values_params

    def format_between_predicate(
        self,
        expr: "bases.BaseExpression",
        low: "bases.BaseExpression",
        high: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format BETWEEN predicate."""
        expr_sql, expr_params = expr.to_sql()
        low_sql, low_params = low.to_sql()
        high_sql, high_params = high.to_sql()
        sql = f"{expr_sql} BETWEEN {low_sql} AND {high_sql}"
        return sql, expr_params + low_params + high_params

    def format_is_null_predicate(
        self,
        expr: "bases.BaseExpression",
        is_not: bool
    ) -> Tuple[str, Tuple]:
        """Format IS NULL predicate."""
        expr_sql, expr_params = expr.to_sql()
        not_str = " NOT" if is_not else ""
        sql = f"{expr_sql} IS{not_str} NULL"
        return sql, expr_params

    def format_exists_expression(
        self,
        subquery: "bases.BaseExpression",
        is_not: bool
    ) -> Tuple[str, Tuple]:
        """Format EXISTS predicate."""
        subquery_sql, subquery_params = subquery.to_sql()
        exists_clause = "NOT EXISTS" if is_not else "EXISTS"
        sql = f"{exists_clause} {subquery_sql}"
        return sql, subquery_params

    def format_add_column_action(
        self,
        action: "AddColumn"
    ) -> Tuple[str, tuple]:
        """Format ADD COLUMN action."""
        column_sql, column_params = self.format_column_definition(action.column)
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(
        self,
        action: "DropColumn"
    ) -> Tuple[str, tuple]:
        """Format DROP COLUMN action."""
        if hasattr(action, 'if_exists') and action.if_exists:
            return f"DROP COLUMN IF EXISTS {self.format_identifier(action.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()

    def format_alter_column_action(
        self,
        action: "AlterColumn"
    ) -> Tuple[str, tuple]:
        """Format ALTER COLUMN action."""
        all_params = []
        # Handle operation that might be an enum by getting its string value
        operation_str = str(action.operation)
        if hasattr(action.operation, 'value'):
            operation_str = action.operation.value
        elif hasattr(action.operation, '__str__'):
            operation_str = str(action.operation)

        column_part = f"ALTER COLUMN {self.format_identifier(action.column_name)} {operation_str}"
        if hasattr(action, 'new_value') and action.new_value is not None:
            # Handle different types of new_value based on operation
            if operation_str == "SET DATA TYPE":
                # For SET DATA TYPE, new_value is a type specification, not a parameter
                column_part += f" {action.new_value}"
            elif isinstance(action.new_value, str):
                # Handle literal strings
                column_part += f" {self.get_parameter_placeholder()}"
                all_params.append(action.new_value)
            elif hasattr(action.new_value, 'to_sql') and callable(getattr(action.new_value, 'to_sql')):
                # If it's an expression (like FunctionCall), format it
                value_sql, value_params = action.new_value.to_sql()
                column_part += f" {value_sql}"
                all_params.extend(value_params)
            else:
                # Handle other literal values
                column_part += f" {self.get_parameter_placeholder()}"
                all_params.append(action.new_value)
        # Add cascade if specified
        if hasattr(action, 'cascade') and action.cascade:
            column_part += " CASCADE"
        return column_part, tuple(all_params)

    def format_add_table_constraint_action(
        self,
        action: "AddTableConstraint"
    ) -> Tuple[str, tuple]:
        """Format ADD CONSTRAINT action per SQL standard."""
        from ..expression.statements import TableConstraintType

        all_params = []
        parts = []
        if action.constraint.name:
            parts.append(f"CONSTRAINT {self.format_identifier(action.constraint.name)}")

        # Add the constraint type and details based on the constraint type
        if action.constraint.constraint_type == TableConstraintType.PRIMARY_KEY:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
            else:
                parts.append("PRIMARY KEY")
        elif action.constraint.constraint_type == TableConstraintType.UNIQUE:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"UNIQUE ({cols_str})")
            else:
                parts.append("UNIQUE")
        elif action.constraint.constraint_type == TableConstraintType.CHECK and action.constraint.check_condition:
            check_sql, check_params = action.constraint.check_condition.to_sql()
            parts.append(f"CHECK ({check_sql})")
            all_params.extend(check_params)
        elif action.constraint.constraint_type == TableConstraintType.FOREIGN_KEY:
            if action.constraint.columns and action.constraint.foreign_key_table:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                ref_table = self.format_identifier(action.constraint.foreign_key_table)
                ref_cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.foreign_key_columns) if action.constraint.foreign_key_columns else ""
                if ref_cols_str:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}({ref_cols_str})")
                else:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}")
            else:
                parts.append("FOREIGN KEY")
        else:
            # For unknown constraint types, just add the name
            parts.append("UNKNOWN CONSTRAINT")

        return f"ADD {' '.join(parts)}", tuple(all_params)


    def format_add_index_action(
        self,
        action: "AddIndex"
    ) -> Tuple[str, tuple]:
        """Format ADD INDEX action."""
        return f"ADD INDEX {self.format_identifier(action.index.name)}", ()

    def format_drop_index_action(
        self,
        action: "DropIndex"
    ) -> Tuple[str, tuple]:
        """Format DROP INDEX action."""
        cmd = f"DROP INDEX {self.format_identifier(action.index_name)}"
        if hasattr(action, 'if_exists') and action.if_exists:
            cmd = f"DROP INDEX IF EXISTS {self.format_identifier(action.index_name)}"
        return cmd, ()

    def format_drop_table_constraint_action(
        self,
        action: "DropTableConstraint"
    ) -> Tuple[str, tuple]:
        """Format DROP CONSTRAINT action per SQL standard."""
        result = f"DROP CONSTRAINT {self.format_identifier(action.constraint_name)}"
        if hasattr(action, 'cascade') and action.cascade:
            result += " CASCADE"
        return result, ()


    def format_rename_column_action(self, action: "RenameColumn") -> Tuple[str, tuple]:
        """Format RENAME COLUMN action per SQL standard."""
        return f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}", ()

    def format_rename_table_action(self, action: "RenameTable") -> Tuple[str, tuple]:
        """Format RENAME TABLE action per SQL standard."""
        return f"RENAME TO {self.format_identifier(action.new_name)}", ()

    def format_any_expression(
        self,
        expr: "bases.BaseExpression",
        op: str,
        array_expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format ANY expression."""
        expr_sql, expr_params = expr.to_sql()
        # Check if array_expr is a Literal with list/tuple value by checking for 'value' attribute
        if (hasattr(array_expr, 'value') and
            isinstance(array_expr.value, (list, tuple))):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        sql = f"({expr_sql} {op} ANY{array_sql})"
        return sql, tuple(list(expr_params) + list(array_params))

    def format_all_expression(
        self,
        expr: "bases.BaseExpression",
        op: str,
        array_expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format ALL expression."""
        expr_sql, expr_params = expr.to_sql()
        # Check if array_expr is a Literal with list/tuple value by checking for 'value' attribute
        if (hasattr(array_expr, 'value') and
            isinstance(array_expr.value, (list, tuple))):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        sql = f"({expr_sql} {op} ALL{array_sql})"
        return sql, tuple(list(expr_params) + list(array_params))

    def format_like_predicate(
        self,
        op: str,
        expr: "bases.BaseExpression",
        pattern: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format LIKE predicate."""
        expr_sql, expr_params = expr.to_sql()
        pattern_sql, pattern_params = pattern.to_sql()
        sql = f"{expr_sql} {op} {pattern_sql}"
        return sql, expr_params + pattern_params

    def format_binary_operator(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        sql = f"{left_sql} {op} {right_sql}"
        return sql, left_params + right_params

    def format_unary_operator(
        self,
        op: str,
        operand_sql: str,
        pos: str,
        operand_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format unary operator."""
        if pos == 'before':
            sql = f"{op} {operand_sql}"
        else:
            sql = f"{operand_sql} {op}"
        return sql, operand_params

    def format_binary_arithmetic_expression(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format binary arithmetic expression."""
        sql = f"{left_sql} {op} {right_sql}"
        return sql, left_params + right_params


    def format_cast_expression(
        self,
        expr_sql: str,
        target_type: str,
        expr_params: tuple,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format CAST expression."""
        sql = f"CAST({expr_sql} AS {target_type})"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, expr_params

    def format_subquery(
        self,
        subquery_sql: str,
        subquery_params: tuple,
        alias: str
    ) -> Tuple[str, Tuple]:
        """Format subquery."""
        return f"{subquery_sql} AS {self.format_identifier(alias)}", subquery_params

    def format_alias(
        self,
        expression_sql: str,
        alias: str,
        expression_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format alias."""
        sql = f"{expression_sql} AS {self.format_identifier(alias)}"
        return sql, expression_params

    def format_values_expression(
        self,
        values: List[Tuple[Any, ...]],
        alias: Optional[str],
        column_names: Optional[List[str]]
    ) -> Tuple[str, Tuple]:
        """Format VALUES expression as data source."""
        all_params: List[Any] = []
        rows_sql = []
        for row in values:
            placeholders = ", ".join([self.get_parameter_placeholder()] * len(row))
            rows_sql.append(f"({placeholders})")
            all_params.extend(row)

        values_sql = ", ".join(rows_sql)
        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"

        if alias is not None:
            # Format with alias: (VALUES (...)) AS alias(...)
            sql = f"(VALUES {values_sql}) AS {self.format_identifier(alias)}{cols_sql}"
        else:
            # Format without alias: VALUES (...)
            sql = f"VALUES {values_sql}{cols_sql}"

        return sql, tuple(all_params)

    def supports_offset_without_limit(self) -> bool:
        """Check if the dialect supports OFFSET clause without LIMIT clause."""
        # By default, assume the dialect does not support OFFSET without LIMIT
        return False

    def format_limit_offset(self, limit=None, offset=None) -> Tuple[str, List]:
        """
        Format LIMIT and/or OFFSET clause.

        Args:
            limit: Limit value (optional)
            offset: Offset value (optional)

        Returns:
            Tuple of (SQL string, parameters list)
        """
        parts = []
        params = []

        if limit is not None:
            parts.append(f"LIMIT {self.get_parameter_placeholder()}")
            params.append(limit)

        if offset is not None:
            parts.append(f"OFFSET {self.get_parameter_placeholder()}")
            params.append(offset)

        if not parts:
            return None, []

        return " ".join(parts), params

    def format_limit_offset_clause(self, clause: "LimitOffsetClause") -> Tuple[str, tuple]:
        """Default implementation for LIMIT and OFFSET clause formatting."""
        all_params = []

        parts = []

        if clause.limit is not None:
            # Handle limit value - might be int or expression
            if hasattr(clause.limit, 'to_sql'):
                limit_sql, limit_params = clause.limit.to_sql()
                parts.append(f"LIMIT {limit_sql}")
                all_params.extend(limit_params)
            else:
                parts.append(f"LIMIT {self.get_parameter_placeholder()}")
                all_params.append(clause.limit)

        if clause.offset is not None:
            # Handle offset value - might be int or expression
            if hasattr(clause.offset, 'to_sql'):
                offset_sql, offset_params = clause.offset.to_sql()
                parts.append(f"OFFSET {offset_sql}")
                all_params.extend(offset_params)
            else:
                parts.append(f"OFFSET {self.get_parameter_placeholder()}")
                all_params.append(clause.offset)

        return " ".join(parts), tuple(all_params)

    def format_query_statement(self, expr: "QueryExpression") -> Tuple[str, tuple]:
        """Format a complete SELECT statement from a QueryExpression object.

        This method performs strict parameter validation for SQL standard compliance
        by default. To bypass # pragma: no cover validation for performance optimization, set strict_validation=False
        on the dialect instance.
        """
        # Perform strict parameter validation for SQL standard compliance
        # This validation may impact performance. If performance is critical,
        # dialect implementations can set strict_validation=False.
        if self.strict_validation:
            expr.validate(strict=True)

        all_params: List[Any] = []

        # SELECT clause with optional DISTINCT/ALL modifier
        select_parts = []
        for e in expr.select:
            expr_sql, expr_params = e.to_sql()
            select_parts.append(expr_sql)
            all_params.extend(expr_params)

        # Add DISTINCT/ALL modifier if present
        modifier_str = ""
        if expr.select_modifier:
            modifier_str = f" {expr.select_modifier.value}"

        select_sql = f"SELECT{modifier_str} " + ", ".join(select_parts)

        from_sql = ""
        if expr.from_:
            if isinstance(expr.from_, str):
                # Handle string table name
                from_expr_sql = self.format_identifier(expr.from_)
                from_expr_params = []
            elif isinstance(expr.from_, list):
                # Handle list of FROM sources (comma-separated tables/subqueries - implicit CROSS JOIN)
                from_parts = []
                from_expr_params = []
                for source in expr.from_:
                    if isinstance(source, str):
                        # String table name in list
                        part_sql = self.format_identifier(source)
                        part_params = []
                    else:  # Assume it's a BaseExpression
                        part_sql, part_params = source.to_sql()
                        # For ValuesExpression used as FROM source in list, wrap in parentheses
                        # This is required by SQL standard for VALUES in FROM clause
                        if hasattr(source, '__class__') and source.__class__.__name__ == "ValuesExpression":
                            part_sql = f"({part_sql})"
                    from_parts.append(part_sql)
                    from_expr_params.extend(part_params)
                from_expr_sql = ", ".join(from_parts)
            else: # Assume it's a single BaseExpression
                from_expr_sql, from_expr_params = expr.from_.to_sql()
                # For ValuesExpression used as FROM source, wrap in parentheses
                # This is required by SQL standard for VALUES in FROM clause
                if hasattr(expr.from_, '__class__') and expr.from_.__class__.__name__ == "ValuesExpression":
                    from_expr_sql = f"({from_expr_sql})"
            from_sql = f" FROM {from_expr_sql}"
            all_params.extend(from_expr_params)
        where_sql = ""
        if expr.where:
            where_expr_sql, where_expr_params = expr.where.to_sql()
            where_sql = f" {where_expr_sql}"
            all_params.extend(where_expr_params)
        # Handle group_by_having clause which combines GROUP BY and HAVING
        group_by_having_sql = ""
        if expr.group_by_having:
            gbh_expr_sql, gbh_expr_params = expr.group_by_having.to_sql()
            group_by_having_sql = f" {gbh_expr_sql}"
            all_params.extend(gbh_expr_params)
        order_by_sql = ""
        if expr.order_by:
            order_by_expr_sql, order_by_expr_params = expr.order_by.to_sql()
            order_by_sql = f" {order_by_expr_sql}"
            all_params.extend(order_by_expr_params)
        qualify_sql = ""
        if expr.qualify:
            qualify_expr_sql, qualify_expr_params = expr.qualify.to_sql()
            qualify_sql = f" QUALIFY {qualify_expr_sql}"
            all_params.extend(qualify_expr_params)

        # Build initial SQL without FOR UPDATE
        sql = f"{select_sql}{from_sql}{where_sql}{group_by_having_sql}{order_by_sql}{qualify_sql}"

        # Add FOR UPDATE clause at the end (if present)
        if expr.for_update:
            for_update_sql, for_update_params = expr.for_update.to_sql()
            if for_update_sql:
                sql += f" {for_update_sql}"
                all_params.extend(for_update_params)

        # Add LIMIT/OFFSET clause at the end (if present)
        if expr.limit_offset:
            limit_offset_sql, limit_offset_params = expr.limit_offset.to_sql()
            if limit_offset_sql:
                sql += f" {limit_offset_sql}"
                all_params.extend(limit_offset_params)
        return sql, tuple(all_params)

    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Format INSERT statement.

        This method performs strict parameter validation for SQL standard compliance
        by default. To bypass # pragma: no cover validation for performance optimization, set strict_validation=False
        on the dialect instance.
        """
        # Perform strict parameter validation for SQL standard compliance
        # This validation may impact performance. If performance is critical,
        # dialect implementations can set strict_validation=False.
        if self.strict_validation:
            expr.validate(strict=True)

        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)

        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"

        source_sql = ""
        # Import here to avoid circular imports
        from ..expression.statements import DefaultValuesSource, ValuesSource, SelectSource
        if isinstance(expr.source, DefaultValuesSource):
            source_sql = "DEFAULT VALUES"
        elif isinstance(expr.source, ValuesSource):
            all_rows_sql = []
            for row in expr.source.values_list:
                row_sql, row_params = [], []
                for val in row:
                    s, p = val.to_sql()
                    row_sql.append(s)
                    row_params.extend(p)
                all_rows_sql.append(f"({', '.join(row_sql)})")
                all_params.extend(row_params)
            source_sql = "VALUES " + ", ".join(all_rows_sql)
        elif isinstance(expr.source, SelectSource):
            s_sql, s_params = expr.source.select_query.to_sql()
            source_sql = s_sql
            all_params.extend(s_params)

        sql = f"INSERT INTO {table_sql} {columns_sql} {source_sql}".strip()

        if expr.on_conflict:
            conflict_sql, conflict_params = expr.on_conflict.to_sql()
            sql += f" {conflict_sql}"
            all_params.extend(conflict_params)

        if expr.returning:
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            sql += f" {returning_sql}"
            all_params.extend(returning_params)

        return sql, tuple(all_params)

    def format_update_statement(self, expr: "UpdateExpression") -> Tuple[str, tuple]:
        all_params: List[Any] = []

        # Target table (expr.table is a TableExpression)
        table_sql, table_params = expr.table.to_sql()
        all_params.extend(table_params)

        # Assignments (SET clause)
        assignment_parts = []
        for col, e in expr.assignments.items():
            col_sql = self.format_identifier(col) # Column name is still a string
            expr_sql, expr_params = e.to_sql()
            assignment_parts.append(f"{col_sql} = {expr_sql}")
            all_params.extend(expr_params)
        assignments_sql = ", ".join(assignment_parts)

        # Build SQL parts
        current_sql = f"UPDATE {table_sql} SET {assignments_sql}"

        # FROM clause
        if expr.from_:
            from_sql_parts = []
            from_params: List[Any] = []

            # Helper to format a single FROM source
            def _format_single_from_source(source: Union[str, "bases.BaseExpression"]) -> Tuple[str, List[Any]]:
                if isinstance(source, str):
                    return self.format_identifier(source), []
                # Import here to avoid circular imports
                from ..expression.statements import QueryExpression
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql() # Get bare SQL
                    # Convert tuple to list to match return type
                    return f"({s_sql})", list(s_params) # Add parentheses
                if isinstance(source, bases.BaseExpression): # Explicitly check for BaseExpression
                    s_sql, s_params = source.to_sql()
                    # Convert tuple to list to match return type
                    return s_sql, list(s_params)
                raise TypeError(f"Unsupported FROM source type: {type(source)}")

            if isinstance(expr.from_, list):
                for source_item in expr.from_:
                    item_sql, item_params = _format_single_from_source(source_item)
                    from_sql_parts.append(item_sql)
                    from_params.extend(item_params)
                current_sql += f" FROM {', '.join(from_sql_parts)}" # Append directly with leading space
                all_params.extend(from_params)
            else:
                from_expr_sql, from_expr_params = _format_single_from_source(expr.from_)
                current_sql += f" FROM {from_expr_sql}" # Append directly with leading space
                all_params.extend(from_expr_params)

        # WHERE clause
        if expr.where:
            where_sql, where_params = expr.where.to_sql()
            # The WhereClause.to_sql() returns "WHERE condition", so just append it
            current_sql += f" {where_sql}" # Append directly with leading space
            all_params.extend(where_params)

        # RETURNING clause
        if expr.returning:
            returning_sql, returning_params = self.format_returning_clause(expr.returning) # This returns "RETURNING col1, ..."
            current_sql += f" {returning_sql}" # Append directly with leading space
            all_params.extend(returning_params)

        return current_sql, tuple(all_params)

    def format_delete_statement(self, expr: "DeleteExpression") -> Tuple[str, tuple]:
        """Format DELETE statement.

        This method performs strict parameter validation for SQL standard compliance
        by default. To bypass # pragma: no cover validation for performance optimization, set strict_validation=False
        on the dialect instance.
        """
        # Perform strict parameter validation for SQL standard compliance
        # This validation may impact performance. If performance is critical,
        # dialect implementations can set strict_validation=False.
        if self.strict_validation:
            expr.validate(strict=True)

        all_params: List[Any] = []

        # Target tables (expr.tables is a list of TableExpression)
        table_sql_parts = []
        for table_expr in expr.tables:
            table_sql, table_params = table_expr.to_sql()
            table_sql_parts.append(table_sql)
            all_params.extend(table_params)

        # Join the table names for the DELETE statement
        tables_sql = ", ".join(table_sql_parts)
        current_sql = f"DELETE FROM {tables_sql}"

        # USING clause (for multi-table delete or joins)
        # Note: Different databases use different keywords (USING for PostgreSQL, FROM for MySQL)
        # The default is USING for SQL standard compliance
        if expr.using:
            using_sql_parts = []
            using_params: List[Any] = []

            # Helper to format a single USING source (copied from format_update_statement)
            def _format_single_using_source(source: Union[str, "bases.BaseExpression"]) -> Tuple[str, List[Any]]:
                if isinstance(source, str):
                    return self.format_identifier(source), []
                # Import here to avoid circular imports
                from ..expression.statements import QueryExpression
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql() # Get bare SQL
                    # Convert tuple to list to match return type
                    return f"({s_sql})", list(s_params) # Add parentheses
                if isinstance(source, bases.BaseExpression):
                    s_sql, s_params = source.to_sql()
                    # Convert tuple to list to match return type
                    return s_sql, list(s_params)
                # As a fallback, try to convert to string representation
                # This acts as a safety net in case validation didn't catch all cases
                return str(source), []

            if isinstance(expr.using, list):
                for source_item in expr.using:
                    item_sql, item_params = _format_single_using_source(source_item)
                    using_sql_parts.append(item_sql)
                    using_params.extend(item_params)
                current_sql += f" USING {', '.join(using_sql_parts)}"
                all_params.extend(using_params)
            else:
                using_expr_sql, using_expr_params = _format_single_using_source(expr.using)
                current_sql += f" USING {using_expr_sql}"
                all_params.extend(using_params)

        # WHERE clause
        if expr.where:
            where_sql, where_params = expr.where.to_sql()
            # The WhereClause.to_sql() returns "WHERE condition", so just append it
            current_sql += f" {where_sql}"
            all_params.extend(where_params)

        # RETURNING clause
        if expr.returning:
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            current_sql += f" {returning_sql}"
            all_params.extend(returning_params)

        return current_sql, tuple(all_params)

    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """
        Format CREATE TABLE statement with all supported features.

        This implementation handles all the features of the new CreateTableExpression:
        - Column definitions with data types and constraints
        - Table constraints
        - Temporary table flag
        - IF NOT EXISTS clause
        - Storage options, tablespace, partitioning
        - CREATE TABLE AS queries
        """
        all_params = []

        # Import here to avoid circular imports
        from ..expression.statements import ColumnConstraintType, TableConstraintType

        # Build the basic statement with flags
        parts = []
        temp_part = "TEMPORARY " if expr.temporary else ""
        not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""

        table_part = f"CREATE {temp_part}TABLE {not_exists_part}{self.format_identifier(expr.table_name)} "

        # Build column definitions
        column_parts = []
        for col_def in expr.columns:
            # Basic column: name type
            col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type}"

            # Add column constraints
            constraint_parts = []
            for constraint in col_def.constraints:
                if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                    constraint_parts.append("PRIMARY KEY")
                elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                    constraint_parts.append("NOT NULL")
                elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                    constraint_parts.append("UNIQUE")
                elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                    if constraint.default_value is None:
                        raise ValueError("DEFAULT constraint must have a default value specified.")
                    if isinstance(constraint.default_value, bases.BaseExpression):
                        default_sql, default_params = constraint.default_value.to_sql()
                        constraint_parts.append(f"DEFAULT {default_sql}")
                        all_params.extend(default_params)
                    else:
                        constraint_parts.append("DEFAULT ?")
                        all_params.append(constraint.default_value)
                elif constraint.constraint_type == ColumnConstraintType.CHECK:
                    if constraint.check_condition is None:
                        raise ValueError("CHECK constraint must have a check condition specified.")
                    check_sql, check_params = constraint.check_condition.to_sql()
                    constraint_parts.append(f"CHECK ({check_sql})")
                    all_params.extend(check_params)
                elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY:
                    if constraint.foreign_key_reference is None:
                        raise ValueError("FOREIGN KEY constraint must have a foreign key reference specified.")
                    referenced_table, referenced_columns = constraint.foreign_key_reference
                    ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
                    constraint_parts.append(f"REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})")

            if constraint_parts:
                col_sql += " " + " ".join(constraint_parts)

            if col_def.comment:
                col_sql += f" COMMENT '{col_def.comment}'"

            column_parts.append(col_sql)

        # Combine column definitions
        full_column_def = "(" + ", ".join(column_parts) + ")"

        # Add table constraints
        table_constraint_parts = []
        for t_const in expr.table_constraints:
            const_parts = []
            if t_const.name:
                const_parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")

            if t_const.constraint_type == TableConstraintType.PRIMARY_KEY:
                if not t_const.columns:
                    raise ValueError("PRIMARY KEY constraint must have at least one column specified.")
                cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
                const_parts.append(f"PRIMARY KEY ({cols_str})")
            elif t_const.constraint_type == TableConstraintType.UNIQUE:
                if not t_const.columns:
                    raise ValueError("UNIQUE constraint must have at least one column specified.")
                cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
                const_parts.append(f"UNIQUE ({cols_str})")
            elif t_const.constraint_type == TableConstraintType.CHECK:
                if t_const.check_condition is None:
                    raise ValueError("CHECK constraint must have a check condition specified.")
                check_sql, check_params = t_const.check_condition.to_sql()
                const_parts.append(f"CHECK ({check_sql})")
                all_params.extend(check_params)
            elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY:
                if not t_const.columns:
                    raise ValueError("FOREIGN KEY constraint must have at least one local column specified.")
                if not t_const.foreign_key_columns:
                    raise ValueError("FOREIGN KEY constraint must have at least one foreign key column specified.")
                if not t_const.foreign_key_table:
                    raise ValueError("FOREIGN KEY constraint must have a foreign key table specified.")
                cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
                ref_cols_str = ", ".join(self.format_identifier(col) for col in t_const.foreign_key_columns)
                const_parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {self.format_identifier(t_const.foreign_key_table)}({ref_cols_str})")

            if const_parts:
                table_constraint_parts.append(" ".join(const_parts))

        if table_constraint_parts:
            full_column_def += ", " + ", ".join(table_constraint_parts)

        parts.append(table_part + full_column_def)

        # Add storage options if present
        if expr.storage_options:
            storage_parts = []
            for key, value in expr.storage_options.items():
                if isinstance(value, str):
                    storage_parts.append(f"{key.upper()} = '{value}'")
                elif isinstance(value, (int, float)):
                    storage_parts.append(f"{key.upper()} = {value}")
                else:
                    storage_parts.append(f"{key.upper()} = ?")
                    all_params.append(value)
            if storage_parts:
                parts.append(" WITH (" + ", ".join(storage_parts) + ")")

        # Add tablespace if present
        if expr.tablespace:
            parts.append(f" TABLESPACE {self.format_identifier(expr.tablespace)}")

        # Add inherit clause if present (PostgreSQL specific)
        if expr.inherits:
            inherits_str = ", ".join(self.format_identifier(table) for table in expr.inherits)
            parts.append(f" INHERITS ({inherits_str})")

        # Add partition clause if present
        if expr.partition_by:
            partition_type, partition_cols = expr.partition_by
            cols_str = ", ".join(self.format_identifier(col) for col in partition_cols)
            parts.append(f" PARTITION BY {partition_type.upper()} ({cols_str})")

        # Add AS clause if present
        if expr.as_query:
            query_sql, query_params = expr.as_query.to_sql()
            parts.append(f" AS ({query_sql})")
            all_params.extend(query_params)

        return "".join(parts), tuple(all_params)

    def format_drop_table_statement(self, expr: "DropTableExpression") -> Tuple[str, tuple]:
        if_exists_part = "IF EXISTS " if expr.if_exists else ""
        sql = f"DROP TABLE {if_exists_part}{self.format_identifier(expr.table_name)}"
        return sql.strip(), ()

    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        """Format ALTER TABLE statement with comprehensive support for different actions."""
        all_params = []

        # Basic statement
        parts = [f"ALTER TABLE {self.format_identifier(expr.table_name)}"]

        # Process each action
        action_parts = []
        for action in expr.actions:
            action_part, action_params = action.to_sql()
            action_parts.append(action_part)
            all_params.extend(action_params)

        if action_parts:
            # Join actions with commas (some databases support multiple actions per ALTER TABLE)
            parts.append(" " + ", ".join(action_parts))

        return " ".join(parts), tuple(all_params)

    def format_case_expression(
        self,
        value_sql: Optional[str],
        value_params: Optional[tuple],
        conditions_results: List[Tuple[str, str, tuple, tuple]],
        else_result_sql: Optional[str],
        else_result_params: Optional[tuple],
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format CASE expression."""
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

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement."""
        # Basic statement
        replace_part = "OR REPLACE " if expr.replace else ""
        temporary_part = "TEMPORARY " if expr.temporary else ""
        sql_parts = [f"CREATE {replace_part}{temporary_part}VIEW {self.format_identifier(expr.view_name)}"]

        all_params = []

        # Add column aliases if specified
        if expr.column_aliases:
            aliases_str = ", ".join(self.format_identifier(alias) for alias in expr.column_aliases)
            sql_parts.append(f"({aliases_str})")

        # Add AS and the query
        query_sql, query_params = expr.query.to_sql()
        sql_parts.append(f" AS ({query_sql})")
        all_params.extend(query_params)

        # Handle view-specific options
        from ..expression.statements import ViewCheckOption
        if expr.options.check_option == ViewCheckOption.LOCAL:
            sql_parts.append(" WITH LOCAL CHECK OPTION")
        elif expr.options.check_option == ViewCheckOption.CASCADED:
            sql_parts.append(" WITH CASCADED CHECK OPTION")

        return " ".join(sql_parts), tuple(all_params)

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement."""
        if_exists_part = "IF EXISTS " if expr.if_exists else ""
        cascade_part = " CASCADE" if expr.cascade else ""
        sql = f"DROP VIEW {if_exists_part}{self.format_identifier(expr.view_name)}{cascade_part}"
        return sql.strip(), ()

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format TRUNCATE statement."""
        # Basic TRUNCATE statement
        sql = f"TRUNCATE TABLE {self.format_identifier(expr.table_name)}"

        # Add PostgreSQL-specific options if present
        if expr.restart_identity:
            sql += " RESTART IDENTITY"
        if expr.cascade:
            sql += " CASCADE"

        return sql, ()

    def format_group_by_having_clause(self, clause: "GroupByHavingClause") -> Tuple[str, tuple]:
        """Format combined GROUP BY and HAVING clauses."""
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

    def format_set_operation_expression(
        self,
        left: "bases.BaseExpression",
        right: "bases.BaseExpression",
        operation: str,
        alias: Optional[str],
        all_: bool,
        order_by_clause: Optional["OrderByClause"] = None,
        limit_offset_clause: Optional["LimitOffsetClause"] = None,
        for_update_clause: Optional["ForUpdateClause"] = None
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT) with optional clauses."""
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        all_str = " ALL" if all_ else ""

        # Build the base set operation SQL
        base_sql = f"{left_sql} {operation}{all_str} {right_sql}"

        # According to SQL standard, set operations can be followed directly by ORDER BY, LIMIT/OFFSET, etc.
        all_params = list(left_params + right_params)

        # Add parentheses around the base set operation if needed for additional clauses or alias
        if order_by_clause or limit_offset_clause or for_update_clause or alias:
            sql_parts = [f"({base_sql})"]
        else:
            sql_parts = [base_sql]

        # Add alias if present
        if alias:
            sql_parts.append(f"AS {self.format_identifier(alias)}")

        # Add ORDER BY clause if present
        if order_by_clause:
            order_by_sql, order_by_params = order_by_clause.to_sql()
            sql_parts.append(order_by_sql)
            all_params.extend(order_by_params)

        # Add LIMIT/OFFSET clause if present
        if limit_offset_clause:
            limit_offset_sql, limit_offset_params = limit_offset_clause.to_sql()
            sql_parts.append(limit_offset_sql)
            all_params.extend(limit_offset_params)

        # Add FOR UPDATE clause if present
        if for_update_clause:
            for_update_sql, for_update_params = for_update_clause.to_sql()
            sql_parts.append(for_update_sql)
            all_params.extend(for_update_params)

        sql = " ".join(sql_parts)
        return sql, tuple(all_params)

    def format_where_clause(self, clause: "WhereClause") -> Tuple[str, tuple]:
        """Format WHERE clause with condition."""
        condition_sql, condition_params = clause.condition.to_sql()
        return f"WHERE {condition_sql}", condition_params

    def format_order_by_clause(self, clause: "OrderByClause") -> Tuple[str, tuple]:
        """Format ORDER BY clause with expressions and directions."""
        all_params = []

        expr_parts = []
        for item in clause.expressions:
            if isinstance(item, tuple):
                # (expression, direction) format
                expr, direction = item
                expr_sql, expr_params = expr.to_sql()
                expr_parts.append(f"{expr_sql} {direction.upper()}")
                all_params.extend(expr_params)
            else:
                # Just expression (defaults to ASC)
                expr_sql, expr_params = item.to_sql()
                expr_parts.append(expr_sql)
                all_params.extend(expr_params)

        order_sql = f"ORDER BY {', '.join(expr_parts)}"
        return order_sql, tuple(all_params)

    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, tuple]:
        """Format a column definition for use in ADD COLUMN clauses."""
        all_params = []

        # Basic column definition: name data_type
        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type}"

        # Handle constraints
        from ..expression.statements import ColumnConstraintType

        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                col_sql += " PRIMARY KEY"
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                col_sql += " NOT NULL"
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                col_sql += " NULL"  # Explicitly allow NULL (though redundant in most cases)
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                col_sql += " UNIQUE"
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is None:
                    raise ValueError("DEFAULT constraint must have a default value specified.")
                if isinstance(constraint.default_value, bases.BaseExpression):
                    default_sql, default_params = constraint.default_value.to_sql()
                    col_sql += f" DEFAULT {default_sql}"
                    all_params.extend(default_params)
                else:
                    col_sql += f" DEFAULT {self.get_parameter_placeholder()}"
                    all_params.append(constraint.default_value)
            elif constraint.constraint_type == ColumnConstraintType.CHECK and constraint.check_condition is not None:
                check_sql, check_params = constraint.check_condition.to_sql()
                col_sql += f" CHECK ({check_sql})"
                all_params.extend(check_params)
            elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY:
                if constraint.foreign_key_reference is None:
                    raise ValueError("Foreign key constraint must have a foreign_key_reference specified.")
                referenced_table, referenced_columns = constraint.foreign_key_reference
                ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
                col_sql += f" REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})"

        # Add comment if present
        if col_def.comment:
            col_sql += f" COMMENT '{col_def.comment}'"

        return col_sql, tuple(all_params)