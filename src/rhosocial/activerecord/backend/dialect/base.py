# src/rhosocial/activerecord/backend/dialect/base.py
"""
SQL dialect abstract base classes and common implementations.

This module defines the core dialect interfaces and provides default
implementations for standard SQL features.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Dict, Union, TYPE_CHECKING

from .exceptions import ProtocolNotImplementedError, UnsupportedFeatureError
from ..expression import bases, JoinExpression, ColumnDefinition, AlterTableAction, MatchClause

if TYPE_CHECKING:
    from ..expression.statements import (
        QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
        MergeExpression, ExplainExpression, CreateTableExpression,
        DropTableExpression, AlterTableExpression, OnConflictClause, ForUpdateClause,
        ExplainOptions,  # Updated import to reference ExplainOptions from expression module
        ReturningClause, ColumnConstraintType, TableConstraintType,  # Added ReturningClause import
        CreateViewExpression, DropViewExpression, ViewCheckOption, ViewOptions  # View-related imports
    )
    from ..expression.query_parts import (
        WhereClause, GroupByHavingClause, LimitOffsetClause, OrderByClause, QualifyClause
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

    @abstractmethod
    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Formats a CREATE VIEW statement from a CreateViewExpression object."""
        raise NotImplementedError

    @abstractmethod
    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Formats a DROP VIEW statement from a DropViewExpression object."""
        raise NotImplementedError
    # endregion Full Statement Formatting

    # region Clause Formatting
    @abstractmethod
    def format_cte(
        self,
        name: str,
        query_sql: str,
        columns: Optional[List[str]] = None,
        recursive: bool = False,
        materialized: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a single CTE definition.

        Args:
            name: CTE name
            query_sql: CTE query SQL
            columns: Optional column names
            recursive: Whether CTE is recursive
            materialized: Optional materialization hint
            dialect_options: Dialect-specific options

        Returns:
            Formatted CTE definition string
        """
        pass

    @abstractmethod
    def format_with_query(
        self,
        cte_sql_parts: List[str],
        main_query_sql: str,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a complete query with WITH clause.

        Args:
            cte_sql_parts: List of formatted CTE definition strings
            main_query_sql: Main query SQL
            dialect_options: Dialect-specific options

        Returns:
            Complete query with WITH clause string
        """
        pass

    @abstractmethod
    def format_join_expression(
        self,
        join_expr: "JoinExpression"
    ) -> Tuple[str, Tuple]:
        """
        Format JOIN expression.

        Args:
            join_expr: JoinExpression object containing the join specifications

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_set_operation_expression(
        self,
        left: "bases.BaseExpression",
        right: "bases.BaseExpression",
        operation: str,
        alias: str,
        all: bool
    ) -> Tuple[str, Tuple]:
        """
        Format set operation expression (UNION, INTERSECT, EXCEPT).

        Args:
            left: Left query expression
            right: Right query expression
            operation: Set operation type ('UNION', 'INTERSECT', 'EXCEPT')
            alias: Alias for the result
            all: Whether to use ALL modifier

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
    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, tuple]:
        """
        Formats a RETURNING clause for INSERT, UPDATE, or DELETE statements.

        Args:
            clause: ReturningClause object containing the expressions to return

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
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
    def format_where_clause(self, clause: "WhereClause") -> Tuple[str, tuple]:
        """
        Formats a WHERE clause.

        Args:
            clause: WhereClause object containing the filtering condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        raise NotImplementedError

    @abstractmethod
    def format_group_by_having_clause(self, clause: "GroupByHavingClause") -> Tuple[str, tuple]:
        """
        Formats combined GROUP BY and HAVING clauses.

        Args:
            clause: GroupByHavingClause object containing the grouping expressions and optional HAVING condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clauses.
        """
        raise NotImplementedError

    @abstractmethod
    def format_order_by_clause(self, clause: "OrderByClause") -> Tuple[str, tuple]:
        """
        Formats an ORDER BY clause.

        Args:
            clause: OrderByClause object containing the ordering specifications.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        raise NotImplementedError

    @abstractmethod
    def format_limit_offset_clause(self, clause: "LimitOffsetClause") -> Tuple[str, tuple]:
        """
        Formats LIMIT and OFFSET clauses.

        Args:
            clause: LimitOffsetClause object containing the limit and offset specifications.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clauses.
        """
        raise NotImplementedError

    @abstractmethod
    def format_qualify_clause(
        self,
        clause: "QualifyClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a QUALIFY clause.

        Args:
            clause: QualifyClause object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        pass

    @abstractmethod
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
        else_result_params: Optional[tuple],
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Format CASE expression.

        Args:
            value_sql: Optional value expression SQL (for simple CASE)
            value_params: Value expression parameters
            conditions_results: List of (condition_sql, result_sql, condition_params, result_params)
            else_result_sql: Optional ELSE result SQL
            else_result_params: ELSE result parameters
            alias: Optional alias for the CASE expression

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
    def format_in_predicate_with_literal_values(
        self,
        expr_sql: str,
        literal_values: tuple,
        expr_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format IN predicate with literal values (e.g., IN (?, ?, ?)).

        Args:
            expr_sql: Expression SQL
            literal_values: Tuple of literal values
            expr_params: Expression parameters

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_any_expression(
        self,
        expr: "bases.BaseExpression",
        op: str,
        array_expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """
        Format ANY expression.

        Args:
            expr: Left side expression
            op: Comparison operator
            array_expr: Array or subquery expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_all_expression(
        self,
        expr: "bases.BaseExpression",
        op: str,
        array_expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """
        Format ALL expression.

        Args:
            expr: Left side expression
            op: Comparison operator
            array_expr: Array or subquery expression

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
    def format_exists_expression(
        self,
        subquery: "core.Subquery",
        is_not: bool
    ) -> Tuple[str, Tuple]:
        """
        Format EXISTS predicate.

        Args:
            subquery: Subquery expression
            is_not: Whether to use NOT EXISTS

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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def format_json_expression(
        self,
        column: Union["bases.BaseExpression", str],
        path: str,
        operation: str
    ) -> Tuple[str, Tuple]:
        """
        Format JSON expression.

        Args:
            column: Column expression or identifier
            path: JSON path
            operation: JSON operation (e.g., '->', '->>')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass

    @abstractmethod
    def format_array_expression(
        self,
        operation: str,
        elements: Optional[List["bases.BaseExpression"]],
        base_expr: Optional["bases.BaseExpression"],
        index_expr: Optional["bases.BaseExpression"]
    ) -> Tuple[str, Tuple]:
        """
        Format array expression.

        Args:
            operation: Array operation type ('CONSTRUCTOR', 'ACCESS', etc.)
            elements: List of elements for array constructor
            base_expr: Base expression for array access
            index_expr: Index expression for array access

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

    def get_placeholder(self) -> str:
        """
        Get parameter placeholder format.

        Returns:
            Placeholder string ('?')
        """
        return "?"

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

    # region Protocol Support Checks
    def supports_window_functions(self) -> bool: return False
    def supports_window_frame_clause(self) -> bool: return False
    def supports_basic_cte(self) -> bool: return False
    def supports_recursive_cte(self) -> bool: return False
    def supports_materialized_cte(self) -> bool: return False
    def supports_rollup(self) -> bool: return False
    def supports_cube(self) -> bool: return False
    def supports_grouping_sets(self) -> bool: return False
    def supports_returning_clause(self) -> bool: return False
    def supports_upsert(self) -> bool: return False
    def get_upsert_syntax_type(self) -> str: return "NOT SUPPORTED"
    def supports_lateral_join(self) -> bool: return False
    def supports_array_type(self) -> bool: return False
    def supports_array_constructor(self) -> bool: return False
    def supports_array_access(self) -> bool: return False
    def supports_json_type(self) -> bool: return False
    def get_json_access_operator(self) -> str: return "NOT SUPPORTED"
    def supports_json_table(self) -> bool: return False
    def supports_explain_analyze(self) -> bool: return False
    def supports_explain_format(self, format_type: str) -> bool: return False
    def supports_filter_clause(self) -> bool: return False
    def supports_ordered_set_aggregation(self) -> bool: return False
    def supports_merge_statement(self) -> bool: return False
    def supports_temporal_tables(self) -> bool: return False
    def supports_qualify_clause(self) -> bool: return False
    def supports_for_update_skip_locked(self) -> bool: return False
    def supports_graph_match(self) -> bool: return False
    # endregion

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

    def format_in_predicate_with_literal_values(
        self,
        expr_sql: str,
        literal_values: tuple,
        expr_params: tuple
    ) -> Tuple[str, Tuple]:
        """Format IN predicate with literal values."""
        if not literal_values:  # Handle empty list case for IN ()
            values_sql = "()"
            values_params = ()
        else:
            placeholders = ", ".join([self.get_placeholder()] * len(literal_values))
            values_sql = f"({placeholders})"
            values_params = tuple(literal_values)  # Convert to tuple to ensure correct type
        sql = f"{expr_sql} IN {values_sql}"
        return sql, expr_params + values_params

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
            array_sql = self.get_placeholder()
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
            array_sql = self.get_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        sql = f"({expr_sql} {op} ALL{array_sql})"
        return sql, tuple(list(expr_params) + list(array_params))

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
        materialized: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a single CTE definition."""
        recursive_str = "RECURSIVE " if recursive else ""
        materialized_hint = ""
        if materialized is not None:
            materialized_hint = "MATERIALIZED " if materialized else "NOT MATERIALIZED "

        name_part = self.format_identifier(name)
        columns_part = f" ({', '.join(self.format_identifier(c) for c in columns)})" if columns else ""
        return f"{recursive_str}{name_part}{columns_part} AS {materialized_hint}({query_sql})"


    def format_with_query(
        self,
        cte_sql_parts: List[str],
        main_query_sql: str,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a complete query with WITH clause."""
        if not cte_sql_parts:
            return main_query_sql
        with_clause = self._format_with_clause(cte_sql_parts)
        return f"{with_clause} {main_query_sql}"

    def _format_with_clause(self, ctes_sql: List[str]) -> str:
        """Helper to format complete WITH clause from list of CTE definitions."""
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

    def supports_offset_without_limit(self) -> bool:
        """Check if the dialect supports OFFSET clause without LIMIT clause."""
        # By default, assume the dialect does not support OFFSET without LIMIT
        return False

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
                parts.append(f"LIMIT {self.get_placeholder()}")
                all_params.append(clause.limit)

        if clause.offset is not None:
            # Handle offset value - might be int or expression
            if hasattr(clause.offset, 'to_sql'):
                offset_sql, offset_params = clause.offset.to_sql()
                parts.append(f"OFFSET {offset_sql}")
                all_params.extend(offset_params)
            else:
                parts.append(f"OFFSET {self.get_placeholder()}")
                all_params.append(clause.offset)

        return " ".join(parts), tuple(all_params)



    # region Full Statement Formatting
    def format_query_statement(self, expr: "QueryExpression") -> Tuple[str, tuple]:
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
                from_expr_sql = self.format_identifier(expr.from_)
                from_expr_params = []
            else: # Assume it's a BaseExpression
                from_expr_sql, from_expr_params = expr.from_.to_sql()
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
                    return f"({s_sql})", s_params # Add parentheses
                if isinstance(source, bases.BaseExpression): # Explicitly check for BaseExpression
                    return source.to_sql()
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
        all_params: List[Any] = []

        # Target table (expr.table is a TableExpression)
        table_sql, table_params = expr.table.to_sql()
        all_params.extend(table_params)

        current_sql = f"DELETE FROM {table_sql}"

        # FROM clause (for multi-table delete or joins)
        if expr.from_:
            from_sql_parts = []
            from_params: List[Any] = []

            # Helper to format a single FROM source (copied from format_update_statement)
            def _format_single_from_source(source: Union[str, "bases.BaseExpression"]) -> Tuple[str, List[Any]]:
                if isinstance(source, str):
                    return self.format_identifier(source), []
                # Import here to avoid circular imports
                from ..expression.statements import QueryExpression
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql() # Get bare SQL
                    return f"({s_sql})", s_params # Add parentheses
                if isinstance(source, bases.BaseExpression):
                    return source.to_sql()
                raise TypeError(f"Unsupported FROM source type: {type(source)}")

            if isinstance(expr.from_, list):
                for source_item in expr.from_:
                    item_sql, item_params = _format_single_from_source(source_item)
                    from_sql_parts.append(item_sql)
                    from_params.extend(item_params)
                current_sql += f" FROM {', '.join(from_sql_parts)}"
                all_params.extend(from_params)
            else:
                from_expr_sql, from_expr_params = _format_single_from_source(expr.from_)
                current_sql += f" FROM {from_expr_sql}"
                all_params.extend(from_params)

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

    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
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

    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
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
            parts.append("SETTINGS")
        if options.wal:
            parts.append("WAL")

        return f"{' '.join(parts)} {statement_sql}", statement_params

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
                elif constraint.constraint_type == ColumnConstraintType.DEFAULT and constraint.default_value is not None:
                    if isinstance(constraint.default_value, bases.BaseExpression):
                        default_sql, default_params = constraint.default_value.to_sql()
                        constraint_parts.append(f"DEFAULT {default_sql}")
                        all_params.extend(default_params)
                    else:
                        constraint_parts.append("DEFAULT ?")
                        all_params.append(constraint.default_value)
                elif constraint.constraint_type == ColumnConstraintType.CHECK and constraint.check_condition is not None:
                    check_sql, check_params = constraint.check_condition.to_sql()
                    constraint_parts.append(f"CHECK ({check_sql})")
                    all_params.extend(check_params)
                elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY and constraint.foreign_key_reference is not None:
                    referenced_table, referenced_columns = constraint.foreign_key_reference
                    ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
                    constraint_parts.append(f"REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})")

            if constraint_parts:
                col_sql += " " + " ".join(constraint_parts)

            # Handle the nullable field separately from constraints
            if col_def.nullable is False:
                col_sql += " NOT NULL"  # Explicitly not null
            elif col_def.nullable is True:
                col_sql += " NULL"     # Explicitly allow null (though this is usually redundant)

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

            if t_const.constraint_type == TableConstraintType.PRIMARY_KEY and t_const.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
                const_parts.append(f"PRIMARY KEY ({cols_str})")
            elif t_const.constraint_type == TableConstraintType.UNIQUE and t_const.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
                const_parts.append(f"UNIQUE ({cols_str})")
            elif t_const.constraint_type == TableConstraintType.CHECK and t_const.check_condition is not None:
                check_sql, check_params = t_const.check_condition.to_sql()
                const_parts.append(f"CHECK ({check_sql})")
                all_params.extend(check_params)
            elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY and t_const.foreign_key_table and t_const.foreign_key_columns and t_const.columns:
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
            action_part, action_params = self._format_alter_table_action(action)
            action_parts.append(action_part)
            all_params.extend(action_params)

        if action_parts:
            # Join actions with commas (some databases support multiple actions per ALTER TABLE)
            parts.append(" " + ", ".join(action_parts))

        return " ".join(parts), tuple(all_params)

    def _format_alter_table_action(self, action: "AlterTableAction") -> Tuple[str, tuple]:
        """Format individual alter table action."""
        from rhosocial.activerecord.backend.expression.statements import (
            AddColumn, DropColumn, AlterColumn, AddConstraint, DropConstraint,
            RenameObject, AddIndex, DropIndex
        )

        all_params = []

        if isinstance(action, AddColumn):
            # Format ADD COLUMN action
            column_sql, column_params = self.format_column_definition(action.column)
            all_params.extend(column_params)
            return f"ADD COLUMN {column_sql}", tuple(all_params)

        elif isinstance(action, DropColumn):
            # Format DROP COLUMN action
            return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()

        elif isinstance(action, AlterColumn):
            # Format ALTER COLUMN action
            column_part = f"ALTER COLUMN {self.format_identifier(action.column_name)} {action.operation}"
            if hasattr(action, 'new_value') and action.new_value is not None:
                # Handle different types of new_value based on operation
                if action.operation == "SET DATA TYPE":
                    # For SET DATA TYPE, new_value is a type specification, not a parameter
                    column_part += f" {action.new_value}"
                elif isinstance(action.new_value, str):
                    # Handle literal strings
                    column_part += f" {self.get_placeholder()}"
                    all_params.append(action.new_value)
                elif hasattr(action.new_value, 'to_sql'):
                    # If it's an expression (like FunctionCall), format it
                    value_sql, value_params = action.new_value.to_sql()
                    column_part += f" {value_sql}"
                    all_params.extend(value_params)
                else:
                    # Handle other literal values
                    column_part += f" {self.get_placeholder()}"
                    all_params.append(action.new_value)
            # Add cascade if specified
            if hasattr(action, 'cascade') and action.cascade:
                column_part += " CASCADE"
            return column_part, tuple(all_params)

        elif isinstance(action, AddConstraint):
            # Format ADD CONSTRAINT action (would delegate to constraint formatting)
            # For a table-level constraint, format it appropriately
            from rhosocial.activerecord.backend.expression.statements import TableConstraintType

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

            return f"ADD {' '.join(parts)}", tuple(all_params)

        elif isinstance(action, DropConstraint):
            # Format DROP CONSTRAINT action
            result = f"DROP CONSTRAINT {self.format_identifier(action.constraint_name)}"
            if hasattr(action, 'cascade') and action.cascade:
                result += " CASCADE"
            return result, tuple(all_params)

        elif isinstance(action, RenameObject):
            # Format RENAME action based on object type
            if hasattr(action, 'object_type') and action.object_type.upper() == "COLUMN":
                return f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}", ()
            elif hasattr(action, 'object_type') and action.object_type.upper() == "TABLE":
                # Though this wouldn't typically be used in ALTER TABLE context
                return f"RENAME TO {self.format_identifier(action.new_name)}", ()
            else:
                return f"RENAME {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}", ()

        elif isinstance(action, AddIndex):
            # Format ADD INDEX action
            # This is usually done separately from ALTER TABLE in most dialects
            # But we include it for completeness
            return f"ADD INDEX {self.format_identifier(action.index.name)}", ()

        elif isinstance(action, DropIndex):
            # Format DROP INDEX action
            cmd = f"DROP INDEX {self.format_identifier(action.index_name)}"
            if hasattr(action, 'if_exists') and action.if_exists:
                cmd = f"DROP INDEX IF EXISTS {self.format_identifier(action.index_name)}"
            return cmd, ()

        else:
            # Handle unknown action types
            return f"PROCESS {type(action).__name__}", ()

    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, tuple]:
        """Format a column definition for use in ADD COLUMN clauses."""
        all_params = []

        # Basic column definition: name data_type
        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type}"

        # Handle nullable flag
        if col_def.nullable is False:
            col_sql += " NOT NULL"
        elif col_def.nullable is True:
            col_sql += " NULL"  # Explicitly allow NULL (though redundant in most cases)

        # Handle constraints
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType

        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                col_sql += " PRIMARY KEY"
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                col_sql += " NOT NULL"
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                col_sql += " UNIQUE"
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT and constraint.default_value is not None:
                if isinstance(constraint.default_value, bases.BaseExpression):
                    default_sql, default_params = constraint.default_value.to_sql()
                    col_sql += f" DEFAULT {default_sql}"
                    all_params.extend(default_params)
                else:
                    col_sql += f" DEFAULT {self.get_placeholder()}"
                    all_params.append(constraint.default_value)
            elif constraint.constraint_type == ColumnConstraintType.CHECK and constraint.check_condition is not None:
                check_sql, check_params = constraint.check_condition.to_sql()
                col_sql += f" CHECK ({check_sql})"
                all_params.extend(check_params)
            elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY and constraint.foreign_key_reference is not None:
                referenced_table, referenced_columns = constraint.foreign_key_reference
                ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
                col_sql += f" REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})"

        # Add comment if present
        if col_def.comment:
            col_sql += f" COMMENT '{col_def.comment}'"

        return col_sql, tuple(all_params)
    # endregion

    # region Clause Formatting
    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
        all_params: List[Any] = []
        parts = ["ON CONFLICT"]
        if expr.conflict_target:
            target_parts = []
            for t in expr.conflict_target:
                if isinstance(t, str):
                    target_parts.append(self.format_identifier(t))
                else:
                    t_sql, t_params = t.to_sql()
                    target_parts.append(t_sql)
                    all_params.extend(t_params)
            parts.append(f"({', '.join(target_parts)})")

        if expr.do_nothing:
            parts.append("DO NOTHING")
        elif expr.update_assignments:
            parts.append("DO UPDATE SET")
            update_parts = []
            for col, e in expr.update_assignments.items():
                col_sql = self.format_identifier(col)
                expr_sql, expr_params = e.to_sql()
                update_parts.append(f"{col_sql} = {expr_sql}")
                all_params.extend(expr_params)
            parts.append(", ".join(update_parts))
            if expr.update_where:
                where_sql, where_params = expr.update_where.to_sql()
                parts.append(f"WHERE {where_sql}")
                all_params.extend(where_params)

        return " ".join(parts), tuple(all_params)

    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, tuple]:
        """Formats a RETURNING clause with the provided expressions."""
        all_params: List[Any] = []
        expr_parts = []

        for expr in clause.expressions:
            sql, params = expr.to_sql()
            expr_parts.append(sql)
            all_params.extend(params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"

        # Add alias if provided
        if clause.alias:
            returning_sql += f" AS {self.format_identifier(clause.alias)}"

        return returning_sql, tuple(all_params)

    def format_filter_clause(self, condition_sql: str, condition_params: tuple) -> Tuple[str, Tuple]:
        return f"FILTER (WHERE {condition_sql})", condition_params

    def format_qualify_clause(self, clause: "QualifyClause") -> Tuple[str, tuple]:
        condition_sql, condition_params = clause.condition.to_sql()
        return f"QUALIFY {condition_sql}", condition_params

    def format_window_frame_specification(self, spec: "WindowFrameSpecification") -> Tuple[str, tuple]:
        parts = [spec.frame_type]
        if spec.end_frame:
            parts.append(f"BETWEEN {spec.start_frame} AND {spec.end_frame}")
        else:
            parts.append(spec.start_frame)
        return " ".join(parts), ()

    def format_window_specification(self, spec: "WindowSpecification") -> Tuple[str, tuple]:
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

    def format_window_definition(self, spec: "WindowDefinition") -> Tuple[str, tuple]:
        spec_sql, spec_params = self.format_window_specification(spec.specification)
        window_def = f"{self.format_identifier(spec.name)} AS ({spec_sql})"
        return window_def, spec_params

    def format_window_clause(self, clause: "WindowClause") -> Tuple[str, tuple]:
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

    def format_window_function_call(self, call: "WindowFunctionCall") -> Tuple[str, tuple]:
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
            else:
                # Inline window specification
                window_spec_sql, window_spec_params = self.format_window_specification(call.window_spec)
                window_part = f"({window_spec_sql})" if window_spec_sql else "()"
                all_params.extend(window_spec_params)

            sql = f"{func_sql} OVER {window_part}"

        if call.alias:
            sql = f"{sql} AS {self.format_identifier(call.alias)}"

        return sql, tuple(all_params)

    def format_match_clause(self, clause: "MatchClause") -> Tuple[str, tuple]:
        """Format MATCH clause with expression."""
        # This method is called from MatchClause.to_sql(), so we need to format the MATCH clause
        # with the path components from the clause
        path_sql, all_params = [], []
        for part in clause.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)

        match_sql = f"MATCH {' '.join(path_sql)}"
        return match_sql, tuple(all_params)

    def format_temporal_options(self, options: Dict[str, Any]) -> Tuple[str, tuple]:
        if not options:
            return "", ()
        sql_parts, params = ["FOR SYSTEM_TIME"], []
        # Add temporal options to SQL parts based on the options provided
        for key, value in options.items():
            sql_parts.append(f"{key.upper()} ?")
            params.append(value)
        return " ".join(sql_parts), tuple(params)

    # region View and Query Part Formatting Methods

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement with comprehensive support for different options."""
        all_params = []

        # Build the basic statement with options
        parts = ["CREATE"]

        # Add replace if needed
        if expr.replace:
            parts.append("OR REPLACE")

        # Add temporary if needed
        if expr.temporary:
            parts.append("TEMPORARY")

        parts.append("VIEW")
        parts.append(self.format_identifier(expr.view_name))

        # Add column aliases if specified
        if expr.column_aliases:
            alias_parts = []
            for alias in expr.column_aliases:
                if isinstance(alias, str):
                    alias_parts.append(self.format_identifier(alias))
                else:  # ColumnAlias object
                    alias_parts.append(self.format_identifier(alias.alias or alias.name))
            parts.append(f"({', '.join(alias_parts)})")

        # Add AS and the query
        query_sql, query_params = expr.query.to_sql()
        parts.append(f" AS ({query_sql})")
        all_params.extend(query_params)

        # Handle view-specific options
        from rhosocial.activerecord.backend.expression.statements import ViewCheckOption
        options = expr.options
        if options.check_option:
            # Handle check option based on enum value
            if options.check_option == ViewCheckOption.LOCAL:
                parts.append(" WITH LOCAL CHECK OPTION")
            elif options.check_option == ViewCheckOption.CASCADED:
                parts.append(" WITH CASCADED CHECK OPTION")

        return " ".join(parts), tuple(all_params)

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement with IF EXISTS and CASCADE options."""
        if_exists_part = "IF EXISTS " if expr.if_exists else ""
        cascade_part = " CASCADE" if expr.cascade else ""

        sql = f"DROP VIEW {if_exists_part}{self.format_identifier(expr.view_name)}{cascade_part}"
        return sql.strip(), ()

    def format_where_clause(self, clause: "WhereClause") -> Tuple[str, tuple]:
        """Format WHERE clause with condition."""
        condition_sql, condition_params = clause.condition.to_sql()
        return f"WHERE {condition_sql}", condition_params

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

    # region Expression & Predicate Formatting
    def format_graph_vertex(
        self,
        variable: str,
        table: str
    ) -> Tuple[str, tuple]:
        """
        Formats a graph vertex expression according to SQL 2023 standard.
        The syntax is (variable IS table).
        """
        sql = f"({variable} IS {self.format_identifier(table)})"
        return sql, ()

    def format_json_expression(
        self,
        column: Union["bases.BaseExpression", str],
        path: str,
        operation: str
    ) -> Tuple[str, Tuple]:
        """Format JSON expression."""
        if isinstance(column, bases.BaseExpression):
            col_sql, col_params = column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(column)), ()
        sql = f"({col_sql} {operation} ?)"
        return sql, col_params + (path,)

    def format_graph_edge(
        self,
        variable: str,
        table: str,
        direction: "GraphEdgeDirection"
    ) -> Tuple[str, tuple]:
        """
        Formats a graph edge expression according to SQL 2023 standard.
        """
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

    def format_grouping_expression(
        self,
        operation: str,
        expressions: List["bases.BaseExpression"]
    ) -> Tuple[str, tuple]:
        """
        Formats a grouping expression (ROLLUP, CUBE, GROUPING SETS).
        """
        # Check feature support based on operation type
        if operation.upper() == "ROLLUP":
            self.check_feature_support('supports_rollup', 'ROLLUP')
        elif operation.upper() == "CUBE":
            self.check_feature_support('supports_cube', 'CUBE')
        elif operation.upper() == "GROUPING SETS":
            self.check_feature_support('supports_grouping_sets', 'GROUPING SETS')

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

    def format_json_table_expression(self, json_col_sql: str, path: str, columns: List[Dict[str, Any]], alias: str, params: tuple) -> Tuple[str, Tuple]:
        cols_defs = [f"{col['name']} {col['type']} PATH '{col['path']}'" for col in columns]
        columns_sql = f"COLUMNS({', '.join(cols_defs)})"
        sql = f"JSON_TABLE({json_col_sql}, '{path}' {columns_sql}) AS {self.format_identifier(alias)}"
        return sql, params

    def format_array_expression(
        self,
        operation: str,
        elements: Optional[List["bases.BaseExpression"]],
        base_expr: Optional["bases.BaseExpression"],
        index_expr: Optional["bases.BaseExpression"]
    ) -> Tuple[str, Tuple]:
        """Format array expression."""
        if operation.upper() == "CONSTRUCTOR" and elements is not None:
            element_parts, all_params = [], []
            for elem in elements:
                elem_sql, elem_params = elem.to_sql()
                element_parts.append(elem_sql)
                all_params.extend(elem_params)
            return f"ARRAY[{', '.join(element_parts)}]", tuple(all_params)
        elif operation.upper() == "ACCESS" and base_expr and index_expr:
            base_sql, base_params = base_expr.to_sql()
            index_sql, index_params = index_expr.to_sql()
            return f"({base_sql}[{index_sql}])", base_params + index_params
        return "ARRAY[]", ()

    def format_case_expression(
        self,
        value_sql: Optional[str],
        value_params: Optional[tuple],
        conditions_results: List[Tuple[str, str, tuple, tuple]],
        else_result_sql: Optional[str],
        else_result_params: Optional[tuple],
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format CASE expression with optional alias."""
        all_params = list(value_params) if value_params else []

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

    def format_ordered_set_aggregation(self, func_name: str, func_args_sql: List[str], func_args_params: tuple, order_by_sql: List[str], order_by_params: tuple, alias: Optional[str] = None) -> Tuple[str, Tuple]:
        all_params = list(func_args_params) + list(order_by_params)
        func_part = f"{func_name.upper()}({', '.join(func_args_sql)})"
        order_by_part = f"WITHIN GROUP (ORDER BY {', '.join(order_by_sql)})"
        sql = f"{func_part} {order_by_part}"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, tuple(all_params)
    # endregion

    def format_join_expression(self, join_expr: "JoinExpression") -> Tuple[str, Tuple]:
        """Format JOIN expression with left table, right table, type, condition, and options."""
        all_params = []

        # Format left and right tables
        left_sql, left_params = join_expr.left_table.to_sql()
        right_sql, right_params = join_expr.right_table.to_sql()
        all_params.extend(left_params)
        all_params.extend(right_params)

        # Use the join type string directly
        join_clause = join_expr.join_type

        # Add NATURAL if specified
        if join_expr.natural:
            join_clause = f"NATURAL {join_clause}"

        # Build the JOIN expression
        if join_expr.using:
            # USING clause
            using_cols = [self.format_identifier(col) for col in join_expr.using]
            join_sql = f"{left_sql} {join_clause} {right_sql} USING ({', '.join(using_cols)})"
        elif join_expr.condition:
            # ON condition
            condition_sql, condition_params = join_expr.condition.to_sql()
            join_sql = f"{left_sql} {join_clause} {right_sql} ON {condition_sql}"
            all_params.extend(condition_params)
        else:
            # No condition (e.g., CROSS JOIN)
            join_sql = f"{left_sql} {join_clause} {right_sql}"

        # Add alias if specified
        if join_expr.alias:
            join_sql = f"({join_sql}) AS {self.format_identifier(join_expr.alias)}"

        return join_sql, tuple(all_params)

    def format_set_operation_expression(
        self,
        left: "bases.BaseExpression",
        right: "bases.BaseExpression",
        operation: str,
        alias: str,
        all: bool
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT)."""
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        all_str = " ALL" if all else ""
        sql = f"{left_sql} {operation}{all_str} {right_sql}"
        params = left_params + right_params
        return f"({sql}) AS {self.format_identifier(alias)}", tuple(params)
