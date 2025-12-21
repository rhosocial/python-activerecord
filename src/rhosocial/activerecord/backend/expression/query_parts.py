# src/rhosocial/activerecord/backend/expression/query_parts.py
"""
SQL query clause expressions like WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, etc.

These expression classes collect parameters for specific SQL clauses 
and delegate SQL generation to backend-specific dialects.
"""
from typing import Tuple, List, Union, Optional, Any, Dict
from enum import Enum
from dataclasses import dataclass
from . import bases
from . import core
from . import mixins


class JoinType(Enum):
    """Enumeration of SQL JOIN types."""
    INNER = "INNER JOIN"        # INNER JOIN
    JOIN = "JOIN"               # JOIN (equivalent to INNER JOIN)
    LEFT = "LEFT JOIN"          # LEFT JOIN
    LEFT_OUTER = "LEFT OUTER JOIN"  # LEFT OUTER JOIN
    RIGHT = "RIGHT JOIN"        # RIGHT JOIN
    RIGHT_OUTER = "RIGHT OUTER JOIN"  # RIGHT OUTER JOIN
    FULL = "FULL JOIN"          # FULL JOIN
    FULL_OUTER = "FULL OUTER JOIN"    # FULL OUTER JOIN
    CROSS = "CROSS JOIN"        # CROSS JOIN
    # Additional types could be added if needed
    # MySQL-specific
    STRAIGHT = "STRAIGHT JOIN"  # MySQL STRAIGHT_JOIN
    # Other database-specific types could be added here

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase
#     from .predicates import SQLPredicate
#     from .bases import BaseExpression


class WhereClause(bases.BaseExpression):
    """
    Represents a WHERE clause in a SQL query.

    The WHERE clause filters rows based on specified conditions, allowing only
    rows satisfying the predicate to be included in the result set.
    
    Examples:
        # Basic WHERE clause
        where_clause = WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "status"), Literal(dialect, "active"))
        )
        
        # Complex WHERE with logical operators
        condition = (Column(dialect, "age") > Literal(dialect, 18)) & (Column(dialect, "status") == Literal(dialect, "active"))
        where_clause = WhereClause(dialect, condition=condition)
    """
    def __init__(self, dialect: "SQLDialectBase", condition: "bases.SQLPredicate"):
        super().__init__(dialect)
        self.condition = condition  # The filtering condition (predicate)

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the WHERE clause to the configured dialect."""
        return self.dialect.format_where_clause(self)


class GroupByHavingClause(bases.BaseExpression):
    """
    Represents combined GROUP BY and HAVING clauses in a SQL query.

    This unified class handles both grouping specifications and group filtering,
    enforcing the dependency that HAVING requires GROUP BY. It centralizes
    validation and SQL generation for these related clauses.

    Examples:
        # Basic GROUP BY only
        group_clause = GroupByHavingClause(
            dialect,
            group_by=[Column(dialect, "category")]
        )

        # GROUP BY with HAVING condition
        group_having_clause = GroupByHavingClause(
            dialect,
            group_by=[Column(dialect, "category")],
            having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5)
        )

        # Complex grouping with multiple expressions and filtering
        complex_clause = GroupByHavingClause(
            dialect,
            group_by=[
                FunctionCall(dialect, "YEAR", Column(dialect, "created_at")),
                Column(dialect, "status")
            ],
            having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 10)
        )
    """
    def __init__(self,
                 dialect: "SQLDialectBase",
                 group_by: Optional[List["bases.BaseExpression"]] = None,  # List of grouping expressions
                 having: Optional["bases.SQLPredicate"] = None):  # HAVING condition (requires GROUP BY)
        super().__init__(dialect)

        self.group_by = group_by or []
        self.having = having

        # Validate that HAVING requires GROUP BY
        if having is not None and not self.group_by:
            raise ValueError("HAVING clause requires GROUP BY clause")

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the GROUP BY/HAVING clause combination to the configured dialect."""
        return self.dialect.format_group_by_having_clause(self)


