# src/rhosocial/activerecord/backend/expression_/statements.py
"""
SQL DML (Data Manipulation Language) and DQL (Data Query Language) statements.
"""
from typing import Tuple, Any, List, Optional, Dict, Union, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field

from . import bases
from . import core
from . import mixins

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase, ExplainOptions
#     from .query_clauses import SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression


class MergeActionType(Enum):
    """Represents the type of action to perform in a MERGE statement."""
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    DELETE = "DELETE"

@dataclass
class MergeAction:
    """
    Represents an action (UPDATE, INSERT, or DELETE) to be performed
    within a MERGE statement's WHEN clause.
    """
    action_type: MergeActionType
    assignments: Optional[Dict[str, "bases.BaseExpression"]] = field(default_factory=dict)
    values: Optional[List["bases.BaseExpression"]] = field(default_factory=list)
    condition: Optional["bases.SQLPredicate"] = None

class MergeExpression(bases.BaseExpression):
    """
    Represents a MERGE statement.
    """
    def __init__(self, dialect: "SQLDialectBase",
                 target_table: Union[str, "core.TableExpression"],
                 source: Union["core.Subquery", "core.TableExpression", "ValuesExpression"],
                 on_condition: "bases.SQLPredicate",
                 when_matched: Optional[List[MergeAction]] = None,
                 when_not_matched: Optional[List[MergeAction]] = None):
        super().__init__(dialect)
        self.target_table = target_table if isinstance(target_table, core.TableExpression) else core.TableExpression(dialect, target_table)
        self.source = source
        self.on_condition = on_condition
        self.when_matched = when_matched or []
        self.when_not_matched = when_not_matched or []

    def to_sql(self) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        target_sql, target_params = self.target_table.to_sql()
        all_params.extend(target_params)
        source_sql, source_params = self.source.to_sql()
        all_params.extend(source_params)
        on_sql, on_params = self.on_condition.to_sql()
        all_params.extend(on_params)

        prepared_when_matched = []
        for action in self.when_matched:
            action_params: List[Any] = []  # Reset for each action
            assignments_sql_and_params = []
            values_sql_and_params = []

            # Process condition parameters first to match the order of placeholders in SQL
            condition_sql_and_params = None
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                condition_sql_and_params = (cond_sql, cond_params)
                action_params.extend(cond_params)

            # Then process assignment and value parameters
            if action.assignments:
                for col, expr in action.assignments.items():
                    expr_sql, expr_params = expr.to_sql()
                    assignments_sql_and_params.append((col, expr_sql, expr_params))
                    action_params.extend(expr_params)
            if action.values:
                for expr in action.values:
                    expr_sql, expr_params = expr.to_sql()
                    values_sql_and_params.append((expr_sql, expr_params))
                    action_params.extend(expr_params)

            prepared_when_matched.append({
                "action_type": action.action_type, "assignments": assignments_sql_and_params,
                "values": values_sql_and_params, "condition": condition_sql_and_params,
                "params": tuple(action_params)
            })
            all_params.extend(action_params)

        prepared_when_not_matched = []
        for action in self.when_not_matched:
            action_params: List[Any] = []  # Reset for each action
            assignments_sql_and_params = []
            values_sql_and_params = []

            # Process condition parameters first to match the order of placeholders in SQL
            condition_sql_and_params = None
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                condition_sql_and_params = (cond_sql, cond_params)
                action_params.extend(cond_params)

            # Then process assignment and value parameters
            if action.assignments:
                for col, expr in action.assignments.items():
                    expr_sql, expr_params = expr.to_sql()
                    assignments_sql_and_params.append((col, expr_sql, expr_params))
                    action_params.extend(expr_params)
            if action.values:
                for expr in action.values:
                    expr_sql, expr_params = expr.to_sql()
                    values_sql_and_params.append((expr_sql, expr_params))
                    action_params.extend(expr_params)

            prepared_when_not_matched.append({
                "action_type": action.action_type, "assignments": assignments_sql_and_params,
                "values": values_sql_and_params, "condition": condition_sql_and_params,
                "params": tuple(action_params)
            })
            all_params.extend(action_params)

        return self.dialect.format_merge_statement(
            target_sql, source_sql, on_sql, prepared_when_matched, prepared_when_not_matched,
            target_params + source_params + on_params + tuple(all_params)
        )


class QueryExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a complete SELECT query expression with all clauses."""
    def __init__(self, dialect: "SQLDialectBase",
                 select: List["bases.BaseExpression"],
                 from_: Optional[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression", "bases.BaseExpression"]] = None,
                 where: Optional["bases.SQLPredicate"] = None,
                 group_by: Optional[List["bases.BaseExpression"]] = None,
                 having: Optional["bases.SQLPredicate"] = None,
                 order_by: Optional[List["bases.BaseExpression"]] = None,
                 qualify: Optional["bases.SQLPredicate"] = None,
                 limit: Optional[int] = None,
                 offset: Optional[int] = None,
                 for_update_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.select, self.from_, self.where, self.group_by, self.having = select or [], from_, where, group_by or [], having
        self.order_by, self.qualify, self.limit, self.offset, self.for_update_options = order_by or [], qualify, limit, offset, for_update_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        select_parts = []
        for expr in self.select:
            expr_sql, expr_params = expr.to_sql()
            select_parts.append(expr_sql)
            all_params.extend(expr_params)
        select_sql = "SELECT " + ", ".join(select_parts)
        from_sql = ""
        if self.from_:
            from_expr_sql, from_expr_params = self.from_.to_sql()
            from_sql = f" FROM {from_expr_sql}"
            all_params.extend(from_expr_params)
        where_sql = ""
        if self.where:
            where_expr_sql, where_expr_params = self.where.to_sql()
            where_sql = f" WHERE {where_expr_sql}"
            all_params.extend(where_expr_params)
        group_by_sql = ""
        if self.group_by:
            group_by_parts = [expr.to_sql()[0] for expr in self.group_by]
            all_params.extend([p for expr in self.group_by for p in expr.to_sql()[1]])
            group_by_sql = f" GROUP BY {', '.join(group_by_parts)}"
        having_sql = ""
        if self.having:
            having_expr_sql, having_expr_params = self.having.to_sql()
            having_sql = f" HAVING {having_expr_sql}"
            all_params.extend(having_expr_params)
        order_by_sql = ""
        if self.order_by:
            order_by_parts = []
            for item in self.order_by:
                if isinstance(item, tuple):
                    expr, direction = item
                    expr_sql, expr_params = expr.to_sql()
                    order_by_parts.append(f"{expr_sql} {direction.upper()}")
                    all_params.extend(expr_params)
                else:
                    expr_sql, expr_params = item.to_sql()
                    order_by_parts.append(expr_sql)
                    all_params.extend(expr_params)
            order_by_sql = f" ORDER BY {', '.join(order_by_parts)}"
        qualify_sql = ""
        if self.qualify:
            qualify_expr_sql, qualify_expr_params = self.qualify.to_sql()
            qualify_sql = f" QUALIFY {qualify_expr_sql}"
            all_params.extend(qualify_expr_params)
        sql = f"{select_sql}{from_sql}{where_sql}{group_by_sql}{having_sql}{order_by_sql}{qualify_sql}"
        if self.for_update_options:
            for_update_sql, for_update_params = self.dialect.format_for_update_clause(self.for_update_options)
            if for_update_sql:
                sql += f" {for_update_sql}"
                all_params.extend(for_update_params)
        limit_offset_sql, limit_offset_params = self.dialect.format_limit_offset(self.limit, self.offset)
        if limit_offset_sql:
            sql += " " + limit_offset_sql
            all_params.extend(limit_offset_params)
        return sql, tuple(all_params)


class DeleteExpression(bases.BaseExpression):
    """Represents a DELETE statement."""
    def __init__(self, dialect: "SQLDialectBase", table: str, where: Optional["bases.SQLPredicate"] = None):
        super().__init__(dialect)
        self.table, self.where = table, where

    def to_sql(self) -> Tuple[str, tuple]:
        table_sql = self.dialect.format_identifier(self.table)
        sql = f"DELETE FROM {table_sql}"
        all_params: List[Any] = []
        if self.where:
            where_sql, where_params = self.where.to_sql()
            sql += f" WHERE {where_sql}"
            all_params.extend(where_params)
        return sql, tuple(all_params)


class UpdateExpression(bases.BaseExpression):
    """Represents an UPDATE statement."""
    def __init__(self, dialect: "SQLDialectBase", table: str, assignments: Dict[str, "bases.BaseExpression"], where: Optional["bases.SQLPredicate"] = None):
        super().__init__(dialect)
        self.table, self.assignments, self.where = table, assignments, where

    def to_sql(self) -> Tuple[str, tuple]:
        table_sql = self.dialect.format_identifier(self.table)
        assignment_parts, all_params = [], []
        for col, expr in self.assignments.items():
            col_sql, expr_sql, expr_params = self.dialect.format_identifier(col), expr.to_sql()[0], expr.to_sql()[1]
            assignment_parts.append(f"{col_sql} = {expr_sql}")
            all_params.extend(expr_params)
        assignments_sql = ", ".join(assignment_parts)
        sql = f"UPDATE {table_sql} SET {assignments_sql}"
        if self.where:
            where_sql, where_params = self.where.to_sql()
            sql += f" WHERE {where_sql}"
            all_params.extend(where_params)
        return sql, tuple(all_params)


class InsertExpression(bases.BaseExpression):
    """
    Represents an SQL INSERT statement.

    This class supports various forms of the INSERT statement:
    1.  `INSERT INTO <table> (columns) VALUES (...)` for single or multi-row inserts.
    2.  `INSERT INTO <table> (columns) SELECT ... FROM ...` for inserting data from a subquery.
    3.  `INSERT INTO <table> DEFAULT VALUES` for inserting a row with default column values.

    It performs validation to ensure only one insertion method is specified at a time.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        columns: Optional[List[str]] = None,
        values_list: Optional[List[List["bases.BaseExpression"]]] = None,
        select_query: Optional["QueryExpression"] = None,
        default_values: bool = False,
    ):
        """
        Initializes an InsertExpression.

        Args:
            dialect: The SQL dialect to use for formatting.
            table: The name of the target table.
            columns: An optional list of column names for the insert. Required for VALUES and SELECT inserts,
                     optional for DEFAULT VALUES (though usually omitted).
            values_list: An optional list of lists of BaseExpression objects, where each inner list
                         represents a row of values to be inserted. Used for `INSERT ... VALUES`.
            select_query: An optional QueryExpression object representing a SELECT subquery
                          whose results are to be inserted. Used for `INSERT ... SELECT`.
            default_values: A boolean flag indicating whether to use `DEFAULT VALUES` clause.
                            Used for `INSERT ... DEFAULT VALUES`.

        Raises:
            ValueError: If an invalid combination of insertion methods is provided.
        """
        super().__init__(dialect)
        self.table = table
        self.columns = columns

        # Validate that only one insertion method is provided
        provided_methods = sum([
            1 if values_list is not None else 0,
            1 if select_query is not None else 0,
            1 if default_values else 0,
        ])
        if provided_methods > 1:
            raise ValueError(
                "Only one of 'values_list', 'select_query', or 'default_values' "
                "can be provided for an INSERT statement."
            )
        # Ensure that at least one insertion method or columns for a SELECT subquery are provided.
        # This handles cases like INSERT INTO tbl (col1) SELECT ... where columns is provided
        # but no direct insertion method.
        if provided_methods == 0 and not columns:
            raise ValueError(
                "At least one of 'values_list', 'select_query', or 'default_values' "
                "must be provided for an INSERT statement, or columns must be specified "
                "for a SELECT subquery."
            )

        self.values_list = values_list
        self.select_query = select_query
        self.default_values = default_values

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generates the SQL string and parameters for the INSERT statement.

        Returns:
            A tuple containing the formatted SQL string and a tuple of parameters.

        Raises:
            ValueError: If the InsertExpression is in an invalid state, e.g., using DEFAULT VALUES
                        with other insertion methods, or a SELECT/VALUES insert without columns.
        """
        table_sql = self.dialect.format_identifier(self.table)
        all_params: List[Any] = []

        columns_sql = ""
        if self.columns:
            columns_sql = "(" + ", ".join([self.dialect.format_identifier(c) for c in self.columns]) + ")"

        # Handle INSERT ... DEFAULT VALUES
        if self.default_values:
            if self.columns or self.values_list or self.select_query:
                raise ValueError(
                    "Cannot use 'DEFAULT VALUES' with 'columns', 'values_list', or 'select_query'."
                )
            sql = f"INSERT INTO {table_sql} DEFAULT VALUES"
            return sql, tuple(all_params)

        # Handle INSERT ... SELECT
        if self.select_query:
            if not self.columns:
                 raise ValueError("Columns must be specified when using 'select_query' for INSERT.")
            select_sql, select_params = self.select_query.to_sql()
            all_params.extend(select_params)
            sql = f"INSERT INTO {table_sql} {columns_sql} {select_sql}"
            return sql, tuple(all_params)

        # Handle INSERT ... VALUES (single or multi-row)
        if self.values_list is not None:
            if not self.columns:
                raise ValueError("Columns must be specified when using 'values_list' for INSERT.")

            all_rows_sql_parts = []
            for row_values in self.values_list:
                row_values_sql_parts = []
                for value_expr in row_values:
                    value_sql, value_params = value_expr.to_sql()
                    row_values_sql_parts.append(value_sql)
                    all_params.extend(value_params)
                all_rows_sql_parts.append("(" + ", ".join(row_values_sql_parts) + ")")
            
            values_clause = "VALUES " + ", ".join(all_rows_sql_parts)
            sql = f"INSERT INTO {table_sql} {columns_sql} {values_clause}"
            return sql, tuple(all_params)
        
        # This fallback covers the scenario where provided_methods == 0 but columns were specified.
        # This typically implies an INSERT ... SELECT where select_query was not directly passed
        # but implied (e.g., from a higher-level query builder that will inject it).
        # However, for a standalone InsertExpression, this is an invalid state.
        if self.columns:
            raise ValueError("No insertion data (values_list, select_query, default_values) provided despite columns being specified.")



class ExplainExpression(bases.BaseExpression):
    """Represents an EXPLAIN statement."""
    def __init__(self, dialect: "SQLDialectBase",
                 statement: Union[QueryExpression, InsertExpression, UpdateExpression, DeleteExpression],
                 options: Optional["ExplainOptions"] = None):
        super().__init__(dialect)
        self.statement, self.options = statement, options

    def to_sql(self) -> Tuple[str, tuple]:
        statement_sql, statement_params = self.statement.to_sql()
        explain_sql = self.dialect.format_explain(statement_sql, self.options)
        return explain_sql, statement_params