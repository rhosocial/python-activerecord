# src/rhosocial/activerecord/backend/dialect/base.py
"""
SQL dialect abstract base classes and common implementations.

This module defines the core dialect interfaces and provides default
implementations for standard SQL features.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Dict, TYPE_CHECKING
from .options import ExplainOptions # Import ExplainOptions

from .exceptions import ProtocolNotImplementedError, UnsupportedFeatureError
from ..expression import bases

if TYPE_CHECKING:
    from ..expression.statements import (
        QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
        MergeExpression, ExplainExpression, CreateTableExpression,
        DropTableExpression, AlterTableExpression, OnConflictClause, ForUpdateClause
    )
    from ..expression.advanced_functions import (
        WindowFrameSpecification, WindowSpecification, WindowDefinition,
        WindowClause, WindowFunctionCall
    )


class SQLDialectBase(ABC):
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
        pass

    @property
    def name(self) -> str:
        """
        Get dialect name for error messages.

        Returns:
            Dialect name (class name without 'Dialect' suffix)
        """
        return self.__class__.__name__.replace("Dialect", "")

    @abstractmethod
    def get_placeholder(self) -> str:
        """
        Get parameter placeholder format.

        Returns:
            Placeholder string ('?', '%s', '$', etc.)
        """
        pass

    @abstractmethod
    def get_parameter_placeholder(self, position: int) -> str:
        """
        Get parameter placeholder with position.

        Args:
            position: Parameter position (1-indexed)

        Returns:
            Positional placeholder string
        """
        pass
    # endregion Core & General

    # region Full Statement Formatting
    @abstractmethod
    def format_query_statement(self, expr: "QueryExpression") -> Tuple[str, tuple]:
        """Formats a complete SELECT statement from a QueryExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Formats a complete INSERT statement from an InsertExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_update_statement(self, expr: "UpdateExpression") -> Tuple[str, tuple]:
        """Formats a complete UPDATE statement from an UpdateExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_delete_statement(self, expr: "DeleteExpression") -> Tuple[str, tuple]:
        """Formats a complete DELETE statement from a DeleteExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
        """Formats a complete MERGE statement from a MergeExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
        """Formats an EXPLAIN statement from an ExplainExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Formats a CREATE TABLE statement from a CreateTableExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_drop_table_statement(self, expr: "DropTableExpression") -> Tuple[str, tuple]:
        """Formats a DROP TABLE statement from a DropTableExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        """Formats an ALTER TABLE statement from an AlterTableExpression object."""
        raise NotImplementedError
    # endregion Full Statement Formatting

    # region Clause Formatting
    @abstractmethod
    def format_with_clause(self, ctes_sql: List[str]) -> str:
        """
        Format complete WITH clause from list of CTE definitions.

        Args:
            ctes_sql: List of formatted CTE definition strings

        Returns:
            Complete WITH clause string
        """
        pass

    @abstractmethod
    def format_cte(
        self,
        name: str,
        query_sql: str,
        columns: Optional[List[str]] = None,
        recursive: bool = False,
        materialized: Optional[bool] = None
    ) -> str:
        """
        Format a single CTE definition.

        Args:
            name: CTE name
            query_sql: CTE query SQL
            columns: Optional column names
            recursive: Whether CTE is recursive
            materialized: Optional materialization hint

        Returns:
            Formatted CTE definition string
        """
        pass

    @abstractmethod
    def format_join_expression(
        self,
        base_join_sql: str,
        base_join_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format JOIN expression.

        Args:
            base_join_sql: Base JOIN SQL
            base_join_params: JOIN parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
        """
        Formats an ON CONFLICT clause for upsert operations.
        This should be implemented by dialects that support it, e.g., PostgreSQL's
        ON CONFLICT or MySQL's ON DUPLICATE KEY UPDATE.
        """
        raise NotImplementedError

    @abstractmethod
    def format_returning_clause(self, expressions: List["bases.BaseExpression"]) -> Tuple[str, tuple]:
        """Formats a RETURNING clause."""
        raise NotImplementedError

    @abstractmethod
    def format_for_update_clause(
        self,
        clause: "ForUpdateClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE clause with optional locking modifiers.

        Args:
            clause: ForUpdateClause object containing locking options.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        pass

    @abstractmethod
    def format_limit_offset(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[Optional[str], List[Any]]:
        """
        Format LIMIT and OFFSET clause.

        Args:
            limit: Optional row limit
            offset: Optional row offset

        Returns:
            Tuple of (SQL string or None, parameters list)
        """
        pass

    @abstractmethod
    def format_qualify_clause(
        self,
        qualify_sql: str,
        qualify_params: tuple
    ) -> Tuple[str, tuple]:
        """
        Formats a QUALIFY clause.

        Args:
            qualify_sql: SQL string for the QUALIFY condition.
            qualify_params: Parameters for the QUALIFY condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        pass

    @abstractmethod
    def format_match_clause(
        self,
        path_sql: List[str],
        path_params: tuple
    ) -> Tuple[str, tuple]:
        """
        Formats a MATCH clause.

        Args:
            path_sql: List of SQL strings for each part of the path.
            path_params: All parameters for the path.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        pass

    @abstractmethod
    def format_temporal_options(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a temporal table clause (e.g., FOR SYSTEM_TIME AS OF ...).

        Args:
            options: A dictionary of temporal options.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        pass

    @abstractmethod
    def format_window_frame_specification(
        self,
        spec: "WindowFrameSpecification"
    ) -> Tuple[str, tuple]:
        """
        Formats a window frame specification.

        Args:
            spec: WindowFrameSpecification object containing frame specification

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted specification.
        """
        pass

    @abstractmethod
    def format_window_specification(
        self,
        spec: "WindowSpecification"
    ) -> Tuple[str, tuple]:
        """
        Formats a window specification.

        Args:
            spec: WindowSpecification object containing the specification

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted specification.
        """
        pass

    @abstractmethod
    def format_window_definition(
        self,
        spec: "WindowDefinition"
    ) -> Tuple[str, tuple]:
        """
        Formats a named window definition.

        Args:
            spec: WindowDefinition object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted definition.
        """
        pass

    @abstractmethod
    def format_window_clause(
        self,
        clause: "WindowClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a complete WINDOW clause.

        Args:
            clause: WindowClause object containing the clause

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        pass

    @abstractmethod
    def format_window_function_call(
        self,
        call: "WindowFunctionCall"
    ) -> Tuple[str, tuple]:
        """
        Formats a window function call.

        Args:
            call: WindowFunctionCall object containing the call

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted call.
        """
        pass
    # endregion Clause Formatting

    # region Expression & Predicate Formatting
    @abstractmethod
    def format_identifier(self, identifier: str) -> str:
        """
        Format identifier (table name, column name) with appropriate quoting.

        Args:
            identifier: Raw identifier string

        Returns:
            Quoted identifier
        """
        pass

    @abstractmethod
    def format_column(
        self,
        name: str,
        table: Optional[str] = None,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Format column reference.

        Args:
            name: Column name
            table: Optional table name/alias
            alias: Optional column alias

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_table(
        self,
        table_name: str,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Format table reference.

        Args:
            table_name: Table name
            alias: Optional table alias

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_alias(
        self,
        expression_sql: str,
        alias: str,
        expression_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format alias.

        Args:
            expression_sql: Expression SQL
            alias: Alias name
            expression_params: Expression parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_subquery(
        self,
        subquery_sql: str,
        subquery_params: tuple,
        alias: str
    ) -> Tuple[str, Tuple]:
        """
        Format subquery.

        Args:
            subquery_sql: Subquery SQL
            subquery_params: Subquery parameters
            alias: Subquery alias

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
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
        Format function call.

        Args:
            func_name: Function name
            args_sql: List of argument SQL strings
            args_params: List of argument parameter tuples
            is_distinct: Whether to use DISTINCT
            alias: Optional result alias
            filter_sql: Optional SQL for FILTER (WHERE ...) clause
            filter_params: Optional parameters for FILTER clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
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
        Format an ordered-set aggregate function call (WITHIN GROUP (ORDER BY ...)).

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
        pass

    @abstractmethod
    def format_case_expression(
        self,
        value_sql: Optional[str],
        value_params: Optional[tuple],
        conditions_results: List[Tuple[str, str, tuple, tuple]],
        else_result_sql: Optional[str],
        else_result_params: Optional[tuple]
    ) -> Tuple[str, Tuple]:
        """
        Format CASE expression.

        Args:
            value_sql: Optional value expression SQL (for simple CASE)
            value_params: Value expression parameters
            conditions_results: List of (condition_sql, result_sql, condition_params, result_params)
            else_result_sql: Optional ELSE result SQL
            else_result_params: ELSE result parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_cast_expression(
        self,
        expr_sql: str,
        target_type: str,
        expr_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format CAST expression.

        Args:
            expr_sql: Expression SQL
            target_type: Target type name
            expr_params: Expression parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_comparison_predicate(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format comparison predicate.

        Args:
            op: Comparison operator
            left_sql: Left operand SQL
            right_sql: Right operand SQL
            left_params: Left operand parameters
            right_params: Right operand parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_logical_predicate(
        self,
        op: str,
        *predicates_sql_and_params: Tuple[str, tuple]
    ) -> Tuple[str, Tuple]:
        """
        Format logical predicate (AND, OR, NOT).

        Args:
            op: Logical operator
            predicates_sql_and_params: Variable number of (SQL, params) tuples

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_in_predicate(
        self,
        expr_sql: str,
        values_sql: str,
        expr_params: tuple,
        values_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format IN predicate.

        Args:
            expr_sql: Expression SQL
            values_sql: Values list SQL
            expr_params: Expression parameters
            values_params: Values parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_between_predicate(
        self,
        expr_sql: str,
        low_sql: str,
        high_sql: str,
        expr_params: tuple,
        low_params: tuple,
        high_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format BETWEEN predicate.

        Args:
            expr_sql: Expression SQL
            low_sql: Lower bound SQL
            high_sql: Upper bound SQL
            expr_params: Expression parameters
            low_params: Lower bound parameters
            high_params: Upper bound parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_is_null_predicate(
        self,
        expr_sql: str,
        is_not: bool,
        expr_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format IS NULL/IS NOT NULL predicate.

        Args:
            expr_sql: Expression SQL
            is_not: Whether to use IS NOT NULL
            expr_params: Expression parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_like_predicate(
        self,
        op: str,
        expr_sql: str,
        pattern_sql: str,
        expr_params: tuple,
        pattern_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format LIKE predicate.

        Args:
            op: LIKE operator (LIKE, NOT LIKE, ILIKE, etc.)
            expr_sql: Expression SQL
            pattern_sql: Pattern SQL
            expr_params: Expression parameters
            pattern_params: Pattern parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_binary_operator(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format binary operator.

        Args:
            op: Binary operator
            left_sql: Left operand SQL
            right_sql: Right operand SQL
            left_params: Left operand parameters
            right_params: Right operand parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_unary_operator(
        self,
        op: str,
        operand_sql: str,
        pos: str,
        operand_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format unary operator.

        Args:
            op: Unary operator
            operand_sql: Operand SQL
            pos: Position ('before' or 'after')
            operand_params: Operand parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_binary_arithmetic_expression(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format binary arithmetic expression.

        Args:
            op: Arithmetic operator (+, -, *, /, etc.)
            left_sql: Left operand SQL
            right_sql: Right operand SQL
            left_params: Left operand parameters
            right_params: Right operand parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_values_expression(
        self,
        values: List[Tuple[Any, ...]],
        alias: str,
        column_names: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format VALUES expression as data source.

        Args:
            values: List of value tuples
            alias: VALUES alias
            column_names: Column names for VALUES

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_table_function_expression(
        self,
        func_name: str,
        args_sql: List[str],
        args_params: Tuple[Any, ...],
        alias: str,
        column_names: Optional[List[str]]
    ) -> Tuple[str, Tuple]:
        """
        Format table-valued function expression.

        Args:
            func_name: Function name
            args_sql: Argument SQL strings
            args_params: Argument parameters
            alias: Function result alias
            column_names: Optional column names

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_lateral_expression(
        self,
        expr_sql: str,
        expr_params: Tuple[Any, ...],
        alias: str,
        join_type: str
    ) -> Tuple[str, Tuple]:
        """
        Format LATERAL expression.

        Args:
            expr_sql: Inner expression SQL
            expr_params: Expression parameters
            alias: LATERAL alias
            join_type: JOIN type (CROSS, LEFT, etc.)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
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
        pass
    # endregion Expression & Predicate Formatting

    # region Utilities
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


class BaseDialect(SQLDialectBase):
    """
    Base dialect with standard SQL implementations.

    This class provides default implementations for most SQL features that
    work across different databases. Subclasses can override specific methods
    for dialect-specific behavior.
    """

    def get_parameter_placeholder(self, position: int) -> str:
        """
        Get parameter placeholder with position.

        For dialects using positional placeholders, position is ignored.

        Args:
            position: Parameter position (1-indexed)

        Returns:
            Placeholder string
        """
        return self.get_placeholder()

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
        from .protocols import FilterClauseSupport  # Local import to avoid circular dependency

        distinct = "DISTINCT " if is_distinct else ""
        args_sql_str = ", ".join(args_sql)
        func_call_sql = f"{func_name.upper()}({distinct}{args_sql_str})"

        all_params: List[Any] = []
        for param_tuple in args_params:
            all_params.extend(param_tuple)

        # Handle FILTER clause
        if filter_sql:
            if isinstance(self, FilterClauseSupport) and self.supports_filter_clause():
                filter_clause_sql, filter_clause_params = self.format_filter_clause(filter_sql, filter_params if filter_params is not None else ())
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

    def format_comparison_predicate(
        self,
        op: str,
        left_sql: str,
        right_sql: str,
        left_params: tuple,
        right_params: tuple
    ) -> Tuple[str, Tuple]:
        sql = f"{left_sql} {op} {right_sql}"
        return sql, left_params + right_params

    def format_logical_predicate(
        self,
        op: str,
        *predicates_sql_and_params: Tuple[str, tuple]
    ) -> Tuple[str, Tuple]:
        """Format logical predicate (AND, OR, NOT)."""
        if op.upper() == "NOT" and len(predicates_sql_and_params) == 1:
            sql, params = predicates_sql_and_params[0]
            return f"NOT ({sql})", params # KEEP () here for NOT
        else:
            parts = []
            all_params: List[Any] = []
            for sql, params in predicates_sql_and_params:
                parts.append(sql) # Removed () around sql
                all_params.extend(params)
            sql = f" {op} ".join(parts)
            return sql, tuple(all_params) # Removed outer () here

    def format_in_predicate(
        self,
        expr_sql: str,
        values_sql: str,
        expr_params: tuple,
        values_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format IN predicate."""
        sql = f"{expr_sql} IN {values_sql}"
        return sql, expr_params + values_params

    def format_between_predicate(
        self,
        expr_sql: str,
        low_sql: str,
        high_sql: str,
        expr_params: tuple,
        low_params: tuple,
        high_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format BETWEEN predicate."""
        sql = f"{expr_sql} BETWEEN {low_sql} AND {high_sql}"
        return sql, expr_params + low_params + high_params

    def format_is_null_predicate(
        self,
        expr_sql: str,
        is_not: bool,
        expr_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format IS NULL predicate."""
        not_str = " NOT" if is_not else ""
        sql = f"{expr_sql} IS{not_str} NULL"
        return sql, expr_params

    def format_like_predicate(
        self,
        op: str,
        expr_sql: str,
        pattern_sql: str,
        expr_params: tuple,
        pattern_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format LIKE predicate."""
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

    def format_case_expression(
        self,
        value_sql: Optional[str],
        value_params: Optional[tuple],
        conditions_results: List[Tuple[str, str, tuple, tuple]],
        else_result_sql: Optional[str],
        else_result_params: Optional[tuple]
    ) -> Tuple[str, Tuple]:
        """Format CASE expression."""
        parts = ["CASE"]
        all_params: List[Any] = []

        if value_sql:
            parts.append(value_sql)
            if value_params:
                all_params.extend(value_params)

        for condition_sql, result_sql, condition_params, result_params in conditions_results:
            parts.append(f"WHEN {condition_sql} THEN {result_sql}")
            all_params.extend(condition_params)
            all_params.extend(result_params)

        if else_result_sql:
            parts.append(f"ELSE {else_result_sql}")
            if else_result_params:
                all_params.extend(else_result_params)

        parts.append("END")
        sql = " ".join(parts)
        return sql, tuple(all_params)

    def format_cast_expression(
        self,
        expr_sql: str,
        target_type: str,
        expr_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format CAST expression."""
        sql = f"CAST({expr_sql} AS {target_type})"
        return sql, expr_params

    def format_subquery(
        self,
        subquery_sql: str,
        subquery_params: tuple,
        alias: str
    ) -> Tuple[str, Tuple]:
        """Format subquery."""
        return f"{subquery_sql} AS {self.format_identifier(alias)}", subquery_params

    def format_limit_offset(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[Optional[str], List[Any]]:
        """Format LIMIT/OFFSET clause."""
        if limit is not None and offset is not None:
            return "LIMIT ? OFFSET ?", [limit, offset]
        elif limit is not None:
            return "LIMIT ?", [limit]
        elif offset is not None:
            return "OFFSET ?", [offset]
        else:
            return None, []

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

    def format_join_expression(
        self,
        base_join_sql: str,
        base_join_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format JOIN expression."""
        return base_join_sql, base_join_params

    def format_alias(
        self,
        expression_sql: str,
        alias: str,
        expression_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format alias."""
        sql = f"{expression_sql} AS {self.format_identifier(alias)}"
        return sql, expression_params

    def format_cte(
        self,
        name: str,
        query_sql: str,
        columns: Optional[List[str]] = None,
        recursive: bool = False,
        materialized: Optional[bool] = None
    ) -> str:
        """Format a single CTE definition."""
        recursive_str = "RECURSIVE " if recursive else ""
        materialized_hint = ""
        if materialized is not None:
            materialized_hint = "MATERIALIZED " if materialized else "NOT MATERIALIZED "

        name_part = self.format_identifier(name)
        columns_part = f" ({', '.join(self.format_identifier(c) for c in columns)})" if columns else ""
        return f"{recursive_str}{name_part}{columns_part} AS {materialized_hint}({query_sql})"

    def format_with_clause(self, ctes_sql: List[str]) -> str:
        """Format complete WITH clause from list of CTE definitions."""
        if not ctes_sql:
            return ""
        return f"WITH {', '.join(ctes_sql)}"

    def format_values_expression(
        self,
        values: List[Tuple[Any, ...]],
        alias: str,
        column_names: List[str]
    ) -> Tuple[str, Tuple]:
        """Format VALUES expression as data source."""
        all_params: List[Any] = []
        rows_sql = []
        for row in values:
            placeholders = ", ".join([self.get_placeholder()] * len(row))
            rows_sql.append(f"({placeholders})")
            all_params.extend(row)

        values_sql = ", ".join(rows_sql)
        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"

        sql = f"(VALUES {values_sql}) AS {self.format_identifier(alias)}{cols_sql}"
        return sql, tuple(all_params)

    def format_table_function_expression(
        self,
        func_name: str,
        args_sql: List[str],
        args_params: Tuple[Any, ...],
        alias: str,
        column_names: Optional[List[str]]
    ) -> Tuple[str, Tuple]:
        """Format table-valued function expression."""
        args_str = ", ".join(args_sql)

        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"

        sql = f"{func_name.upper()}({args_str}) AS {self.format_identifier(alias)}{cols_sql}"
        return sql, args_params

    def format_lateral_expression(
        self,
        expr_sql: str,
        expr_params: Tuple[Any, ...],
        alias: str,
        join_type: str
    ) -> Tuple[str, Tuple]:
        """Format LATERAL expression."""
        sql = f"{join_type.upper()} JOIN LATERAL {expr_sql} AS {self.format_identifier(alias)}"
        return sql, expr_params

    def format_window_frame_specification(
        self,
        spec: "WindowFrameSpecification"
    ) -> Tuple[str, tuple]:
        """Default implementation for window frame specification."""
        parts = [spec.frame_type]
        if spec.end_frame:
            parts.append(f"BETWEEN {spec.start_frame} AND {spec.end_frame}")
        else:
            parts.append(spec.start_frame)
        return " ".join(parts), ()

    def format_window_specification(
        self,
        spec: "WindowSpecification"
    ) -> Tuple[str, tuple]:
        """Default implementation for window specification."""
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
            frame_sql, frame_params = self.format_window_frame_specification(spec.frame)
            parts.append(frame_sql)
            all_params.extend(frame_params)

        return " ".join(parts) if parts else "", tuple(all_params)

    def format_window_definition(
        self,
        spec: "WindowDefinition"
    ) -> Tuple[str, tuple]:
        """Default implementation for window definition."""
        spec_sql, spec_params = self.format_window_specification(spec.specification)
        window_def = f"{self.format_identifier(spec.name)} AS ({spec_sql})"
        return window_def, spec_params

    def format_window_clause(
        self,
        clause: "WindowClause"
    ) -> Tuple[str, tuple]:
        """Default implementation for WINDOW clause."""
        all_params = []
        def_parts = []

        for defn in clause.definitions:
            def_sql, def_params = self.format_window_definition(defn)
            def_parts.append(def_sql)
            all_params.extend(def_params)

        if def_parts:
            return f"WINDOW {', '.join(def_parts)}", tuple(all_params)
        else:
            return "", tuple(all_params)

    def format_window_function_call(
        self,
        call: "WindowFunctionCall"
    ) -> Tuple[str, tuple]:
        """Default implementation for window function call."""
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
                arg_parts.append(self.get_placeholder())
                all_params.append(arg)

        func_sql = f"{call.function_name}({', '.join(arg_parts)})"

        if call.window_spec is None:
            # No window specification
            sql = func_sql
        else:
            if isinstance(call.window_spec, str):
                # Reference to named window
                window_part = self.format_identifier(call.window_spec)
            elif hasattr(call.window_spec, 'to_sql'):
                # Inline window specification
                window_spec_sql, window_spec_params = self.format_window_specification(call.window_spec)
                window_part = f"({window_spec_sql})" if window_spec_sql else "()"
                all_params.extend(window_spec_params)
            else:
                window_part = "()"

            sql = f"{func_sql} OVER {window_part}"

        if call.alias:
            sql = f"{sql} AS {self.format_identifier(call.alias)}"

        return sql, tuple(all_params)

    def format_query_statement(self, expr: "QueryExpression") -> Tuple[str, tuple]:
        """Default implementation for format_query_statement."""
        all_params = []

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

        # FROM clause (optional)
        from_sql = ""
        if expr.from_:
            from_sql_parts = []
            from_params = []

            def _format_from_source(source):
                if isinstance(source, str):
                    return self.format_identifier(source), []
                elif isinstance(source, bases.BaseExpression):
                    return source.to_sql()
                else:
                    raise TypeError(f"Unsupported FROM source type: {type(source)}")

            if isinstance(expr.from_, list):
                for source_item in expr.from_:
                    item_sql, item_params = _format_from_source(source_item)
                    from_sql_parts.append(item_sql)
                    from_params.extend(item_params)
                from_sql = f" FROM {', '.join(from_sql_parts)}"
            else:
                from_expr_sql, from_expr_params = _format_from_source(expr.from_)
                from_sql = f" FROM {from_expr_sql}"
            all_params.extend(from_params)

        # WHERE clause (optional)
        where_sql = ""
        if expr.where:
            where_expr_sql, where_expr_params = expr.where.to_sql()
            where_sql = f" WHERE {where_expr_sql}"
            all_params.extend(where_expr_params)

        # GROUP BY clause (optional)
        group_by_sql = ""
        if expr.group_by:
            group_by_parts = []
            for e in expr.group_by:
                expr_sql, expr_params = e.to_sql()
                group_by_parts.append(expr_sql)
                all_params.extend(expr_params)
            group_by_sql = f" GROUP BY {', '.join(group_by_parts)}"

        # HAVING clause (optional, requires GROUP BY)
        having_sql = ""
        if expr.having:
            having_expr_sql, having_expr_params = expr.having.to_sql()
            having_sql = f" HAVING {having_expr_sql}"
            all_params.extend(having_expr_params)

        # QUALIFY clause (optional)
        qualify_sql = ""
        if expr.qualify:
            qualify_expr_sql, qualify_expr_params = expr.qualify.to_sql()
            qualify_sql = f" QUALIFY {qualify_expr_sql}"
            all_params.extend(qualify_expr_params)

        # ORDER BY clause (optional)
        order_by_sql = ""
        if expr.order_by:
            order_by_parts = []
            for item in expr.order_by:
                if isinstance(item, tuple):
                    e, direction = item
                    expr_sql, expr_params = e.to_sql()
                    order_by_parts.append(f"{expr_sql} {direction.upper()}")
                    all_params.extend(expr_params)
                else:
                    expr_sql, expr_params = item.to_sql()
                    order_by_parts.append(expr_sql)
                    all_params.extend(expr_params)
            order_by_sql = f" ORDER BY {', '.join(order_by_parts)}"

        # LIMIT and OFFSET clauses (optional)
        limit_offset_sql = ""
        if expr.limit is not None or expr.offset is not None:
            # This will use the existing format_limit_offset method
            lo_sql, lo_params = self.format_limit_offset(expr.limit, expr.offset)
            if lo_sql:
                limit_offset_sql = f" {lo_sql}"
                all_params.extend(lo_params)

        # Combine all parts
        sql_parts = [
            select_sql,
            from_sql,
            where_sql,
            group_by_sql,
            having_sql,
            qualify_sql,
            order_by_sql,
            limit_offset_sql
        ]

        # Add FOR UPDATE clause at the end (if present)
        for_update_sql = ""
        if expr.for_update:
            for_update_sql_str, for_update_params = expr.for_update.to_sql()
            if for_update_sql_str:
                for_update_sql = f" {for_update_sql_str}"
                all_params.extend(for_update_params)

        # Build final SQL
        sql = "".join(part for part in sql_parts if part)  # Remove empty parts
        if for_update_sql:
            sql += for_update_sql

        return sql, tuple(all_params)

    def format_explain(
        self,
        sql: str,
        options: Optional['ExplainOptions'] = None
    ) -> str:
        """Format EXPLAIN statement."""
        return f"EXPLAIN {sql}"
