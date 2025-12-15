# src/rhosocial/activerecord/backend/expression/statements.py
"""
SQL DML (Data Manipulation Language) and DQL (Data Query Language) statements.
"""
from typing import Tuple, Any, List, Optional, Dict, Union, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field
from .base import BaseExpression, SQLPredicate
from .core import Subquery, TableExpression # Import Subquery and TableExpression
from ..dialect import SQLDialectBase, ExplainOptions

# Imported for type hinting
if TYPE_CHECKING:
    from .query_clauses import SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression


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
    assignments: Optional[Dict[str, BaseExpression]] = field(default_factory=dict) # For UPDATE
    values: Optional[List[BaseExpression]] = field(default_factory=list) # For INSERT
    condition: Optional[SQLPredicate] = None # Optional condition for WHEN clause (e.g., WHEN MATCHED AND condition THEN ...)

class MergeExpression(BaseExpression):
    """
    Represents a MERGE statement.
    """
    def __init__(self, dialect: SQLDialectBase,
                 target_table: Union[str, TableExpression],
                 source: Union[Subquery, TableExpression, ValuesExpression],
                 on_condition: SQLPredicate,
                 when_matched: Optional[List[MergeAction]] = None,
                 when_not_matched: Optional[List[MergeAction]] = None):
        """
        Initializes a MERGE expression.

        Args:
            dialect: The SQL dialect instance.
            target_table: The target table for the MERGE operation.
            source: The source data for matching.
            on_condition: The condition to match rows between target and source.
            when_matched: List of actions to perform when rows are matched.
            when_not_matched: List of actions to perform when rows are not matched.
        """
        super().__init__(dialect)
        self.target_table = target_table if isinstance(target_table, TableExpression) else TableExpression(dialect, target_table)
        self.source = source
        self.on_condition = on_condition
        self.when_matched = when_matched or []
        self.when_not_matched = when_not_matched or []

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to dialect for MERGE statement formatting
        all_params: List[Any] = []

        target_sql, target_params = self.target_table.to_sql()
        all_params.extend(target_params)

        source_sql, source_params = self.source.to_sql()
        all_params.extend(source_params)

        on_sql, on_params = self.on_condition.to_sql()
        all_params.extend(on_params)

        # Prepare matched actions
        prepared_when_matched = []
        action_params: List[Any] = [] # Initialize once
        for action in self.when_matched:
            assignments_sql_and_params = []
            values_sql_and_params = []
            
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

            condition_sql_and_params = None
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                condition_sql_and_params = (cond_sql, cond_params)
                action_params.extend(cond_params)

            prepared_when_matched.append({
                "action_type": action.action_type,
                "assignments": assignments_sql_and_params,
                "values": values_sql_and_params,
                "condition": condition_sql_and_params,
                "params": tuple(action_params)
            })
            all_params.extend(action_params)

        # Prepare not matched actions
        prepared_when_not_matched = []
        # action_params already initialized above, just extend
        for action in self.when_not_matched:
            assignments_sql_and_params = [] # Not applicable for INSERT or DELETE, but keep for consistency
            values_sql_and_params = []

            if action.assignments: # Not typical for WHEN NOT MATCHED (usually INSERT)
                for col, expr in action.assignments.items():
                    expr_sql, expr_params = expr.to_sql()
                    assignments_sql_and_params.append((col, expr_sql, expr_params))
                    action_params.extend(expr_params)

            if action.values:
                for expr in action.values:
                    expr_sql, expr_params = expr.to_sql()
                    values_sql_and_params.append((expr_sql, expr_params))
                    action_params.extend(expr_params)

            condition_sql_and_params = None
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                condition_sql_and_params = (cond_sql, cond_params)
                action_params.extend(cond_params)

            prepared_when_not_matched.append({
                "action_type": action.action_type,
                "assignments": assignments_sql_and_params,
                "values": values_sql_and_params,
                "condition": condition_sql_and_params,
                "params": tuple(action_params)
            })
            all_params.extend(action_params)


        return self.dialect.format_merge_statement(
            target_sql,
            source_sql,
            on_sql,
            prepared_when_matched,
            prepared_when_not_matched,
            target_params + source_params + on_params + tuple(all_params)
        )


