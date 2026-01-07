"""
Data source expressions for SQL queries like VALUES, table functions, lateral joins, and CTEs.

These expression classes represent different types of data sources that can be used
in the FROM clause of a query, including constructed values, table-valued functions,
lateral expressions, and common table expressions.
"""
from dataclasses import dataclass
from typing import Tuple, Any, List, Optional, Union, TYPE_CHECKING, Dict

from . import bases
from . import core
from . import mixins

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class SetOperationExpression(bases.BaseExpression):
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

        # UNION operation without alias (alias is optional)
        union_expr_no_alias = SetOperationExpression(
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
            operation="UNION"
        )

        # Recursive CTE with UNION ALL (essential for iterative algorithms like Sudoku solver)
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
            from_=[TableExpression(dialect, "counter")],  # Reference to CTE itself
            where=(Column(dialect, "level") < Literal(dialect, 10))
        )

        # Combine initial and recursive parts with UNION ALL for recursive CTE
        recursive_union = SetOperationExpression(
            dialect,
            left=initial_values,
            right=recursive_query,
            operation="UNION ALL",
            alias="counter_recursive"
        )

        # Without alias (alias is optional)
        recursive_union_no_alias = SetOperationExpression(
            dialect,
            left=initial_values,
            right=recursive_query,
            operation="UNION ALL"
        )
    """
    def __init__(self, dialect: "SQLDialectBase", left: "bases.BaseExpression", right: "bases.BaseExpression", operation: str, alias: Optional[str] = None, all_: bool = False):
        """
        Initialize a SetOperationExpression.

        Args:
            dialect: The SQL dialect to use for formatting
            left: The left-hand query expression
            right: The right-hand query expression
            operation: The set operation (e.g., "UNION", "INTERSECT", "EXCEPT")
            alias: Optional alias for the set operation result
            all_: Whether to use ALL variant of the operation (e.g., UNION ALL when operation="UNION")
        """
        super().__init__(dialect)
        self.left = left
        self.right = right
        self.operation = operation
        self.alias = alias
        self.all = all_

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_set_operation_expression method
        return self.dialect.format_set_operation_expression(self.left, self.right, self.operation, self.alias, self.all)


class CTEExpression(bases.BaseExpression):
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
    def __init__(self, dialect: "SQLDialectBase", name: str,
                 query: Union["core.Subquery", "bases.BaseExpression", Tuple[str, List[Any]]],
                 columns: Optional[List[str]] = None,
                 materialized: Optional[bool] = None, dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.name = name
        self.query = query
        self.columns = columns
        self.materialized = materialized
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        # Handle different query types that may be stored in self.query:
        if isinstance(self.query, bases.BaseExpression):
            # When query is a BaseExpression (e.g., Subquery, QueryExpression),
            # call its to_sql() method to get SQL and parameters
            query_sql, query_params = self.query.to_sql()
        elif isinstance(self.query, tuple):
            # When query is a tuple of format (sql_string, params_list),
            # extract SQL and parameters directly from the tuple
            query_sql, query_params = self.query[0], tuple(self.query[1])
        else:
            # When query is a raw string or other type that can be converted to string,
            # convert to string and no parameters are associated
            query_sql, query_params = str(self.query), ()

        sql = self.dialect.format_cte(
            name=self.name,
            query_sql=query_sql,
            columns=self.columns,
            materialized=self.materialized,
            dialect_options=self.dialect_options
        )
        return sql, query_params


class WithQueryExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
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
                select=[Column(dialect, "u.id"), Column(dialect, "u.name"), FunctionCall(dialect, "COUNT", Column(dialect, "o.id"))],
                from_=[TableExpression(dialect, "users", alias="u")],
                where=ComparisonPredicate(dialect, '>', FunctionCall(dialect, "COUNT", Column(dialect, "o.id")), Literal(dialect, 0))
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
    def __init__(self, dialect: "SQLDialectBase", ctes: List[CTEExpression],
                 main_query: "bases.BaseExpression", recursive: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.ctes = ctes
        self.main_query = main_query
        self.recursive = recursive
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        cte_sql_parts = []
        for cte in self.ctes:
            cte_sql, cte_params = cte.to_sql()
            cte_sql_parts.append(cte_sql)
            all_params.extend(cte_params)
        main_sql, main_params = self.main_query.to_sql()
        all_params.extend(main_params)

        sql = self.dialect.format_with_query(
            cte_sql_parts=cte_sql_parts,
            main_query_sql=main_sql,
            dialect_options=self.dialect_options,
            has_recursive=self.recursive  # Pass recursive information to dialect
        )
        return sql, tuple(all_params)


class ValuesExpression(bases.BaseExpression):
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
    def __init__(self, dialect: "SQLDialectBase", values: List[Tuple[Any, ...]], alias: Optional[str] = None, column_names: Optional[List[str]] = None):
        super().__init__(dialect)
        self.values, self.alias, self.column_names = values, alias, column_names

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_values_expression(self.values, self.alias, self.column_names)


class TableFunctionExpression(bases.BaseExpression):
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
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args: "bases.BaseExpression",
                 alias: Optional[str] = None, column_names: Optional[List[str]] = None):
        super().__init__(dialect)
        self.func_name, self.args, self.alias, self.column_names = func_name, list(args), alias, column_names

    def to_sql(self) -> Tuple[str, tuple]:
        formatted_args_sql = [arg.to_sql()[0] for arg in self.args]
        all_params = [p for arg in self.args for p in arg.to_sql()[1]]
        return self.dialect.format_table_function_expression(self.func_name, formatted_args_sql, tuple(all_params), self.alias, self.column_names)


class LateralExpression(bases.BaseExpression):
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
    def __init__(self, dialect: "SQLDialectBase", expression: Union["core.Subquery", "TableFunctionExpression"], alias: Optional[str] = None, join_type: str = "CROSS"):
        super().__init__(dialect)
        self.expression, self.alias, self.join_type = expression, alias, join_type

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expression.to_sql()
        return self.dialect.format_lateral_expression(expr_sql, expr_params, self.alias, self.join_type)


@dataclass
class JSONTableColumn:
    name: str
    data_type: str
    path: str


class JSONTableExpression(core.TableExpression):
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
    def __init__(self, dialect: "SQLDialectBase", json_column: Union[str, "bases.BaseExpression"], path: str, columns: List[JSONTableColumn], alias: Optional[str] = None):
        super().__init__(dialect, name="JSON_TABLE", alias=alias)
        self.json_column, self.path, self.columns = json_column, path, columns

    def to_sql(self) -> Tuple[str, tuple]:
        if isinstance(self.json_column, bases.BaseExpression):
            json_col_sql, json_col_params = self.json_column.to_sql()
        else:
            json_col_sql, json_col_params = self.dialect.format_identifier(str(self.json_column)), ()
        prepared_columns = [{"name": self.dialect.format_identifier(col.name), "type": col.data_type, "path": col.path} for col in self.columns]
        return self.dialect.format_json_table_expression(json_col_sql, self.path, prepared_columns, self.alias, json_col_params)