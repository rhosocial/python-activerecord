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
    """Represents a set operation (UNION, INTERSECT, EXCEPT) between two queries."""
    def __init__(self, dialect: "SQLDialectBase", left: "bases.BaseExpression", right: "bases.BaseExpression", operation: str, alias: str, all: bool = False):
        super().__init__(dialect)
        self.left = left
        self.right = right
        self.operation = operation
        self.alias = alias
        self.all = all

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_set_operation_expression method
        return self.dialect.format_set_operation_expression(self.left, self.right, self.operation, self.alias, self.all)


class CTEExpression(bases.BaseExpression):
    """Represents a Common Table Expression (CTE) expression (WITH ... AS ...)."""
    def __init__(self, dialect: "SQLDialectBase", name: str,
                 query: Union["core.Subquery", "bases.BaseExpression", Tuple[str, List[Any]]],
                 columns: Optional[List[str]] = None, recursive: bool = False,
                 materialized: Optional[bool] = None, dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.name = name
        self.query = query
        self.columns = columns
        self.recursive = recursive
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
            recursive=self.recursive,
            materialized=self.materialized,
            dialect_options=self.dialect_options
        )
        return sql, query_params


class WithQueryExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a query with Common Table Expressions (WITH clause)."""
    def __init__(self, dialect: "SQLDialectBase", ctes: List[CTEExpression],
                 main_query: "bases.BaseExpression", dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.ctes = ctes
        self.main_query = main_query
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
            dialect_options=self.dialect_options
        )
        return sql, tuple(all_params)


class ValuesExpression(bases.BaseExpression):
    """Represents a VALUES clause (row constructor) as a data source."""
    def __init__(self, dialect: "SQLDialectBase", values: List[Tuple[Any, ...]], alias: str, column_names: List[str]):
        super().__init__(dialect)
        self.values, self.alias, self.column_names = values, alias, column_names

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_values_expression(self.values, self.alias, self.column_names)


class TableFunctionExpression(bases.BaseExpression):
    """Represents a table-valued function or array expansion function (e.g., UNNEST, JSON_TABLE)."""
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args: "bases.BaseExpression",
                 alias: str, column_names: Optional[List[str]] = None):
        super().__init__(dialect)
        self.func_name, self.args, self.alias, self.column_names = func_name, list(args), alias, column_names

    def to_sql(self) -> Tuple[str, tuple]:
        formatted_args_sql = [arg.to_sql()[0] for arg in self.args]
        all_params = [p for arg in self.args for p in arg.to_sql()[1]]
        return self.dialect.format_table_function_expression(self.func_name, formatted_args_sql, tuple(all_params), self.alias, self.column_names)


class LateralExpression(bases.BaseExpression):
    """Represents a LATERAL subquery or table function call."""
    def __init__(self, dialect: "SQLDialectBase", expression: Union["core.Subquery", "TableFunctionExpression"], alias: str, join_type: str = "CROSS"):
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
    """Represents a JSON_TABLE function call."""
    def __init__(self, dialect: "SQLDialectBase", json_column: Union[str, "bases.BaseExpression"], path: str, columns: List[JSONTableColumn], alias: str):
        super().__init__(dialect, name="JSON_TABLE", alias=alias)
        self.json_column, self.path, self.columns = json_column, path, columns

    def to_sql(self) -> Tuple[str, tuple]:
        if isinstance(self.json_column, bases.BaseExpression):
            json_col_sql, json_col_params = self.json_column.to_sql()
        else:
            json_col_sql, json_col_params = self.dialect.format_identifier(str(self.json_column)), ()
        prepared_columns = [{"name": self.dialect.format_identifier(col.name), "type": col.data_type, "path": col.path} for col in self.columns]
        return self.dialect.format_json_table_expression(json_col_sql, self.path, prepared_columns, self.alias, json_col_params)