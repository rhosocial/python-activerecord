# src/rhosocial/activerecord/backend/expression/query_clauses.py
"""
Expressions related to SQL query clauses such as SET operations, GROUPING, JOINs, and CTEs.
"""
from typing import Tuple, Any, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
from .base import BaseExpression, SQLPredicate
from .core import Subquery, TableExpression # Import TableExpression
from ..dialect import SQLDialectBase

# Imported for type hinting
if TYPE_CHECKING:
    from .statements import QueryExpression


class SetOperationExpression(BaseExpression):
    """
    Represents a set operation (UNION, INTERSECT, EXCEPT) between two queries.
    """
    def __init__(self, dialect: SQLDialectBase, left: BaseExpression, right: BaseExpression, operation: str, alias: str, all: bool = False):
        """
        Initializes a set operation expression.

        Args:
            dialect: The SQL dialect instance.
            left: The left-hand query expression.
            right: The right-hand query expression.
            operation: The set operation ("UNION", "INTERSECT", "EXCEPT").
            alias: The alias name for the set operation result.
            all: Whether to use ALL variant (UNION ALL, etc.)
        """
        super().__init__(dialect)
        self.left = left
        self.right = right
        self.operation = operation
        self.alias = alias
        self.all = all

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()

        all_str = " ALL" if self.all else ""
        sql = f"({left_sql}) {self.operation}{all_str} ({right_sql})"
        params = left_params + right_params
        
        return f"({sql}) AS {self.dialect.format_identifier(self.alias)}", tuple(params)


class GroupingExpression(BaseExpression):
    """
    Represents grouping operations like ROLLUP, CUBE, and GROUPING SETS.
    """
    def __init__(self, dialect: SQLDialectBase,
                 operation: str,  # 'ROLLUP', 'CUBE', or 'GROUPING SETS'
                 expressions: List[BaseExpression]):
        """
        Initializes a grouping expression.

        Args:
            dialect: The SQL dialect instance.
            operation: The grouping operation type ('ROLLUP', 'CUBE', 'GROUPING SETS').
            expressions: List of expressions to group by.
        """
        super().__init__(dialect)
        self.operation = operation
        self.expressions = expressions

    def to_sql(self) -> Tuple[str, tuple]:
        op = self.operation.upper()
        
        # Check for feature support and provide suggestions
        if op == "ROLLUP":
            self.dialect.check_feature_support(
                'supports_rollup', 'ROLLUP', 
                suggestion="Consider using multiple GROUP BY queries with UNION ALL."
            )
        elif op == "CUBE":
            self.dialect.check_feature_support(
                'supports_cube', 'CUBE',
                suggestion="This can be emulated by generating all grouping combinations manually with UNION ALL."
            )
        elif op == "GROUPING SETS":
            self.dialect.check_feature_support(
                'supports_grouping_sets', 'GROUPING SETS',
                suggestion="This can also be emulated with multiple GROUP BY queries combined with UNION ALL."
            )

        expr_parts = []
        all_params: List[Any] = []

        for expr in self.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        if self.operation.upper() == "GROUPING SETS":
            # Special handling for GROUPING SETS which has nested structure
            inner_expr = "(" + ", ".join(expr_parts) + ")"
            sql = f"{self.operation}({inner_expr})"
        else:
            # For ROLLUP and CUBE
            sql = f"{self.operation}({', '.join(expr_parts)})"

        return sql, tuple(all_params)


class GroupExpression(BaseExpression):
    """
    Represents a GROUP BY expression.
    """
    def __init__(self, dialect: SQLDialectBase, expressions: List[BaseExpression]):
        """
        Initializes a GROUP BY expression.

        Args:
            dialect: The SQL dialect instance.
            expressions: List of expressions to group by.
        """
        super().__init__(dialect)
        self.expressions = expressions

    def to_sql(self) -> Tuple[str, tuple]:
        expr_parts = []
        all_params: List[Any] = []

        for expr in self.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        sql = f"GROUP BY {', '.join(expr_parts)}"
        return sql, tuple(all_params)