class QueryExpression(BaseExpression):
    """
    Represents a complete SELECT query expression with all clauses.
    """
    def __init__(self, dialect: SQLDialectBase,
                 select: List[BaseExpression],
                 from_: Optional[Union[TableExpression, Subquery, SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression, BaseExpression]] = None,
                 where: Optional[SQLPredicate] = None,
                 group_by: Optional[List[BaseExpression]] = None,
                 having: Optional[SQLPredicate] = None,
                 order_by: Optional[List[BaseExpression]] = None,
                 qualify: Optional[SQLPredicate] = None,
                 limit: Optional[int] = None,
                 offset: Optional[int] = None,
                 for_update_options: Optional[Dict[str, Any]] = None):
        """
        Initializes a query expression.

        Args:
            dialect: The SQL dialect instance.
            select: List of SELECT expressions.
            from_: FROM clause expression (table or subquery).
            where: WHERE clause predicate.
            group_by: GROUP BY expressions.
            having: HAVING clause predicate.
            order_by: ORDER BY expressions.
            qualify: QUALIFY clause predicate.
            limit: LIMIT value.
            offset: OFFSET value.
            for_update_options: Options for FOR UPDATE/FOR SHARE clauses (e.g., {'skip_locked': True}).
        """
        super().__init__(dialect)
        self.select = select or []
        self.from_ = from_
        self.where = where
        self.group_by = group_by or []
        self.having = having
        self.order_by = order_by or []
        self.qualify = qualify
        self.limit = limit
        self.offset = offset
        self.for_update_options = for_update_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        all_params: List[Any] = []

        # SELECT clause
        select_parts = []
        for expr in self.select:
            expr_sql, expr_params = expr.to_sql()
            select_parts.append(expr_sql)
            all_params.extend(expr_params)
        select_sql = "SELECT " + ", ".join(select_parts)

        # FROM clause
        from_sql = ""
        if self.from_:
            from_expr_sql, from_expr_params = self.from_.to_sql()
            from_sql = f" FROM {from_expr_sql}"
            all_params.extend(from_expr_params)

        # WHERE clause
        where_sql = ""
        if self.where:
            where_expr_sql, where_expr_params = self.where.to_sql()
            where_sql = f" WHERE {where_expr_sql}"
            all_params.extend(where_expr_params)

        # GROUP BY clause
        group_by_sql = ""
        if self.group_by:
            group_by_parts = []
            for expr in self.group_by:
                expr_sql, expr_params = expr.to_sql()
                group_by_parts.append(expr_sql)
                all_params.extend(expr_params)
            group_by_sql = f" GROUP BY {', '.join(group_by_parts)}"

        # HAVING clause
        having_sql = ""
        if self.having:
            having_expr_sql, having_expr_params = self.having.to_sql()
            having_sql = f" HAVING {having_expr_sql}"
            all_params.extend(having_expr_params)

        # ORDER BY clause
        order_by_sql = ""
        if self.order_by:
            order_by_parts = []
            for expr in self.order_by:
                expr_sql, expr_params = expr.to_sql()
                order_by_parts.append(expr_sql)
                all_params.extend(expr_params)
            order_by_sql = f" ORDER BY {', '.join(order_by_parts)}"

        # QUALIFY clause
        qualify_sql = ""
        if self.qualify:
            qualify_expr_sql, qualify_expr_params = self.qualify.to_sql()
            qualify_sql = f" QUALIFY {qualify_expr_sql}"
            all_params.extend(qualify_expr_params)

        # Build the main query string without LIMIT/OFFSET yet
        sql_parts = [select_sql, from_sql, where_sql, group_by_sql, having_sql, order_by_sql, qualify_sql]
        sql = "".join(sql_parts)

        # FOR UPDATE clause (comes after all main clauses)
        for_update_sql = ""
        if self.for_update_options:
            for_update_sql, for_update_params = self.dialect.format_for_update_clause(self.for_update_options)
            all_params.extend(for_update_params)
            if for_update_sql:
                sql += f" {for_update_sql}"

        # LIMIT and OFFSET clauses (always last)
        limit_offset_sql, limit_offset_params = self.dialect.format_limit_offset(self.limit, self.offset)
        if limit_offset_sql:
            sql += " " + limit_offset_sql
            all_params.extend(limit_offset_params)

        return sql, tuple(all_params)


