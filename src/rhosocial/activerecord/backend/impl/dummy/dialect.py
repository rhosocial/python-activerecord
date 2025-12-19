# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.
"""
from typing import Any, List, Optional, Tuple, Dict, Union, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.options import ExplainType
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
)
from rhosocial.activerecord.backend.expression.statements import (
    MergeActionType, ValuesSource, SelectSource, DefaultValuesSource, QueryExpression, QueryExpression
)
from rhosocial.activerecord.backend.expression.bases import BaseExpression # Added this import

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
        MergeExpression, ExplainExpression, CreateTableExpression,
        DropTableExpression, AlterTableExpression, OnConflictClause
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
        if options.type == ExplainType.ANALYZE: parts.append("ANALYZE")
        elif options.type == ExplainType.QUERYPLAN: parts.append("QUERY PLAN")
        parts.append(f"FORMAT {options.format.value.upper()}")
        if options.costs: parts.append("COSTS ON")
        if options.buffers: parts.append("BUFFERS")
        if options.timing and options.type == ExplainType.ANALYZE: parts.append("TIMING ON")
        if options.verbose: parts.append("VERBOSE")
        if options.settings: parts.append("SETTINGS")
        if options.wal: parts.append("WAL")

        return f"{ ' '.join(parts)} {statement_sql}", statement_params

    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        return f"CREATE TABLE {self.format_identifier(expr.table_name)} (...)", ()

    def format_drop_table_statement(self, expr: "DropTableExpression") -> Tuple[str, tuple]:
        return f"DROP TABLE {self.format_identifier(expr.table_name)}", ()

    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        return f"ALTER TABLE {self.format_identifier(expr.table_name)} ...", ()
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

    def format_returning_clause(self, expressions: List["BaseExpression"]) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        cols_sql = []
        for expr in expressions:
            sql, params = expr.to_sql()
            cols_sql.append(sql)
            all_params.extend(params)
        return f"RETURNING {', '.join(cols_sql)}", tuple(all_params)

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



