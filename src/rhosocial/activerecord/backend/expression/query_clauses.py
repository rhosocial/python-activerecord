# src/rhosocial/activerecord/backend/expression_/query_clauses.py
"""
Expressions related to SQL query clauses such as SET operations, GROUPING, JOINs, and CTEs.
"""
from typing import Tuple, Any, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
from . import bases
from . import core
from . import mixins

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase
    from .statements import QueryExpression


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
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()
        all_str = " ALL" if self.all else ""
        sql = f"{left_sql} {self.operation}{all_str} {right_sql}"
        params = left_params + right_params
        return f"({sql}) AS {self.dialect.format_identifier(self.alias)}", tuple(params)


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


class GroupExpression(bases.BaseExpression):
    """Represents a GROUP BY expression."""
    def __init__(self, dialect: "SQLDialectBase", expressions: List["bases.BaseExpression"]):
        super().__init__(dialect)
        self.expressions = expressions

    def to_sql(self) -> Tuple[str, tuple]:
        expr_parts = [expr.to_sql()[0] for expr in self.expressions]
        all_params = [p for expr in self.expressions for p in expr.to_sql()[1]]
        return f"GROUP BY {', '.join(expr_parts)}", tuple(all_params)


class JoinExpression(bases.BaseExpression):
    """Represents a JOIN expression (e.g., table1 JOIN table2 ON condition)."""
    def __init__(self, dialect: "SQLDialectBase",
                 left_table: Union[str, "core.TableExpression", "core.Subquery", "QueryExpression"],
                 right_table: Union[str, "core.TableExpression", "core.Subquery", "QueryExpression"],
                 alias: Optional[str] = None, join_type: str = "INNER",
                 condition: Optional["bases.SQLPredicate"] = None, natural: bool = False,
                 using: Optional[List[str]] = None):
        super().__init__(dialect)
        self.left_table, self.right_table = left_table, right_table
        self.join_type, self.condition, self.natural, self.using, self.alias = join_type, condition, natural, using, alias

    def _build_base_join_sql(self) -> Tuple[str, tuple]:
        left = self.left_table if not isinstance(self.left_table, str) else core.TableExpression(self.dialect, self.left_table)
        left_sql, left_params = left.to_sql()
        right = self.right_table if not isinstance(self.right_table, str) else core.TableExpression(self.dialect, self.right_table)
        right_sql, right_params = right.to_sql()

        join_type_upper = self.join_type.upper()
        
        join_phrase = ""
        if join_type_upper == "CROSS":
            join_phrase = "CROSS JOIN"
        elif join_type_upper in ["INNER", "LEFT", "RIGHT", "FULL"]:
            join_phrase = f"{join_type_upper}"
            if join_type_upper in ["LEFT", "RIGHT", "FULL"]:
                join_phrase += " OUTER"
            join_phrase += " JOIN"
        else:
            join_phrase = f"{join_type_upper} JOIN" # Fallback for custom/unrecognized types

        if self.natural:
            join_phrase = f"NATURAL {join_phrase}"

        all_params: List[Any] = list(left_params) + list(right_params)
        
        if self.using:
            using_cols = [self.dialect.format_identifier(col) for col in self.using]
            sql = f"{left_sql} {join_phrase} {right_sql} USING ({', '.join(using_cols)})"
        elif self.condition:
            condition_sql, condition_params = self.condition.to_sql()
            sql = f"{left_sql} {join_phrase} {right_sql} ON {condition_sql}"
            all_params.extend(condition_params)
        else:
            sql = f"{left_sql} {join_phrase} {right_sql}"
        return sql, tuple(all_params)

    def to_sql(self) -> Tuple[str, tuple]:
        return self._build_base_join_sql()


class CTEExpression(bases.BaseExpression):
    """Represents a Common Table Expression (CTE) expression (WITH ... AS ...)."""
    def __init__(self, dialect: "SQLDialectBase", name: str,
                 query: Union["core.Subquery", "bases.BaseExpression", Tuple[str, List[Any]]],
                 columns: Optional[List[str]] = None, recursive: bool = False, materialized: Optional[bool] = None):
        super().__init__(dialect)
        self.name, self.query, self.columns, self.recursive, self.materialized = name, query, columns, recursive, materialized

    def to_sql(self) -> Tuple[str, tuple]:
        if isinstance(self.query, bases.BaseExpression):
            query_sql, query_params = self.query.to_sql()
        elif isinstance(self.query, tuple):
            query_sql, query_params = self.query[0], tuple(self.query[1])
        else:
            query_sql, query_params = str(self.query), ()
        sql = self.dialect.format_cte(name=self.name, query_sql=query_sql, columns=self.columns, recursive=self.recursive, materialized=self.materialized)
        return sql, query_params


class WithQueryExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a query with Common Table Expressions (WITH clause)."""
    def __init__(self, dialect: "SQLDialectBase", ctes: List[CTEExpression], main_query: "bases.BaseExpression"):
        super().__init__(dialect)
        self.ctes, self.main_query = ctes, main_query

    def to_sql(self) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        cte_sql_parts = []
        for cte in self.ctes:
            cte_sql, cte_params = cte.to_sql()
            cte_sql_parts.append(cte_sql)
            all_params.extend(cte_params)
        with_clause_sql = self.dialect.format_with_clause(cte_sql_parts)
        main_sql, main_params = self.main_query.to_sql()
        all_params.extend(main_params)
        sql = f"{with_clause_sql} {main_sql}" if with_clause_sql else main_sql
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
    def __init__(self, dialect: "SQLDialectBase", expression: Union["core.Subquery", TableFunctionExpression], alias: str, join_type: str = "CROSS"):
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