class DeleteExpression(BaseExpression):
    """
    Represents a DELETE statement.
    """
    def __init__(self, dialect: SQLDialectBase,
                 table: str,
                 where: Optional[SQLPredicate] = None):
        """
        Initializes a DELETE expression.

        Args:
            dialect: The SQL dialect instance.
            table: The table name to delete from.
            where: WHERE clause predicate (if None, deletes all rows).
        """
        super().__init__(dialect)
        self.table = table
        self.where = where

    def to_sql(self) -> Tuple[str, tuple]:
        table_sql = self.dialect.format_identifier(self.table)
        sql = f"DELETE FROM {table_sql}"

        all_params: List[Any] = []
        if self.where:
            where_sql, where_params = self.where.to_sql()
            sql += f" WHERE {where_sql}"
            all_params.extend(where_params)

        return sql, tuple(all_params)


class UpdateExpression(BaseExpression):
    """
    Represents an UPDATE statement.
    """
    def __init__(self, dialect: SQLDialectBase,
                 table: str,
                 assignments: Dict[str, BaseExpression],
                 where: Optional[SQLPredicate] = None):
        """
        Initializes an UPDATE expression.

        Args:
            dialect: The SQL dialect instance.
            table: The table name to update.
            assignments: Dictionary mapping column names to expressions for assignment.
            where: WHERE clause predicate (if None, updates all rows).
        """
        super().__init__(dialect)
        self.table = table
        self.assignments = assignments
        self.where = where

    def to_sql(self) -> Tuple[str, tuple]:
        table_sql = self.dialect.format_identifier(self.table)

        assignment_parts = []
        all_params: List[Any] = []

        for col, expr in self.assignments.items():
            col_sql = self.dialect.format_identifier(col)
            expr_sql, expr_params = expr.to_sql()
            assignment_parts.append(f"{col_sql} = {expr_sql}")
            all_params.extend(expr_params)

        assignments_sql = ", ".join(assignment_parts)
        sql = f"UPDATE {table_sql} SET {assignments_sql}"

        if self.where:
            where_sql, where_params = self.where.to_sql()
            sql += f" WHERE {where_sql}"
            all_params.extend(where_params)

        return sql, tuple(all_params)


class InsertExpression(BaseExpression):
    """
    Represents an INSERT statement.
    """
    def __init__(self, dialect: SQLDialectBase,
                 table: str,
                 columns: List[str],
                 values: List[BaseExpression]):
        """
        Initializes an INSERT expression.

        Args:
            dialect: The SQL dialect instance.
            table: The table name to insert into.
            columns: List of column names.
            values: List of expression values for each row.
        """
        super().__init__(dialect)
        self.table = table
        self.columns = columns
        self.values = values

    def to_sql(self) -> Tuple[str, tuple]:
        table_sql = self.dialect.format_identifier(self.table)

        column_parts = [self.dialect.format_identifier(col) for col in self.columns]
        columns_sql = "(" + ", ".join(column_parts) + ")"

        values_parts = []
        all_params: List[Any] = []

        for value_expr in self.values:
            value_sql, value_params = value_expr.to_sql()
            values_parts.append(value_sql)
            all_params.extend(value_params)

        values_sql = "(" + ", ".join(values_parts) + ")"

        sql = f"INSERT INTO {table_sql} {columns_sql} VALUES {values_sql}"
        return sql, tuple(all_params)


class ExplainExpression(BaseExpression):
    """
    Represents an EXPLAIN statement. This is a top-level expression
    that wraps a DQL/DML statement to generate its execution plan.
    """
    def __init__(self, dialect: SQLDialectBase,
                 statement: Union["QueryExpression", "InsertExpression", "UpdateExpression", "DeleteExpression"],
                 options: Optional["ExplainOptions"] = None):
        """
        Initializes an EXPLAIN expression.

        Args:
            dialect: The SQL dialect instance.
            statement: The DQL/DML statement to explain. Must be a top-level expression.
            options: Configuration for EXPLAIN output.
        """
        super().__init__(dialect)
        self.statement = statement
        self.options = options

    def to_sql(self) -> Tuple[str, tuple]:
        statement_sql, statement_params = self.statement.to_sql()
        explain_sql = self.dialect.format_explain(statement_sql, self.options)
        return explain_sql, statement_params