class JoinExpression(BaseExpression):
    """
    Represents a JOIN expression (e.g., table1 JOIN table2 ON condition).
    """
    def __init__(self, dialect: SQLDialectBase,
                 left_table: Union[str, TableExpression, Subquery, "QueryExpression"],
                 right_table: Union[str, TableExpression, Subquery, "QueryExpression"],
                 alias: Optional[str] = None,
                 join_type: str = "INNER",
                 condition: Optional[SQLPredicate] = None,
                 natural: bool = False,
                 using: Optional[List[str]] = None):  # For USING clause
        """
        Initializes a JOIN expression.

        Args:
            dialect: The SQL dialect instance.
            left_table: Left table in the join (as string or expression).
            right_table: Right table in the join (as string or expression).
            join_type: Type of join ("INNER", "LEFT", "RIGHT", "FULL", "CROSS").
            condition: Join condition (for ON clause).
            natural: Whether this is a NATURAL join.
            using: Column names for USING clause (alternative to condition).
            alias: The alias name for the join expression.
        """
        super().__init__(dialect)
        self.left_table = left_table
        self.right_table = right_table
        self.join_type = join_type
        self.condition = condition
        self.natural = natural
        self.using = using
        self.alias = alias

    def _build_base_join_sql(self) -> Tuple[str, tuple]:
        """Helper to build the base join SQL and parameters without considering alias."""
        # Format table names
        processed_left_table = self.left_table
        if isinstance(processed_left_table, str):
            processed_left_table = TableExpression(self.dialect, processed_left_table)
        left_sql, left_params = processed_left_table.to_sql()

        processed_right_table = self.right_table
        if isinstance(processed_right_table, str):
            processed_right_table = TableExpression(self.dialect, processed_right_table)
        right_sql, right_params = processed_right_table.to_sql()

        # Build join type and natural modifier
        join_parts = []
        if self.natural:
            join_parts.append("NATURAL")
        join_parts.append(self.join_type)
        join_parts.append("JOIN")
        join_type_str = " ".join(join_parts)

        all_params: List[Any] = [] # Initialize here as it depends on conditional logic

        # Build the join expression
        if self.using:
            # USING clause
            using_cols = [self.dialect.format_identifier(col) for col in self.using]
            sql = f"{left_sql} {join_type_str} {right_sql} USING ({', '.join(using_cols)})"
            all_params.extend(left_params)
            all_params.extend(right_params)
        elif self.condition:
            # ON clause
            condition_sql, condition_params = self.condition.to_sql()
            sql = f"{left_sql} {join_type_str} {right_sql} ON {condition_sql}"
            all_params.extend(left_params)
            all_params.extend(right_params)
            all_params.extend(condition_params)
        else:
            # CROSS JOIN or NATURAL JOIN without condition
            sql = f"{left_sql} {join_type_str} {right_sql}"
            all_params.extend(left_params)
            all_params.extend(right_params)

        return sql, tuple(all_params)

    def to_sql(self) -> Tuple[str, tuple]:
        base_sql, base_params = self._build_base_join_sql() # base_sql now does not include the final alias
        formatted_sql, formatted_params = self.dialect.format_join_expression(base_sql, base_params) # Call new signature
        
        if self.alias:
            # Wrap the formatted_sql with parentheses and apply the alias
            return f"({formatted_sql}) AS {self.dialect.format_identifier(self.alias)}", formatted_params
        return formatted_sql, formatted_params


class CTEExpression(BaseExpression):
    """
    Represents a Common Table Expression (CTE) expression (WITH ... AS ...).
    """
    def __init__(self, dialect: SQLDialectBase,
                 name: str,
                 query: Union[Subquery, BaseExpression, Tuple[str, List[Any]]], # Changed QueryExpression to BaseExpression for more flexibility
                 columns: Optional[List[str]] = None,
                 recursive: bool = False,
                 materialized: Optional[bool] = None):
        """
        Initializes a CTE expression.

        Args:
            dialect: The SQL dialect instance.
            name: The name of the CTE.
            query: The query definition for the CTE.
            columns: Optional list of column names.
            recursive: Whether this is a recursive CTE.
            materialized: Whether to use MATERIALIZED/NOT MATERIALIZED hint (for databases that support it)
        """
        super().__init__(dialect)
        self.name = name
        self.query = query
        self.columns = columns
        self.recursive = recursive
        self.materialized = materialized

    def to_sql(self) -> Tuple[str, tuple]:
        # Format the CTE query
        if isinstance(self.query, Subquery):
            query_sql, query_params = self.query.to_sql()
        elif isinstance(self.query, BaseExpression):  # Like QueryExpression or any other BaseExpression
            query_sql, query_params = self.query.to_sql()
        elif isinstance(self.query, tuple):
            query_sql, query_params = self.query[0], tuple(self.query[1])
        else:
            query_sql, query_params = str(self.query), ()

        # Delegate formatting to the dialect
        sql = self.dialect.format_cte(
            name=self.name,
            query_sql=query_sql,
            columns=self.columns,
            recursive=self.recursive,
            materialized=self.materialized
        )

        return sql, query_params


class WithQueryExpression(BaseExpression):
    """
    Represents a query with Common Table Expressions (WITH clause).
    """
    def __init__(self, dialect: SQLDialectBase,
                 ctes: List[CTEExpression],
                 main_query: BaseExpression):
        """
        Initializes a WITH query expression.

        Args:
            dialect: The SQL dialect instance.
            ctes: List of CTE definitions.
            main_query: The main query that uses the CTEs.
        """
        super().__init__(dialect)
        self.ctes = ctes
        self.main_query = main_query

    def to_sql(self) -> Tuple[str, tuple]:
        cte_sql_parts = []
        all_params: List[Any] = []

        # Format each CTE
        for cte in self.ctes:
            cte_sql, cte_params = cte.to_sql()
            cte_sql_parts.append(cte_sql)
            all_params.extend(cte_params)

        # Delegate WITH clause formatting to the dialect
        with_clause_sql = self.dialect.format_with_clause(cte_sql_parts)

        # Format main query
        main_sql, main_params = self.main_query.to_sql()
        all_params.extend(main_params)

        # Combine WITH clause and main query
        sql = f"{with_clause_sql} {main_sql}" if with_clause_sql else main_sql

        return sql, tuple(all_params)