class OrderByClause(bases.BaseExpression):
    """
    Represents an ORDER BY clause in a SQL query.

    The ORDER BY clause sorts the result set based on specified columns or expressions,
    with optional direction (ASC/DESC) and null order handling.
    
    Examples:
        # Basic ORDER BY
        order_by = OrderByClause(
            dialect,
            expressions=[(Column(dialect, "name"), "ASC")]
        )
        
        # Complex ORDER BY with multiple expressions and directions
        order_by = OrderByClause(
            dialect,
            expressions=[
                (Column(dialect, "category"), "ASC"),
                (FunctionCall(dialect, "COUNT", Column(dialect, "id")), "DESC"),
                (Column(dialect, "name"), "ASC")
            ]
        )
        
        # ORDER BY with expression only (defaults to ASC)
        order_by = OrderByClause(
            dialect,
            expressions=[Column(dialect, "date_created")]
        )
    """
    def __init__(self,
                 dialect: "SQLDialectBase",
                 expressions: List[Union[
                     "bases.BaseExpression",  # Expression with default ASC direction
                     Tuple["bases.BaseExpression", str]  # (expression, direction)
                 ]]):
        super().__init__(dialect)
        self.expressions = expressions  # List of ordering specifications

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the ORDER BY clause to the configured dialect."""
        return self.dialect.format_order_by_clause(self)


class LimitOffsetClause(bases.BaseExpression):
    """
    Represents LIMIT and/or OFFSET clauses in a SQL query.

    The LIMIT clause restricts the number of rows returned, while OFFSET
    skips a specified number of rows before starting to return rows.
    
    Examples:
        # Basic LIMIT
        limit_clause = LimitOffsetClause(dialect, limit=10)
        
        # LIMIT with OFFSET
        limit_clause = LimitOffsetClause(dialect, limit=10, offset=20)
        
        # OFFSET only (some databases support this)
        offset_clause = LimitOffsetClause(dialect, offset=50)
    """
    def __init__(self,
                 dialect: "SQLDialectBase",
                 limit: Optional[Union[int, "bases.BaseExpression"]] = None,
                 offset: Optional[Union[int, "bases.BaseExpression"]] = None):
        super().__init__(dialect)

        # Validate that offset requires limit in dialects that don't support offset without limit
        if offset is not None and limit is None:
            if not dialect.supports_offset_without_limit():
                raise ValueError("OFFSET clause requires LIMIT clause in this dialect")

        self.limit = limit  # Maximum number of rows to return (optional)
        self.offset = offset  # Number of rows to skip (optional, requires LIMIT in most dialects)

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the LIMIT/OFFSET clauses to the configured dialect."""
        return self.dialect.format_limit_offset_clause(self)


class QualifyClause(bases.BaseExpression):
    """
    Represents a QUALIFY clause in a SQL query (available in some SQL dialects like Snowflake).

    The QUALIFY clause filters rows based on the results of window functions,
    similar to how HAVING filters groups based on aggregate function results.
    
    Examples:
        # QUALIFY with window function results
        window_spec = WindowSpecification(
            dialect,
            partition_by=[Column(dialect, "department")],
            order_by=[(Column(dialect, "salary"), "DESC")]
        )
        rank_func = WindowFunctionCall(
            dialect,
            function_name="ROW_NUMBER",
            window_spec=window_spec
        )
        
        qualify_clause = QualifyClause(
            dialect,
            condition=rank_func <= Literal(dialect, 3)  # Top 3 earners per department
        )
    """
    def __init__(self, dialect: "SQLDialectBase", condition: "bases.SQLPredicate"):
        super().__init__(dialect)
        self.condition = condition  # The window function filter condition (predicate)

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the QUALIFY clause to the configured dialect."""
        return self.dialect.format_qualify_clause(self)


class ForUpdateClause(bases.BaseExpression):
    """
    Represents a FOR UPDATE clause used for row-level locking in SELECT statements.

    The FOR UPDATE clause locks selected rows preventing other transactions from
    modifying them until the current transaction is committed or rolled back.

    Example Usage:
        # Basic FOR UPDATE
        for_update = ForUpdateClause(dialect)

        # FOR UPDATE with specific columns
        for_update = ForUpdateClause(
            dialect, 
            of_columns=[Column(dialect, "id"), "name"]
        )

        # FOR UPDATE with NOWAIT
        for_update = ForUpdateClause(dialect, nowait=True)

        # FOR UPDATE with SKIP LOCKED
        for_update = ForUpdateClause(dialect, skip_locked=True)
    """
    def __init__(self, dialect: "SQLDialectBase",
                 of_columns: Optional[List[Union[str, "bases.BaseExpression"]]] = None,  # Specify columns to lock
                 nowait: bool = False,  # NOWAIT option - fail immediately if locked
                 skip_locked: bool = False,  # SKIP LOCKED option - skip locked rows
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options
        super().__init__(dialect)
        self.of_columns = of_columns or []  # Columns to apply the lock to
        self.nowait = nowait  # If True, fail immediately if rows are locked
        self.skip_locked = skip_locked  # If True, skip locked rows instead of waiting
        self.dialect_options = dialect_options or {}  # Additional dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the SQL representation of the FOR UPDATE clause.

        This method delegates the actual SQL generation to the configured dialect,
        allowing for database-specific variations in the FOR UPDATE syntax.

        Args:
            None - All data is contained within the object instance

        Returns:
            Tuple containing:
            - SQL string fragment for the FOR UPDATE clause
            - Tuple of parameter values for prepared statements
        """
        return self.dialect.format_for_update_clause(self)


