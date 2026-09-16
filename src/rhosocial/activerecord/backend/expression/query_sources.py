# src/rhosocial/activerecord/backend/expression/query_sources.py
"""
Data source expressions for SQL queries like VALUES, table functions, lateral joins, and CTEs.

These expression classes represent different types of data sources that can be used
in the FROM clause of a query, including constructed values, table-valued functions,
lateral expressions, and common table expressions.
"""

from dataclasses import dataclass
from typing import Tuple, Any, List, Optional, Union, TYPE_CHECKING, Dict

from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression
from .core import Subquery, TableExpression
from .mixins import ArithmeticMixin, ComparisonMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .query_parts import OrderByClause, LimitOffsetClause, ForUpdateClause


class SetOperationExpression(BaseExpression):
    """Represents a set operation (UNION, INTERSECT, EXCEPT) between two queries.

    This class is commonly used for:
    1. Combining results from multiple queries
    2. Creating recursive CTEs (with UNION ALL)
    3. Removing duplicates (UNION) or keeping all rows (UNION ALL)
    4. Finding common rows (INTERSECT) or differences (EXCEPT)

    Example Usage:
        # Basic UNION operation
        union_expr = SetOperationExpression(
            dialect,
            left=QueryExpression(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name")],
                from_=TableExpression(dialect, "users")
            ),
            right=QueryExpression(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name")],
                from_=TableExpression(dialect, "customers")
            ),
            operation="UNION",
            alias="combined_users"
        )

        # UNION operation with additional clauses
        union_expr_with_order = SetOperationExpression(
            dialect,
            left=QueryExpression(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name")],
                from_=TableExpression(dialect, "users")
            ),
            right=QueryExpression(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name")],
                from_=TableExpression(dialect, "customers")
            ),
            operation="UNION",
            alias="combined_users",
            order_by_clause=OrderByClause(dialect, [Column(dialect, "id")]),
            limit_offset_clause=LimitOffsetClause(dialect, limit=10)
        )

        # Recursive CTE example using UNION ALL (essential for iterative algorithms like Sudoku solver)
        # Initial query part - base case for recursion
        initial_query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "id"),
                Column(dialect, "parent_id"),
                Column(dialect, "name"),
                Literal(dialect, 0).as_("level"),  # Starting level
                FunctionCall(
                    dialect, "ARRAY_APPEND", Literal(dialect, []), Column(dialect, "id")
                ).as_("path")  # Track path
            ],
            from_=TableExpression(dialect, "nodes"),
            where=ComparisonPredicate(dialect, "=", Column(dialect, "parent_id"), Literal(dialect, None))  # Root nodes
        )

        # Recursive query part - self-referencing query
        recursive_query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "n.id"),
                Column(dialect, "n.parent_id"),
                Column(dialect, "n.name"),
                FunctionCall(dialect, "+", Column(dialect, "r.level"), Literal(dialect, 1)).as_("level"),
                FunctionCall(dialect, "ARRAY_APPEND", Column(dialect, "r.path"), Column(dialect, "n.id")).as_("path")
            ],
            from_=[
                TableExpression(dialect, "nodes", alias="n"),
                JoinClause(
                    dialect,
                    left_table=TableExpression(dialect, "recursive_result", alias="r"),
                    right_table=TableExpression(dialect, "nodes", alias="n"),
                    join_type="INNER JOIN",
                    condition=ComparisonPredicate(dialect, "=", Column(dialect, "r.id"), Column(dialect, "n.parent_id"))
                )
            ],
            where=ComparisonPredicate(dialect, "<", Column(dialect, "r.level"), Literal(dialect, 10))  # Limit depth
        )

        # Combine initial and recursive parts with UNION ALL for recursive CTE
        recursive_union = SetOperationExpression(
            dialect,
            left=initial_query,
            right=recursive_query,
            operation="UNION ALL",
            alias="recursive_result"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        left: "BaseExpression",
        right: "BaseExpression",
        operation: str,
        alias: Optional[str] = None,
        all_: bool = False,
        order_by_clause: Optional["OrderByClause"] = None,
        limit_offset_clause: Optional["LimitOffsetClause"] = None,
        for_update_clause: Optional["ForUpdateClause"] = None,
    ):
        """
        Initialize a SetOperationExpression.

        Args:
            dialect: The SQL dialect to use for formatting
            left: The left-hand query expression
            right: The right-hand query expression
            operation: The set operation (e.g., "UNION", "INTERSECT", "EXCEPT")
            alias: Optional alias for the set operation result
            all_: Whether to use ALL variant of the operation (e.g., UNION ALL when operation="UNION")
            order_by_clause: Optional ORDER BY clause to apply to the result set
            limit_offset_clause: Optional LIMIT/OFFSET clause to apply to the result set
            for_update_clause: Optional FOR UPDATE clause to apply to the result set
        """
        super().__init__(dialect)
        self.left = left
        self.right = right
        self.operation = operation
        self.alias = alias
        self.all_ = all_
        self.order_by_clause = order_by_clause
        self.limit_offset_clause = limit_offset_clause
        self.for_update_clause = for_update_clause

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_operation_expression"


class CTEExpression(BaseExpression):
    """Represents a Common Table Expression (CTE) expression (WITH ... AS ...).

    Common Table Expressions (CTEs) allow defining temporary result sets that can be referenced
    within a SELECT, INSERT, UPDATE, or DELETE statement. They are especially useful for
    recursive queries and simplifying complex queries.

    Example Usage:
        # Basic CTE
        cte = CTEExpression(
            dialect,
            name="monthly_sales",
            query=QueryExpression(
                dialect,
                select=[Column(dialect, "month"), FunctionCall(dialect, "SUM", Column(dialect, "amount"))],
                from_=TableExpression(dialect, "sales"),
                group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "month")])
            ),
            columns=["month", "total_sales"]
        )

        # Recursive CTE (for hierarchical data or iterative algorithms like Sudoku solver)
        initial_values = ValuesExpression(
            dialect,
            values=[('1', 1)],  # Starting value
            alias="initial",
            column_names=["value", "level"]
        )

        recursive_query = QueryExpression(
            dialect,
            select=[
                FunctionCall(dialect, "CAST", Column(dialect, "value") + Literal(dialect, 1), "TEXT"),
                Column(dialect, "level") + Literal(dialect, 1)
            ],
            from_=[TableExpression(dialect, "counter")],  # Reference to CTE itself in recursive case
            where=(Column(dialect, "level") < Literal(dialect, 10))
        )

        # Combine using SetOperationExpression for recursive CTE
        combined_query = SetOperationExpression(
            dialect,
            left=initial_values,
            right=recursive_query,
            operation="UNION ALL",
            alias="recursive_union"
        )

        # To create a recursive CTE, use WithQueryExpression with recursive=True
        cte = CTEExpression(
            dialect,
            name="counter",
            query=combined_query,
            columns=["next_value", "next_level"]
        )

        # Use WithQueryExpression to create the recursive query
        recursive_query = WithQueryExpression(
            dialect,
            ctes=[cte],
            main_query=QueryExpression(
                dialect,
                select=[Column(dialect, "next_value"), Column(dialect, "next_level")],
                from_=TableExpression(dialect, "counter")
            ),
            recursive=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        query: Union["BaseExpression", "SQLQueryAndParams"],
        columns: Optional[List[str]] = None,
        materialized: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a CTEExpression.

        Args:
            dialect: The SQL dialect to use for formatting
            name: The name of the CTE
            query: The query that defines the CTE. Can be:
                   - A BaseExpression instance (e.g., QueryExpression, Subquery)
                   - A tuple of (sql_string, params) where params can be a list or tuple,
                     though using a tuple is preferred (params will be converted to tuple if list)
            columns: Optional list of column names for the CTE
            materialized: Whether the CTE should be materialized (for databases that support it)
            dialect_options: Additional dialect-specific options
        """
        super().__init__(dialect)
        self.name = name
        self.query = query
        self.columns = columns
        self.materialized = materialized
        self.dialect_options = dialect_options or {}

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_cte_expression"


class WithQueryExpression(ArithmeticMixin, ComparisonMixin, SQLValueExpression):
    """Represents a query with Common Table Expressions (WITH clause).

    This class allows combining multiple CTEs with a main query. It's commonly used for:
    1. Organizing complex queries with multiple temporary result sets
    2. Creating recursive queries (with RECURSIVE keyword)
    3. Improving query readability and maintainability

    Example Usage:
        # Create multiple CTEs
        cte1 = CTEExpression(
            dialect,
            name="users_with_orders",
            query=QueryExpression(
                dialect,
                select=[
                    Column(dialect, "u.id"),
                    Column(dialect, "u.name"),
                    FunctionCall(dialect, "COUNT", Column(dialect, "o.id")),
                ],
                from_=[TableExpression(dialect, "users", alias="u")],
                where=ComparisonPredicate(
                    dialect, ">", FunctionCall(dialect, "COUNT", Column(dialect, "o.id")), Literal(dialect, 0)
                ),
            ),
            columns=["user_id", "user_name", "order_count"]
        )

        cte2 = CTEExpression(
            dialect,
            name="top_users",
            query=QueryExpression(
                dialect,
                select=[Column(dialect, "user_id"), Column(dialect, "user_name")],
                from_=[TableExpression(dialect, "users_with_orders")],
                where=ComparisonPredicate(dialect, '>', Column(dialect, "order_count"), Literal(dialect, 5))
            ),
            columns=["user_id", "name"]
        )

        # Main query that uses the CTEs
        main_query = QueryExpression(
            dialect,
            select=[Column(dialect, "tu.name"), Column(dialect, "uwo.order_count")],
            from_=[TableExpression(dialect, "top_users", alias="tu")],
            where=ComparisonPredicate(dialect, '=', Column(dialect, "tu.user_id"), Column(dialect, "uwo.user_id"))
        )

        # Combine everything with WithQueryExpression
        with_query = WithQueryExpression(
            dialect,
            ctes=[cte1, cte2],
            main_query=main_query
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        ctes: List[CTEExpression],
        main_query: "BaseExpression",
        recursive: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.ctes = ctes
        self.main_query = main_query
        self.recursive = recursive
        self.dialect_options = dialect_options or {}

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_with_query_expression"


class ValuesExpression(BaseExpression):
    """Represents a VALUES clause (row constructor) as a data source.

    This class is commonly used for:
    1. Providing inline data in queries
    2. Creating temporary data sets for CTEs
    3. Inserting multiple rows with specific values
    4. Serving as input for recursive CTEs

    Example Usage:
        # Single row VALUES expression
        values_expr = ValuesExpression(
            dialect,
            values=[(1, "John Doe", "john@example.com")],
            alias="user_data",
            column_names=["id", "name", "email"]
        )

        # Multiple rows VALUES expression
        values_expr = ValuesExpression(
            dialect,
            values=[
                (1, "John Doe", "john@example.com"),
                (2, "Jane Smith", "jane@example.com"),
                (3, "Bob Johnson", "bob@example.com")
            ],
            alias="users",
            column_names=["id", "name", "email"]
        )

        # Using in a CTE (as initial data for recursive queries)
        initial_values = ValuesExpression(
            dialect,
            values=[('1', 1)],  # Starting value for counter
            alias="initial_counter",
            column_names=["value", "level"]
        )

        # Without alias (alias is optional)
        values_expr = ValuesExpression(
            dialect,
            values=[(1, "John Doe", "john@example.com")],
            column_names=["id", "name", "email"]
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        values: List[Tuple[Any, ...]],
        alias: Optional[str] = None,
        column_names: Optional[List[str]] = None,
    ):
        super().__init__(dialect)
        self.values, self.alias, self.column_names = values, alias, column_names

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_values_expression"


class TableFunctionExpression(BaseExpression):
    """Represents a table-valued function or array expansion function (e.g., UNNEST, JSON_TABLE).

    Example Usage:
        # With alias
        table_func = TableFunctionExpression(
            dialect,
            "UNNEST",
            ArrayExpression(dialect, [1, 2, 3]),
            alias="numbers",
            column_names=["num"]
        )

        # Without alias (alias is optional)
        table_func = TableFunctionExpression(
            dialect,
            "UNNEST",
            ArrayExpression(dialect, [1, 2, 3]),
            column_names=["num"]
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        *args: "BaseExpression",
        alias: Optional[str] = None,
        column_names: Optional[List[str]] = None,
    ):
        super().__init__(dialect)
        self.func_name, self.args, self.alias, self.column_names = func_name, list(args), alias, column_names

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_function_expression"


class LateralExpression(BaseExpression):
    """Represents a LATERAL subquery or table function call.

    Example Usage:
        # With alias
        lateral_expr = LateralExpression(
            dialect,
            Subquery(dialect, query_expr),
            alias="lateral_data"
        )

        # Without alias (alias is optional)
        lateral_expr = LateralExpression(
            dialect,
            Subquery(dialect, query_expr)
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: Union["Subquery", "TableFunctionExpression"],
        alias: Optional[str] = None,
        join_type: str = "CROSS",
    ):
        super().__init__(dialect)
        self.expression, self.alias, self.join_type = expression, alias, join_type

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_lateral_expression"


@dataclass
class JSONTableColumn:
    """A single column of a JSON_TABLE COLUMNS clause (option value object).

    ``data_type`` is a ``DataType`` expression (a SQL clause of its own); the
    option object itself does not render, but declares the expressions it
    holds so dialect propagation reaches them.
    """

    name: str
    data_type: "DataType"
    path: str

    def expression_children(self):
        """Option-object contract: expressions held by this value object."""
        if isinstance(self.data_type, BaseExpression):
            return [self.data_type]
        return []


class JSONTableExpression(TableExpression):
    """Represents a JSON_TABLE function call.

    Example Usage:
        # With alias
        json_table = JSONTableExpression(
            dialect,
            json_column="json_data",
            path="$[*]",
            columns=[JSONTableColumn("id", "INTEGER", "$.id"), JSONTableColumn("name", "TEXT", "$.name")],
            alias="parsed_json"
        )

        # Without alias (alias is optional)
        json_table = JSONTableExpression(
            dialect,
            json_column="json_data",
            path="$[*]",
            columns=[JSONTableColumn("id", "INTEGER", "$.id"), JSONTableColumn("name", "TEXT", "$.name")]
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_column: Union[str, "BaseExpression"],
        path: str,
        columns: List[JSONTableColumn],
        alias: Optional[str] = None,
    ):
        super().__init__(dialect, name="JSON_TABLE", alias=alias)
        self.json_column, self.path, self.columns = json_column, path, columns

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_table_expression"

    @property
    def expression_children(self):
        """Child expressions: the JSON column (if an expression) and each
        column's DataType. JSONTableColumn is an option value object, so its
        held DataType is surfaced here."""
        children = []
        json_column = getattr(self, "json_column", None)
        if isinstance(json_column, BaseExpression):
            children.append(json_column)
        for col in getattr(self, "columns", None) or []:
            if isinstance(col.data_type, BaseExpression):
                children.append(col.data_type)
        return children
