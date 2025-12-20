# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.
"""
from typing import Any, List, Optional, Tuple, Dict, Union, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
)
from rhosocial.activerecord.backend.expression.statements import (
    MergeActionType, ValuesSource, SelectSource, DefaultValuesSource, QueryExpression,
    ExplainType, ExplainFormat, ExplainOptions,  # For handling EXPLAIN functionality
    ColumnConstraintType, TableConstraintType, ForUpdateClause  # For handling new features
)
from rhosocial.activerecord.backend.expression import bases
from rhosocial.activerecord.backend.expression.bases import BaseExpression # Added this import

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
        MergeExpression, ExplainExpression, CreateTableExpression,
        DropTableExpression, AlterTableExpression, OnConflictClause,
        ReturningClause  # Added ReturningClause import
    )
    from rhosocial.activerecord.backend.expression.advanced_functions import (
        WindowFrameSpecification, WindowSpecification, WindowDefinition,
        WindowClause, WindowFunctionCall
    )
    # from rhosocial.activerecord.backend.expression.bases import BaseExpression # Removed, as it's now imported directly


class DummyDialect(
    BaseDialect,
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    # region Core & General
    def get_placeholder(self) -> str:
        """Use '?' placeholder for consistency."""
        return "?"
    # endregion

    # region Protocol Support Checks
    def supports_window_functions(self) -> bool: return True
    def supports_window_frame_clause(self) -> bool: return True
    def supports_basic_cte(self) -> bool: return True
    def supports_recursive_cte(self) -> bool: return True
    def supports_materialized_cte(self) -> bool: return True
    def supports_rollup(self) -> bool: return True
    def supports_cube(self) -> bool: return True
    def supports_grouping_sets(self) -> bool: return True
    def supports_returning_clause(self) -> bool: return True
    def supports_upsert(self) -> bool: return True
    def get_upsert_syntax_type(self) -> str: return "ON CONFLICT"
    def supports_lateral_join(self) -> bool: return True
    def supports_array_type(self) -> bool: return True
    def supports_array_constructor(self) -> bool: return True
    def supports_array_access(self) -> bool: return True
    def supports_json_type(self) -> bool: return True
    def get_json_access_operator(self) -> str: return "->"
    def supports_json_table(self) -> bool: return True
    def supports_explain_analyze(self) -> bool: return True
    def supports_explain_format(self, format_type: str) -> bool: return True
    def supports_filter_clause(self) -> bool: return True
    def supports_ordered_set_aggregation(self) -> bool: return True
    def supports_merge_statement(self) -> bool: return True
    def supports_temporal_tables(self) -> bool: return True
    def supports_qualify_clause(self) -> bool: return True
    def supports_for_update_skip_locked(self) -> bool: return True
    def supports_graph_match(self) -> bool: return True
    # endregion

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
            where_sql = f" WHERE {where_expr_sql}"
            all_params.extend(where_expr_params)
        group_by_sql = ""
        if expr.group_by:
            group_by_parts = [e.to_sql()[0] for e in expr.group_by]
            all_params.extend([p for e in expr.group_by for p in e.to_sql()[1]])
            group_by_sql = f" GROUP BY {', '.join(group_by_parts)}"
        having_sql = ""
        if expr.having:
            having_expr_sql, having_expr_params = expr.having.to_sql()
            having_sql = f" HAVING {having_expr_sql}"
            all_params.extend(having_expr_params)
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
        qualify_sql = ""
        if expr.qualify:
            qualify_expr_sql, qualify_expr_params = expr.qualify.to_sql()
            qualify_sql = f" QUALIFY {qualify_expr_sql}"
            all_params.extend(qualify_expr_params)

        # Build initial SQL without FOR UPDATE
        sql = f"{select_sql}{from_sql}{where_sql}{group_by_sql}{having_sql}{order_by_sql}{qualify_sql}"

        # Add FOR UPDATE clause at the end (if present)
        if expr.for_update:
            for_update_sql, for_update_params = expr.for_update.to_sql()
            if for_update_sql:
                sql += f" {for_update_sql}"
                all_params.extend(for_update_params)

        limit_offset_sql, limit_offset_params = self.format_limit_offset(expr.limit, expr.offset)
        if limit_offset_sql:
            sql += " " + limit_offset_sql
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
            def _format_single_from_source(source: Union["BaseExpression", str]) -> Tuple[str, List[Any]]:
                if isinstance(source, str):
                    return self.format_identifier(source), []
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql() # Get bare SQL
                    return f"({s_sql})", s_params # Add parentheses
                if isinstance(source, BaseExpression): # Explicitly check for BaseExpression
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
            current_sql += f" WHERE {where_sql}" # Append directly with leading space
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
            def _format_single_from_source(source: Union["BaseExpression", str]) -> Tuple[str, List[Any]]:
                if isinstance(source, str):
                    return self.format_identifier(source), []
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql() # Get bare SQL
                    return f"({s_sql})", s_params # Add parentheses
                if isinstance(source, BaseExpression):
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
                all_params.extend(from_expr_params)

        # WHERE clause
        if expr.where:
            where_sql, where_params = expr.where.to_sql()
            current_sql += f" WHERE {where_sql}"
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

    def format_qualify_clause(self, qualify_sql: str, qualify_params: tuple) -> Tuple[str, Tuple]:
        return f"QUALIFY {qualify_sql}", qualify_params

    def format_for_update_clause(self, clause: "ForUpdateClause") -> Tuple[str, tuple]:
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
                if isinstance(part, BaseExpression):
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
                    if isinstance(expr, BaseExpression):
                        expr_sql, expr_params = expr.to_sql()
                        order_by_parts.append(f"{expr_sql} {direction.upper()}")
                        all_params.extend(expr_params)
                    else:
                        order_by_parts.append(f"{self.format_identifier(str(expr))} {direction.upper()}")
                else:
                    if isinstance(item, BaseExpression):
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
            if isinstance(arg, BaseExpression):
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

    def format_match_clause(self, path_sql: List[str], path_params: tuple) -> Tuple[str, tuple]:
        return f"MATCH {' '.join(path_sql)}", path_params

    def format_temporal_options(self, options: Dict[str, Any]) -> Tuple[str, tuple]:
        if not options: return "", ()
        sql_parts, params = ["FOR SYSTEM_TIME"], []
        if "as_of" in options:
            sql_parts.append("AS OF ?")
            params.append(options["as_of"])
        elif "from" in options and "to" in options:
            sql_parts.append("FROM ? TO ?")
            params.extend([options["from"], options["to"]])
        elif "between" in options and "and" in options:
            sql_parts.append("BETWEEN ? AND ?")
            params.extend([options["between"], options["and"]])
        return " ".join(sql_parts), tuple(params)
    # endregion

    # region Expression & Predicate Formatting
    def format_json_table_expression(self, json_col_sql: str, path: str, columns: List[Dict[str, Any]], alias: str, params: tuple) -> Tuple[str, Tuple]:
        cols_defs = [f"{col['name']} {col['type']} PATH '{col['path']}'" for col in columns]
        columns_sql = f"COLUMNS({', '.join(cols_defs)})"
        sql = f"JSON_TABLE({json_col_sql}, '{path}' {columns_sql}) AS {self.format_identifier(alias)}"
        return sql, params

    def format_ordered_set_aggregation(self, func_name: str, func_args_sql: List[str], func_args_params: tuple, order_by_sql: List[str], order_by_params: tuple, alias: Optional[str] = None) -> Tuple[str, Tuple]:
        all_params = list(func_args_params) + list(order_by_params)
        func_part = f"{func_name.upper()}({', '.join(func_args_sql)})"
        order_by_part = f"WITHIN GROUP (ORDER BY {', '.join(order_by_sql)})"
        sql = f"{func_part} {order_by_part}"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, tuple(all_params)
    # endregion