class GroupingExpression(bases.BaseExpression):
    """Represents grouping operations like ROLLUP, CUBE, and GROUPING SETS."""
    def __init__(self, dialect: "SQLDialectBase",
                 operation: str,
                 expressions: List["bases.BaseExpression"]):
        super().__init__(dialect)
        self.operation = operation
        self.expressions = expressions

    def to_sql(self) -> Tuple[str, tuple]:
        op, all_params = self.operation.upper(), []
        if op == "ROLLUP": self.dialect.check_feature_support('supports_rollup', 'ROLLUP')
        elif op == "CUBE": self.dialect.check_feature_support('supports_cube', 'CUBE')
        elif op == "GROUPING SETS": self.dialect.check_feature_support('supports_grouping_sets', 'GROUPING SETS')

        if op == "GROUPING SETS":
            sets_parts = []
            for expr_list in self.expressions:
                expr_parts = []
                for expr in expr_list:
                    expr_sql, expr_params = expr.to_sql()
                    expr_parts.append(expr_sql)
                    all_params.extend(expr_params)
                sets_parts.append(f"({', '.join(expr_parts)})")
            inner_expr = ", ".join(sets_parts)
            sql = f"{op}({inner_expr})"
        else:
            expr_parts = []
            for expr in self.expressions:
                expr_sql, expr_params = expr.to_sql()
                expr_parts.append(expr_sql)
                all_params.extend(expr_params)
            inner_expr = ", ".join(expr_parts)
            sql = f"{op}({inner_expr})"

        return sql, tuple(all_params)


class JoinExpression(bases.BaseExpression):
    """
    Represents a JOIN expression (e.g., table1 JOIN table2 ON condition).

    This class collects all parameters for a JOIN operation and delegates
    the SQL generation to the configured dialect for database-specific syntax.

    Example Usage:
        # Basic INNER JOIN with ON condition
        join_expr = JoinExpression(
            dialect,
            left_table=TableExpression(dialect, "users", alias="u"),
            right_table=TableExpression(dialect, "orders", alias="o"),
            join_type=JoinType.INNER,
            condition=Column(dialect, "user_id", "u") == Column(dialect, "user_id", "o")
        )

        # LEFT JOIN with USING clause
        join_expr = JoinExpression(
            dialect,
            left_table=TableExpression(dialect, "employees", alias="e"),
            right_table=TableExpression(dialect, "departments", alias="d"),
            join_type=JoinType.LEFT,
            using=["dept_id"]
        )

        # NATURAL JOIN
        join_expr = JoinExpression(
            dialect,
            left_table=TableExpression(dialect, "table1"),
            right_table=TableExpression(dialect, "table2"),
            join_type=JoinType.INNER,
            natural=True
        )
    """
    def __init__(self,
                 dialect: "SQLDialectBase",
                 left_table: Union[str, "core.TableExpression", "core.Subquery", "QueryExpression"],
                 right_table: Union[str, "core.TableExpression", "core.Subquery", "QueryExpression"],
                 join_type: str = "JOIN",
                 condition: Optional["bases.SQLPredicate"] = None,  # ON condition (mutually exclusive with 'using')
                 using: Optional[List[str]] = None,  # USING clause columns (mutually exclusive with 'condition')
                 natural: bool = False,  # NATURAL join flag
                 alias: Optional[str] = None,  # Alias for the joined result
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options
        super().__init__(dialect)

        # Normalize table inputs
        self.left_table = left_table if isinstance(left_table, (core.TableExpression, core.Subquery)) else core.TableExpression(dialect, str(left_table))
        self.right_table = right_table if isinstance(right_table, (core.TableExpression, core.Subquery)) else core.TableExpression(dialect, str(right_table))

        # Store join_type as string
        self.join_type = join_type

        # Validate mutual exclusivity of condition and using
        if condition is not None and using is not None:
            raise ValueError("Cannot specify both 'condition' (ON) and 'using' (USING) clauses in a JOIN")

        # Store other parameters
        self.condition = condition  # ON condition
        self.using = using  # USING columns
        self.natural = natural  # NATURAL join flag
        self.alias = alias  # Alias for the join result
        self.dialect_options = dialect_options or {}  # Dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the JOIN expression to the configured dialect."""
        return self.dialect.format_join_expression(self)