class ValuesExpression(BaseExpression):
    """
    Represents a VALUES clause (row constructor) as a data source.
    e.g., FROM (VALUES (1, 'a'), (2, 'b')) AS t(col1, col2)
    """
    def __init__(self, dialect: SQLDialectBase,
                 values: List[Tuple[Any, ...]],
                 alias: str,
                 column_names: List[str]):
        """
        Initializes a ValuesExpression.

        Args:
            dialect: The SQL dialect instance.
            values: A list of tuples, where each tuple represents a row of values.
            alias: The alias name for the values table (mandatory).
            column_names: A list of column names for the values table.
        """
        super().__init__(dialect)
        self.values = values
        self.alias = alias
        self.column_names = column_names

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_values_expression(self.values, self.alias, self.column_names)


class TableFunctionExpression(BaseExpression):
    """
    Represents a table-valued function or array expansion function (e.g., UNNEST, JSON_TABLE).
    e.g., FROM UNNEST(ARRAY[1,2,3]) AS t(col)
          FROM JSON_TABLE(...) AS jt(...)
    """
    def __init__(self, dialect: SQLDialectBase,
                 func_name: str,
                 *args: BaseExpression,
                 alias: str,
                 column_names: Optional[List[str]] = None):
        """
        Initializes a TableFunctionExpression.

        Args:
            dialect: The SQL dialect instance.
            func_name: The name of the table-valued function.
            *args: Positional arguments for the function call.
            alias: The alias name for the resulting table (mandatory).
            column_names: Optional. A list of column names for the resulting table.
        """
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.alias = alias
        self.column_names = column_names

    def to_sql(self) -> Tuple[str, tuple]:
        # Process arguments
        formatted_args_sql = []
        all_params: List[Any] = []
        for arg in self.args:
            arg_sql, arg_params = arg.to_sql()
            formatted_args_sql.append(arg_sql)
            all_params.extend(arg_params)

        return self.dialect.format_table_function_expression(
            self.func_name,
            formatted_args_sql,
            tuple(all_params),
            self.alias,
            self.column_names
        )


class LateralExpression(BaseExpression):
    """
    Represents a LATERAL subquery or table function call.
    e.g., CROSS JOIN LATERAL (SELECT ...) AS alias
    """
    def __init__(self, dialect: SQLDialectBase,
                 expression: Union[Subquery, TableFunctionExpression],
                 alias: str,
                 join_type: str = "CROSS"): # Common types are CROSS, LEFT, INNER
        """
        Initializes a LateralExpression.

        Args:
            dialect: The SQL dialect instance.
            expression: The subquery or table function expression to apply LATERAL to.
            alias: The alias name for the lateral expression (mandatory).
            join_type: The type of join to use with LATERAL (e.g., "CROSS", "LEFT").
        """
        super().__init__(dialect)
        self.expression = expression
        self.alias = alias
        self.join_type = join_type

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expression.to_sql()
        return self.dialect.format_lateral_expression(expr_sql, expr_params, self.alias, self.join_type)

@dataclass
class JSONTableColumn:
    name: str
    data_type: str
    path: str

class JSONTableExpression(TableExpression):
    """
    Represents a JSON_TABLE function call.
    e.g., FROM JSON_TABLE(json_column, '$.path[*]' COLUMNS (...))
    """
    def __init__(self, dialect: SQLDialectBase,
                 json_column: Union[str, BaseExpression],
                 path: str,
                 columns: List[JSONTableColumn],
                 alias: str):
        """
        Initializes a JSONTableExpression.

        Args:
            dialect: The SQL dialect instance.
            json_column: The column or expression containing the JSON data.
            path: The JSON path expression to extract rows.
            columns: A list of JSONTableColumn definitions for the output columns.
            alias: The alias for the resulting table.
        """
        super().__init__(dialect, name="JSON_TABLE", alias=alias)
        self.json_column = json_column
        self.path = path
        self.columns = columns

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to dialect for JSON_TABLE statement formatting
        
        if isinstance(self.json_column, BaseExpression):
            json_col_sql, json_col_params = self.json_column.to_sql()
        else:
            json_col_sql = self.dialect.format_identifier(self.json_column)
            json_col_params = ()
        
        # Prepare columns for the dialect
        prepared_columns = []
        for col in self.columns:
            prepared_columns.append({
                "name": self.dialect.format_identifier(col.name),
                "type": col.data_type, # Type is a string
                "path": col.path
            })

        return self.dialect.format_json_table_expression(
            json_col_sql,
            self.path,
            prepared_columns,
            self.alias,
            json_col_params
        )
