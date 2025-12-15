# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.
"""
from typing import Any, List, Optional, Tuple, Dict

from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport,
    CTESupport,
    AdvancedGroupingSupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    ArraySupport,
    JSONSupport,
    ExplainSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
)
from rhosocial.activerecord.backend.expression.statements import MergeActionType, MergeAction, MergeExpression
from rhosocial.activerecord.backend.expression.advanced_functions import OrderedSetAggregation
from rhosocial.activerecord.backend.expression.graph import GraphVertex, GraphEdge, MatchClause, GraphEdgeDirection


class DummyDialect(
    BaseDialect,
    WindowFunctionSupport,
    CTESupport,
    AdvancedGroupingSupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    ArraySupport,
    JSONSupport,
    ExplainSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
):
    """
    Dummy dialect supporting all features.

    This dialect is used for SQL generation testing and validates query
    building logic without requiring an actual database connection.
    It implements all protocols and returns True for all feature checks.
    """

    def get_placeholder(self) -> str:
        """Use '?' placeholder for consistency."""
        return "?"

    def supports_window_functions(self) -> bool:
        """Window functions are supported."""
        return True

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported."""
        return True

    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported."""
        return True

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported."""
        return True

    def supports_materialized_cte(self) -> bool:
        """Materialized CTEs are supported."""
        return True

    def supports_rollup(self) -> bool:
        """ROLLUP is supported."""
        return True

    def supports_cube(self) -> bool:
        """CUBE is supported."""
        return True

    def supports_grouping_sets(self) -> bool:
        """GROUPING SETS are supported."""
        return True

    def supports_returning_clause(self) -> bool:
        """RETURNING clause is supported."""
        return True

    def format_returning_clause(
        self,
        columns: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format RETURNING clause.

        Args:
            columns: List of column names

        Returns:
            Tuple of (SQL string, empty parameters tuple)
        """
        cols = [self.format_identifier(c) for c in columns]
        return f"RETURNING {', '.join(cols)}", ()

    def supports_upsert(self) -> bool:
        """UPSERT is supported."""
        return True

    def get_upsert_syntax_type(self) -> str:
        """Use PostgreSQL-style ON CONFLICT syntax."""
        return "ON CONFLICT"

    def supports_lateral_join(self) -> bool:
        """LATERAL joins are supported."""
        return True

    def supports_array_type(self) -> bool:
        """Array types are supported."""
        return True

    def supports_array_constructor(self) -> bool:
        """Array constructors are supported."""
        return True

    def supports_array_access(self) -> bool:
        """Array subscript access is supported."""
        return True

    def supports_json_type(self) -> bool:
        """JSON type is supported."""
        return True

    def get_json_access_operator(self) -> str:
        """Use '->' for JSON access."""
        return "->"

    def supports_json_table(self) -> bool:
        """JSON_TABLE is supported."""
        return True

    def format_json_table_expression(
        self,
        json_col_sql: str,
        path: str,
        columns: List[Dict[str, Any]],
        alias: str,
        params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a JSON_TABLE expression for DummyDialect.
        """
        cols_defs = []
        for col in columns:
            cols_defs.append(f"{col['name']} {col['type']} PATH '{col['path']}'")
        
        columns_sql = f"COLUMNS({', '.join(cols_defs)})"
        
        sql = f"JSON_TABLE({json_col_sql}, '{path}' {columns_sql}) AS {self.format_identifier(alias)}"
        
        return sql, params

    def supports_explain_analyze(self) -> bool:
        """EXPLAIN ANALYZE is supported."""
        return True

    def supports_explain_format(self, format_type: str) -> bool:
        """All EXPLAIN formats are supported."""
        return True

    def supports_filter_clause(self) -> bool:
        """FILTER clause is supported."""
        return True

    def format_filter_clause(
        self,
        condition_sql: str,
        condition_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format a FILTER (WHERE ...) clause.

        Args:
            condition_sql: SQL string for the WHERE condition.
            condition_params: Parameters for the WHERE condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        return f"FILTER (WHERE {condition_sql})", condition_params

    def supports_ordered_set_aggregation(self) -> bool:
        """Ordered-set aggregate functions are supported."""
        return True

    def format_ordered_set_aggregation(
        self,
        func_name: str,
        func_args_sql: List[str],
        func_args_params: tuple,
        order_by_sql: List[str],
        order_by_params: tuple,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Formats an ordered-set aggregate function call for DummyDialect.
        """
        all_params = list(func_args_params)
        all_params.extend(order_by_params)

        func_part = f"{func_name.upper()}({', '.join(func_args_sql)})"
        order_by_part = f"WITHIN GROUP (ORDER BY {', '.join(order_by_sql)})"

        sql = f"{func_part} {order_by_part}"

        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"

        return sql, tuple(all_params)

    def supports_merge_statement(self) -> bool:
        """MERGE statement is supported."""
        return True

    def format_merge_statement(
        self,
        target_sql: str,
        source_sql: str,
        on_sql: str,
        when_matched: List[Dict[str, Any]],
        when_not_matched: List[Dict[str, Any]],
        all_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a MERGE statement for DummyDialect.
        """
        merge_sql_parts = [
            f"MERGE INTO {target_sql}",
            f"USING {source_sql}",
            f"ON {on_sql}"
        ]

        for action_info in when_matched:
            action_type = action_info["action_type"]
            action_sql_parts = []
            
            if action_info["condition"]:
                cond_sql, _ = action_info["condition"]
                action_sql_parts.append(f"WHEN MATCHED AND {cond_sql}")
            else:
                action_sql_parts.append("WHEN MATCHED")

            if action_type == MergeActionType.UPDATE:
                assignments = ", ".join([f"{col} = {expr_sql}" for col, expr_sql, _ in action_info["assignments"]])
                action_sql_parts.append(f"THEN UPDATE SET {assignments}")
            elif action_type == MergeActionType.DELETE:
                action_sql_parts.append("THEN DELETE")
            
            merge_sql_parts.append(" ".join(action_sql_parts))

        for action_info in when_not_matched:
            action_type = action_info["action_type"]
            action_sql_parts = []

            if action_info["condition"]:
                cond_sql, _ = action_info["condition"]
                action_sql_parts.append(f"WHEN NOT MATCHED AND {cond_sql}")
            else:
                action_sql_parts.append("WHEN NOT MATCHED")

            if action_type == MergeActionType.INSERT:
                if action_info["assignments"]:
                    insert_cols = [self.format_identifier(col) for col, _, _ in action_info["assignments"]]
                    insert_vals = [expr_sql for _, expr_sql, _ in action_info["assignments"]]

                    if insert_cols and insert_vals:
                        action_sql_parts.append(f"THEN INSERT ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})")
                    else:
                        action_sql_parts.append(f"THEN INSERT DEFAULT VALUES")
            
            merge_sql_parts.append(" ".join(action_sql_parts))

        return " ".join(merge_sql_parts), all_params

    def supports_temporal_tables(self) -> bool:
        """Temporal tables are supported."""
        return True

    def format_temporal_options(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a temporal table clause for DummyDialect.
        """
        if not options:
            return "", ()

        sql_parts = ["FOR SYSTEM_TIME"]
        params = []
        
        if "as_of" in options:
            sql_parts.append("AS OF ?")
            params.append(options["as_of"])
        elif "from" in options and "to" in options:
            sql_parts.append("FROM ? TO ?")
            params.append(options["from"])
            params.append(options["to"])
        elif "between" in options and "and" in options:
            sql_parts.append("BETWEEN ? AND ?")
            params.append(options["between"])
            params.append(options["and"])
        
        return " ".join(sql_parts), tuple(params)

    def supports_qualify_clause(self) -> bool:
        """QUALIFY clause is supported."""
        return True

    def format_qualify_clause(
        self,
        qualify_sql: str,
        qualify_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a QUALIFY clause for DummyDialect.
        """
        return f"QUALIFY {qualify_sql}", qualify_params

    def supports_for_update_skip_locked(self) -> bool:
        """FOR UPDATE SKIP LOCKED is supported."""
        return True

    def format_for_update_clause(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE/FOR SHARE clause for DummyDialect.
        """
        if not options:
            return "", ()

        sql_parts = ["FOR UPDATE"]
        params = []

        if options.get("of"):
            of_tables = ", ".join([self.format_identifier(t) for t in options["of"]])
            sql_parts.append(f"OF {of_tables}")
        
        if options.get("nowait"):
            sql_parts.append("NOWAIT")
        elif options.get("skip_locked"):
            sql_parts.append("SKIP LOCKED")

        return " ".join(sql_parts), tuple(params)

    def supports_graph_match(self) -> bool:
        """Graph MATCH clause is supported."""
        return True

    def format_match_clause(
        self,
        path_sql: List[str],
        path_params: tuple
    ) -> Tuple[str, tuple]:
        """
        Formats a MATCH clause for DummyDialect.
        """
        return f"MATCH {' '.join(path_sql)}", path_params




if __name__ == "__main__":
    from rhosocial.activerecord.backend.expression import (
        Literal, Column, Identifier, FunctionCall, Subquery, TableExpression,
        ComparisonPredicate, LogicalPredicate, InPredicate, BetweenPredicate,
        IsNullPredicate, LikePredicate,
        BinaryExpression, UnaryExpression, RawSQLExpression, BinaryArithmeticExpression,
        CaseExpression, CastExpression, ExistsExpression, AnyExpression, AllExpression,
        WindowExpression, JSONExpression, ArrayExpression,
        SetOperationExpression, GroupingExpression, GroupExpression, JoinExpression,
        CTEExpression, WithQueryExpression, ValuesExpression, TableFunctionExpression,
        LateralExpression,
        QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
        ExplainExpression, SQLOperation, MergeExpression, MergeAction, OrderedSetAggregation,
        JSONTableExpression,
    )

    dialect = DummyDialect()


    def print_sql(description: str, sql: str, params: tuple):
        """Helper function to print SQL and parameters separately."""
        print(f"--- {description} ---")
        print(f"SQL: {sql}")
        if params:
            print(f"Parameters: {params}")
        print()


    # ========== Part 1: Basic Expressions ==========

    def demo_literals():
        """Demonstrate Literal expressions with various types."""
        print("=" * 70)
        print("LITERALS")
        print("=" * 70)
        print()

        lit = Literal(dialect, 42)
        sql, params = lit.to_sql()
        print_sql("Integer Literal", sql, params)

        lit = Literal(dialect, "hello world")
        sql, params = lit.to_sql()
        print_sql("String Literal", sql, params)

        lit = Literal(dialect, None)
        sql, params = lit.to_sql()
        print_sql("NULL Literal", sql, params)

        lit = Literal(dialect, [1, 2, 3])
        sql, params = lit.to_sql()
        print_sql("List Literal", sql, params)

        lit = Literal(dialect, 3.14159)
        sql, params = lit.to_sql()
        print_sql("Float Literal", sql, params)

        lit = Literal(dialect, True)
        sql, params = lit.to_sql()
        print_sql("Boolean Literal", sql, params)


    def demo_identifiers():
        """Demonstrate Identifier expressions."""
        print("=" * 70)
        print("IDENTIFIERS")
        print("=" * 70)
        print()

        ident = Identifier(dialect, "table_name")
        sql, params = ident.to_sql()
        print_sql("Simple Identifier", sql, params)

        ident = Identifier(dialect, "column with spaces")
        sql, params = ident.to_sql()
        print_sql("Identifier with Spaces", sql, params)

        ident = Identifier(dialect, "user-defined")
        sql, params = ident.to_sql()
        print_sql("Identifier with Hyphen", sql, params)


    def demo_columns():
        """Demonstrate Column expressions."""
        print("=" * 70)
        print("COLUMNS")
        print("=" * 70)
        print()

        col = Column(dialect, "name")
        sql, params = col.to_sql()
        print_sql("Simple Column", sql, params)

        col = Column(dialect, "name", table="users")
        sql, params = col.to_sql()
        print_sql("Column with Table", sql, params)

        col = Column(dialect, "name", alias="user_name")
        sql, params = col.to_sql()
        print_sql("Column with Alias", sql, params)

        col = Column(dialect, "email", table="users", alias="contact")
        sql, params = col.to_sql()
        print_sql("Column with Table and Alias", sql, params)


    def demo_tables():
        """Demonstrate TableExpression."""
        print("=" * 70)
        print("TABLE EXPRESSIONS")
        print("=" * 70)
        print()

        tbl = TableExpression(dialect, "users")
        sql, params = tbl.to_sql()
        print_sql("Simple Table", sql, params)

        tbl = TableExpression(dialect, "users", alias="u")
        sql, params = tbl.to_sql()
        print_sql("Table with Alias", sql, params)

        tbl = TableExpression(dialect, "order_details", alias="od")
        sql, params = tbl.to_sql()
        print_sql("Complex Table Name", sql, params)


    def demo_functions():
        """Demonstrate FunctionCall expressions."""
        print("=" * 70)
        print("FUNCTION CALLS")
        print("=" * 70)
        print()

        func = FunctionCall(dialect, "COUNT", Column(dialect, "id"))
        sql, params = func.to_sql()
        print_sql("COUNT Function", sql, params)

        func = FunctionCall(dialect, "SUM", Column(dialect, "amount"), alias="total")
        sql, params = func.to_sql()
        print_sql("SUM with Alias", sql, params)

        func = FunctionCall(dialect, "CONCAT",
                            Column(dialect, "first_name"),
                            Literal(dialect, " "),
                            Column(dialect, "last_name"))
        sql, params = func.to_sql()
        print_sql("CONCAT Function", sql, params)

        func = FunctionCall(dialect, "COUNT", Column(dialect, "id"), is_distinct=True)
        sql, params = func.to_sql()
        print_sql("COUNT DISTINCT", sql, params)

        func = FunctionCall(dialect, "AVG", Column(dialect, "price"), alias="avg_price")
        sql, params = func.to_sql()
        print_sql("AVG Function", sql, params)

        func = FunctionCall(dialect, "COALESCE",
                            Column(dialect, "phone"),
                            Literal(dialect, "N/A"))
        sql, params = func.to_sql()
        print_sql("COALESCE Function", sql, params)



    def demo_filter_clause():
        """Demonstrate aggregate FILTER clause."""
        print("=" * 70)
        print("AGGREGATE FILTER CLAUSE")
        print("=" * 70)
        print()

        filter_cond = ComparisonPredicate(dialect, "=", Column(dialect, "status"), Literal(dialect, "active"))
        func = FunctionCall(dialect, "COUNT", Column(dialect, "*"), filter_=filter_cond, alias="active_count")
        sql, params = func.to_sql()
        print_sql("COUNT with FILTER clause", sql, params)

        filter_cond_2 = ComparisonPredicate(dialect, ">", Column(dialect, "amount"), Literal(dialect, 100))
        func_2 = FunctionCall(dialect, "SUM", Column(dialect, "amount"), filter_=filter_cond_2, alias="high_value_sum")
        sql_2, params_2 = func_2.to_sql()
        print_sql("SUM with FILTER clause", sql_2, params_2)


    def demo_subqueries():
        """Demonstrate Subquery expressions."""
        print("=" * 70)
        print("SUBQUERIES")
        print("=" * 70)
        print()

        sub = Subquery(dialect, "SELECT id FROM users WHERE active = ?", (True,), alias="active_users")
        sql, params = sub.to_sql()
        print_sql("Simple Subquery", sql, params)

        sub = Subquery(dialect,
                       "SELECT MAX(salary) FROM employees WHERE department = ?",
                       ("Engineering",),
                       alias="max_sal")
        sql, params = sub.to_sql()
        print_sql("Aggregate Subquery", sql, params)


    # ========== Part 2: Operators ==========

    def demo_arithmetic():
        """Demonstrate arithmetic operations."""
        print("=" * 70)
        print("ARITHMETIC OPERATIONS")
        print("=" * 70)
        print()

        expr = BinaryArithmeticExpression(dialect, "+",
                                          Column(dialect, "price"),
                                          Literal(dialect, 10))
        sql, params = expr.to_sql()
        print_sql("Addition", sql, params)

        expr = BinaryArithmeticExpression(dialect, "-",
                                          Column(dialect, "balance"),
                                          Literal(dialect, 50))
        sql, params = expr.to_sql()
        print_sql("Subtraction", sql, params)

        expr = BinaryArithmeticExpression(dialect, "*",
                                          Column(dialect, "quantity"),
                                          Column(dialect, "unit_price"))
        sql, params = expr.to_sql()
        print_sql("Multiplication", sql, params)

        expr = BinaryArithmeticExpression(dialect, "/",
                                          Column(dialect, "total"),
                                          Literal(dialect, 12))
        sql, params = expr.to_sql()
        print_sql("Division", sql, params)

        expr = BinaryArithmeticExpression(dialect, "%",
                                          Column(dialect, "value"),
                                          Literal(dialect, 10))
        sql, params = expr.to_sql()
        print_sql("Modulo", sql, params)

        # Nested arithmetic
        price_with_tax = BinaryArithmeticExpression(dialect, "*",
                                                    Column(dialect, "price"),
                                                    Literal(dialect, 1.1))
        rounded = FunctionCall(dialect, "ROUND", price_with_tax, Literal(dialect, 2))
        sql, params = rounded.to_sql()
        print_sql("Nested: ROUND(price * 1.1, 2)", sql, params)


    def demo_binary_operators():
        """Demonstrate binary operators."""
        print("=" * 70)
        print("BINARY OPERATORS")
        print("=" * 70)
        print()

        expr = BinaryExpression(dialect, "||",
                                Column(dialect, "first_name"),
                                Column(dialect, "last_name"))
        sql, params = expr.to_sql()
        print_sql("String Concatenation (||)", sql, params)

        expr = BinaryExpression(dialect, "&&",
                                Column(dialect, "flag1"),
                                Column(dialect, "flag2"))
        sql, params = expr.to_sql()
        print_sql("Bitwise AND", sql, params)


    def demo_unary_operators():
        """Demonstrate unary operators."""
        print("=" * 70)
        print("UNARY OPERATORS")
        print("=" * 70)
        print()

        expr = UnaryExpression(dialect, "NOT", Column(dialect, "active"))
        sql, params = expr.to_sql()
        print_sql("NOT Operator", sql, params)

        expr = UnaryExpression(dialect, "-", Column(dialect, "balance"), pos='before')
        sql, params = expr.to_sql()
        print_sql("Negation (before)", sql, params)

        expr = UnaryExpression(dialect, "!", Column(dialect, "completed"), pos='before')
        sql, params = expr.to_sql()
        print_sql("Logical NOT (before)", sql, params)


    def demo_raw_sql():
        """Demonstrate raw SQL expressions."""
        print("=" * 70)
        print("RAW SQL EXPRESSIONS")
        print("=" * 70)
        print()

        expr = RawSQLExpression(dialect, "CURRENT_TIMESTAMP")
        sql, params = expr.to_sql()
        print_sql("Current Timestamp", sql, params)

        expr = RawSQLExpression(dialect, "NOW()")
        sql, params = expr.to_sql()
        print_sql("NOW() Function", sql, params)

        expr = RawSQLExpression(dialect, "LAST_INSERT_ID()")
        sql, params = expr.to_sql()
        print_sql("Last Insert ID", sql, params)


    def demo_sql_operations():
        """Demonstrate SQLOperation (generic operations)."""
        print("=" * 70)
        print("SQL OPERATIONS (Generic)")
        print("=" * 70)
        print()

        op = SQLOperation(dialect, "COALESCE",
                          Column(dialect, "name"),
                          Literal(dialect, "Unknown"))
        sql, params = op.to_sql()
        print_sql("COALESCE Operation", sql, params)

        op = SQLOperation(dialect, "GREATEST",
                          Column(dialect, "value1"),
                          Column(dialect, "value2"),
                          Literal(dialect, 0))
        sql, params = op.to_sql()
        print_sql("GREATEST Operation", sql, params)


    # ========== Part 3: Predicates ==========

    def demo_comparisons():
        """Demonstrate comparison predicates."""
        print("=" * 70)
        print("COMPARISON PREDICATES")
        print("=" * 70)
        print()

        pred = ComparisonPredicate(dialect, ">=",
                                   Column(dialect, "age"),
                                   Literal(dialect, 18))
        sql, params = pred.to_sql()
        print_sql("Greater Than or Equal", sql, params)

        pred = ComparisonPredicate(dialect, "=",
                                   Column(dialect, "status"),
                                   Literal(dialect, "active"))
        sql, params = pred.to_sql()
        print_sql("Equality", sql, params)

        pred = ComparisonPredicate(dialect, "!=",
                                   Column(dialect, "deleted_at"),
                                   Literal(dialect, None))
        sql, params = pred.to_sql()
        print_sql("Not Equal", sql, params)

        pred = ComparisonPredicate(dialect, "<",
                                   Column(dialect, "price"),
                                   Literal(dialect, 100))
        sql, params = pred.to_sql()
        print_sql("Less Than", sql, params)

        pred = ComparisonPredicate(dialect, "<=",
                                   Column(dialect, "stock"),
                                   Literal(dialect, 10))
        sql, params = pred.to_sql()
        print_sql("Less Than or Equal", sql, params)

        pred = ComparisonPredicate(dialect, ">",
                                   Column(dialect, "rating"),
                                   Literal(dialect, 4.5))
        sql, params = pred.to_sql()
        print_sql("Greater Than", sql, params)


    def demo_logical():
        """Demonstrate logical predicates."""
        print("=" * 70)
        print("LOGICAL PREDICATES")
        print("=" * 70)
        print()

        pred1 = ComparisonPredicate(dialect, ">=", Column(dialect, "age"), Literal(dialect, 18))
        pred2 = ComparisonPredicate(dialect, "<", Column(dialect, "age"), Literal(dialect, 65))

        and_pred = LogicalPredicate(dialect, "AND", pred1, pred2)
        sql, params = and_pred.to_sql()
        print_sql("AND Predicate", sql, params)

        pred3 = ComparisonPredicate(dialect, "=", Column(dialect, "country"), Literal(dialect, "US"))
        or_pred = LogicalPredicate(dialect, "OR", and_pred, pred3)
        sql, params = or_pred.to_sql()
        print_sql("Nested AND/OR", sql, params)

        not_pred = LogicalPredicate(dialect, "NOT", pred1)
        sql, params = not_pred.to_sql()
        print_sql("NOT Predicate", sql, params)

        # Complex nested logic
        complex_pred = LogicalPredicate(dialect, "AND",
                                        LogicalPredicate(dialect, "OR", pred1, pred2),
                                        LogicalPredicate(dialect, "NOT", pred3))
        sql, params = complex_pred.to_sql()
        print_sql("Complex Nested Logic", sql, params)


    def demo_in_predicate():
        """Demonstrate IN predicates."""
        print("=" * 70)
        print("IN PREDICATES")
        print("=" * 70)
        print()

        pred = InPredicate(dialect,
                           Column(dialect, "status"),
                           Literal(dialect, ["active", "pending", "approved"]))
        sql, params = pred.to_sql()
        print_sql("IN with List", sql, params)

        pred = InPredicate(dialect,
                           Column(dialect, "id"),
                           Literal(dialect, [1, 2, 3, 4, 5]))
        sql, params = pred.to_sql()
        print_sql("IN with Numbers", sql, params)

        # IN with subquery
        subquery = Subquery(dialect, "SELECT id FROM users WHERE verified = ?", (True,))
        pred = InPredicate(dialect, Column(dialect, "user_id"), subquery)
        sql, params = pred.to_sql()
        print_sql("IN with Subquery", sql, params)


    def demo_between():
        """Demonstrate BETWEEN predicates."""
        print("=" * 70)
        print("BETWEEN PREDICATES")
        print("=" * 70)
        print()

        pred = BetweenPredicate(dialect,
                                Column(dialect, "age"),
                                Literal(dialect, 18),
                                Literal(dialect, 65))
        sql, params = pred.to_sql()
        print_sql("BETWEEN Numbers", sql, params)

        pred = BetweenPredicate(dialect,
                                Column(dialect, "created_at"),
                                Literal(dialect, "2024-01-01"),
                                Literal(dialect, "2024-12-31"))
        sql, params = pred.to_sql()
        print_sql("BETWEEN Dates", sql, params)

        pred = BetweenPredicate(dialect,
                                Column(dialect, "price"),
                                Literal(dialect, 10.50),
                                Literal(dialect, 99.99))
        sql, params = pred.to_sql()
        print_sql("BETWEEN Decimals", sql, params)


    def demo_is_null():
        """Demonstrate IS NULL predicates."""
        print("=" * 70)
        print("IS NULL PREDICATES")
        print("=" * 70)
        print()

        pred = IsNullPredicate(dialect, Column(dialect, "deleted_at"))
        sql, params = pred.to_sql()
        print_sql("IS NULL", sql, params)

        pred = IsNullPredicate(dialect, Column(dialect, "deleted_at"), is_not=True)
        sql, params = pred.to_sql()
        print_sql("IS NOT NULL", sql, params)

        pred = IsNullPredicate(dialect, Column(dialect, "optional_field"))
        sql, params = pred.to_sql()
        print_sql("IS NULL on Optional Field", sql, params)


    def demo_like():
        """Demonstrate LIKE predicates."""
        print("=" * 70)
        print("LIKE PREDICATES")
        print("=" * 70)
        print()

        pred = LikePredicate(dialect, "LIKE",
                             Column(dialect, "name"),
                             Literal(dialect, "John%"))
        sql, params = pred.to_sql()
        print_sql("LIKE (starts with)", sql, params)

        pred = LikePredicate(dialect, "LIKE",
                             Column(dialect, "email"),
                             Literal(dialect, "%@gmail.com"))
        sql, params = pred.to_sql()
        print_sql("LIKE (ends with)", sql, params)

        pred = LikePredicate(dialect, "LIKE",
                             Column(dialect, "description"),
                             Literal(dialect, "%important%"))
        sql, params = pred.to_sql()
        print_sql("LIKE (contains)", sql, params)

        pred = LikePredicate(dialect, "NOT LIKE",
                             Column(dialect, "email"),
                             Literal(dialect, "%@spam.com"))
        sql, params = pred.to_sql()
        print_sql("NOT LIKE", sql, params)

        pred = LikePredicate(dialect, "ILIKE",
                             Column(dialect, "name"),
                             Literal(dialect, "%smith%"))
        sql, params = pred.to_sql()
        print_sql("ILIKE (case-insensitive)", sql, params)


    # ========== Part 4: Advanced Functions ==========

    def demo_case():
        """Demonstrate CASE expressions."""
        print("=" * 70)
        print("CASE EXPRESSIONS")
        print("=" * 70)
        print()

        # Searched CASE
        cases = [
            (ComparisonPredicate(dialect, "<", Column(dialect, "age"), Literal(dialect, 18)),
             Literal(dialect, "minor")),
            (ComparisonPredicate(dialect, "<", Column(dialect, "age"), Literal(dialect, 65)),
             Literal(dialect, "adult"))
        ]
        case_expr = CaseExpression(dialect,
                                   cases=cases,
                                   else_result=Literal(dialect, "senior"))
        sql, params = case_expr.to_sql()
        print_sql("Searched CASE", sql, params)

        # Simple CASE
        cases = [
            (Literal(dialect, 1), Literal(dialect, "One")),
            (Literal(dialect, 2), Literal(dialect, "Two")),
            (Literal(dialect, 3), Literal(dialect, "Three"))
        ]
        case_expr = CaseExpression(dialect,
                                   value=Column(dialect, "status_code"),
                                   cases=cases,
                                   else_result=Literal(dialect, "Unknown"))
        sql, params = case_expr.to_sql()
        print_sql("Simple CASE", sql, params)

        # Complex CASE with multiple conditions
        cases = [
            (LogicalPredicate(dialect, "AND",
                              ComparisonPredicate(dialect, ">=", Column(dialect, "score"), Literal(dialect, 90)),
                              ComparisonPredicate(dialect, "<=", Column(dialect, "score"), Literal(dialect, 100))),
             Literal(dialect, "A")),
            (BetweenPredicate(dialect, Column(dialect, "score"), Literal(dialect, 80), Literal(dialect, 89)),
             Literal(dialect, "B")),
            (BetweenPredicate(dialect, Column(dialect, "score"), Literal(dialect, 70), Literal(dialect, 79)),
             Literal(dialect, "C"))
        ]
        case_expr = CaseExpression(dialect,
                                   cases=cases,
                                   else_result=Literal(dialect, "F"))
        sql, params = case_expr.to_sql()
        print_sql("Complex CASE with Ranges", sql, params)


    def demo_cast():
        """Demonstrate CAST expressions."""
        print("=" * 70)
        print("CAST EXPRESSIONS")
        print("=" * 70)
        print()

        expr = CastExpression(dialect, Column(dialect, "price"), "INTEGER")
        sql, params = expr.to_sql()
        print_sql("CAST to INTEGER", sql, params)

        expr = CastExpression(dialect, Column(dialect, "amount"), "DECIMAL(10,2)")
        sql, params = expr.to_sql()
        print_sql("CAST to DECIMAL", sql, params)

        expr = CastExpression(dialect, Column(dialect, "created_at"), "DATE")
        sql, params = expr.to_sql()
        print_sql("CAST to DATE", sql, params)

        expr = CastExpression(dialect, Column(dialect, "value"), "VARCHAR(255)")
        sql, params = expr.to_sql()
        print_sql("CAST to VARCHAR", sql, params)


    def demo_exists():
        """Demonstrate EXISTS expressions."""
        print("=" * 70)
        print("EXISTS EXPRESSIONS")
        print("=" * 70)
        print()

        subquery = Subquery(dialect,
                            "SELECT 1 FROM orders WHERE user_id = users.id",
                            ())
        exists = ExistsExpression(dialect, subquery)
        sql, params = exists.to_sql()
        print_sql("EXISTS", sql, params)

        not_exists = ExistsExpression(dialect, subquery, is_not=True)
        sql, params = not_exists.to_sql()
        print_sql("NOT EXISTS", sql, params)

        # Complex EXISTS
        complex_sub = Subquery(dialect,
                               "SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > ?",
                               (1000,))
        exists = ExistsExpression(dialect, complex_sub)
        sql, params = exists.to_sql()
        print_sql("EXISTS with Condition", sql, params)


    def demo_any_all():
        """Demonstrate ANY/ALL expressions."""
        print("=" * 70)
        print("ANY/ALL EXPRESSIONS")
        print("=" * 70)
        print()

        any_expr = AnyExpression(dialect,
                                 Column(dialect, "price"),
                                 ">",
                                 Literal(dialect, [100, 200, 300]))
        sql, params = any_expr.to_sql()
        print_sql("ANY with Array", sql, params)

        all_expr = AllExpression(dialect,
                                 Column(dialect, "price"),
                                 ">",
                                 Literal(dialect, [50, 75]))
        sql, params = all_expr.to_sql()
        print_sql("ALL with Array", sql, params)

        # ANY with subquery
        subquery = Subquery(dialect, "SELECT price FROM products WHERE category = ?", ("electronics",))
        any_expr = AnyExpression(dialect,
                                 Column(dialect, "budget"),
                                 ">=",
                                 subquery)
        sql, params = any_expr.to_sql()
        print_sql("ANY with Subquery", sql, params)


    def demo_window():
        """Demonstrate window functions."""
        print("=" * 70)
        print("WINDOW FUNCTIONS")
        print("=" * 70)
        print()

        rank_func = FunctionCall(dialect, "RANK")
        window = WindowExpression(dialect,
                                  rank_func,
                                  partition_by=[Column(dialect, "department")],
                                  order_by=[Column(dialect, "salary")])
        sql, params = window.to_sql()
        print_sql("RANK() OVER (PARTITION BY ... ORDER BY ...)", sql, params)

        row_num = FunctionCall(dialect, "ROW_NUMBER")
        window = WindowExpression(dialect,
                                  row_num,
                                  order_by=[Column(dialect, "created_at")],
                                  alias="row_num")
        sql, params = window.to_sql()
        print_sql("ROW_NUMBER() with Alias", sql, params)

        lag_func = FunctionCall(dialect, "LAG", Column(dialect, "value"), Literal(dialect, 1))
        window = WindowExpression(dialect,
                                  lag_func,
                                  partition_by=[Column(dialect, "category")],
                                  order_by=[Column(dialect, "date")],
                                  alias="prev_value")
        sql, params = window.to_sql()
        print_sql("LAG() Function", sql, params)

        # Window with frame specification
        sum_func = FunctionCall(dialect, "SUM", Column(dialect, "amount"))
        window = WindowExpression(dialect,
                                  sum_func,
                                  partition_by=[Column(dialect, "user_id")],
                                  order_by=[Column(dialect, "date")],
                                  frame_type="ROWS",
                                  frame_start="UNBOUNDED PRECEDING",
                                  frame_end="CURRENT ROW",
                                  alias="running_total")
        sql, params = window.to_sql()
        print_sql("SUM() with Frame Specification", sql, params)


    def demo_json():
        """Demonstrate JSON operations."""
        print("=" * 70)
        print("JSON OPERATIONS")
        print("=" * 70)
        print()

        json_expr = JSONExpression(dialect,
                                   Column(dialect, "data"),
                                   "$.name")
        sql, params = json_expr.to_sql()
        print_sql("JSON Extract Path", sql, params)

        json_expr = JSONExpression(dialect,
                                   Column(dialect, "metadata"),
                                   "$.settings.theme",
                                   operation="->>")
        sql, params = json_expr.to_sql()
        print_sql("JSON Extract as Text", sql, params)

        json_expr = JSONExpression(dialect,
                                   Column(dialect, "config"),
                                   "$.features[0]",
                                   operation="->")
        sql, params = json_expr.to_sql()
        print_sql("JSON Array Access", sql, params)


    def demo_array():
        """Demonstrate array operations."""
        print("=" * 70)
        print("ARRAY OPERATIONS")
        print("=" * 70)
        print()

        # Array constructor
        array = ArrayExpression(dialect, "CONSTRUCTOR",
                                elements=[Literal(dialect, 1),
                                          Literal(dialect, 2),
                                          Literal(dialect, 3)])
        sql, params = array.to_sql()
        print_sql("Array Constructor", sql, params)

        # Array access
        array_access = ArrayExpression(dialect, "ACCESS",
                                       base_expr=Column(dialect, "tags"),
                                       index_expr=Literal(dialect, 1))
        sql, params = array_access.to_sql()
        print_sql("Array Subscript Access", sql, params)

        # Array with string elements
        array = ArrayExpression(dialect, "CONSTRUCTOR",
                                elements=[Literal(dialect, "red"),
                                          Literal(dialect, "green"),
                                          Literal(dialect, "blue")])
        sql, params = array.to_sql()
        print_sql("String Array Constructor", sql, params)


    def demo_json_table():
        """Demonstrate JSON_TABLE function."""
        print("=" * 70)
        print("JSON_TABLE FUNCTION")
        print("=" * 70)
        print()

        from rhosocial.activerecord.backend.expression.query_clauses import JSONTableColumn
        
        cols = [
            JSONTableColumn(name="id", data_type="INT", path="$.id"),
            JSONTableColumn(name="name", data_type="VARCHAR(100)", path="$.name"),
            JSONTableColumn(name="is_active", data_type="BOOLEAN", path="$.active")
        ]

        json_table_expr = JSONTableExpression(dialect,
                                              json_column=Column(dialect, "json_data"),
                                              path="$.users[*]",
                                              columns=cols,
                                              alias="user_data")
        sql, params = json_table_expr.to_sql()
        print_sql("JSON_TABLE Expression", sql, params)



    def demo_ordered_set_aggregation():
        """Demonstrate ordered-set aggregate functions (WITHIN GROUP)."""
        print("=" * 70)
        print("ORDERED-SET AGGREGATION (WITHIN GROUP)")
        print("=" * 70)
        print()

        # PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary)
        expr = OrderedSetAggregation(dialect,
                                     "PERCENTILE_CONT",
                                     args=[Literal(dialect, 0.5)],
                                     order_by=[Column(dialect, "salary")],
                                     alias="median_salary")
        sql, params = expr.to_sql()
        print_sql("PERCENTILE_CONT WITHIN GROUP", sql, params)

        # LISTAGG(name, ',') WITHIN GROUP (ORDER BY name)
        expr = OrderedSetAggregation(dialect,
                                     "LISTAGG",
                                     args=[Column(dialect, "name"), Literal(dialect, ",")],
                                     order_by=[Column(dialect, "name")],
                                     alias="employee_list")
        sql, params = expr.to_sql()
        print_sql("LISTAGG WITHIN GROUP", sql, params)

        # Some other function, e.g., NTILE (though usually a window function, some databases might support it as ordered-set)
        expr = OrderedSetAggregation(dialect,
                                     "NTILE",
                                     args=[Literal(dialect, 4)], # Divide into 4 tiles
                                     order_by=[Column(dialect, "score", "s")],
                                     alias="score_quartile")
        sql, params = expr.to_sql()
        print_sql("NTILE WITHIN GROUP", sql, params)

    # ========== Part 5: Query Clauses ==========

    def demo_joins():
        """Demonstrate JOIN expressions."""
        print("=" * 70)
        print("JOIN EXPRESSIONS")
        print("=" * 70)
        print()

        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "users", "u"),
                              right_table=TableExpression(dialect, "orders", "o"),
                              join_type="INNER",
                              condition=ComparisonPredicate(dialect, "=",
                                                            Column(dialect, "id", "u"),
                                                            Column(dialect, "user_id", "o")))
        sql, params = join.to_sql()
        print_sql("INNER JOIN", sql, params)

        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "users", "u"),
                              right_table=TableExpression(dialect, "profiles", "p"),
                              join_type="LEFT",
                              condition=ComparisonPredicate(dialect, "=",
                                                            Column(dialect, "id", "u"),
                                                            Column(dialect, "user_id", "p")))
        sql, params = join.to_sql()
        print_sql("LEFT JOIN", sql, params)

        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "employees", "e"),
                              right_table=TableExpression(dialect, "departments", "d"),
                              join_type="RIGHT",
                              condition=ComparisonPredicate(dialect, "=",
                                                            Column(dialect, "dept_id", "e"),
                                                            Column(dialect, "id", "d")))
        sql, params = join.to_sql()
        print_sql("RIGHT JOIN", sql, params)

        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "table1", "t1"),
                              right_table=TableExpression(dialect, "table2", "t2"),
                              join_type="FULL",
                              condition=ComparisonPredicate(dialect, "=",
                                                            Column(dialect, "key", "t1"),
                                                            Column(dialect, "key", "t2")))
        sql, params = join.to_sql()
        print_sql("FULL OUTER JOIN", sql, params)

        # USING clause
        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "orders", "o"),
                              right_table=TableExpression(dialect, "order_items", "oi"),
                              join_type="INNER",
                              using=["order_id"])
        sql, params = join.to_sql()
        print_sql("JOIN with USING", sql, params)

        # CROSS JOIN
        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "colors", "c"),
                              right_table=TableExpression(dialect, "sizes", "s"),
                              join_type="CROSS")
        sql, params = join.to_sql()
        print_sql("CROSS JOIN", sql, params)


    def demo_cte():
        """Demonstrate CTE (Common Table Expressions)."""
        print("=" * 70)
        print("COMMON TABLE EXPRESSIONS (CTE)")
        print("=" * 70)
        print()

        cte = CTEExpression(dialect,
                            name="high_earners",
                            query=("SELECT id, name, salary FROM employees WHERE salary > ?", [50000]),
                            columns=["id", "name", "salary"])
        sql, params = cte.to_sql()
        print_sql("Basic CTE", sql, params)

        # Recursive CTE
        cte = CTEExpression(dialect,
                            name="org_tree",
                            query=("""
                                   SELECT id, name, manager_id, 1 AS level
                                   FROM employees
                                   WHERE manager_id IS NULL
                                   UNION ALL
                                   SELECT e.id, e.name, e.manager_id, t.level + 1
                                   FROM employees e
                                            INNER JOIN org_tree t ON e.manager_id = t.id
                                   """, []),
                            columns=["id", "name", "manager_id", "level"],
                            recursive=True)
        sql, params = cte.to_sql()
        print_sql("Recursive CTE", sql, params)

        # Materialized CTE
        cte = CTEExpression(dialect,
                            name="expensive_query",
                            query=("SELECT * FROM large_table WHERE complex_condition = ?", [True]),
                            materialized=True)
        sql, params = cte.to_sql()
        print_sql("Materialized CTE", sql, params)


    def demo_set_operations():
        """Demonstrate set operations."""
        print("=" * 70)
        print("SET OPERATIONS")
        print("=" * 70)
        print()

        query1 = Subquery(dialect, "SELECT id FROM active_users", ())
        query2 = Subquery(dialect, "SELECT id FROM premium_users", ())

        union = SetOperationExpression(dialect,
                                       query1, query2,
                                       "UNION", "combined")
        sql, params = union.to_sql()
        print_sql("UNION", sql, params)

        union_all = SetOperationExpression(dialect,
                                           query1, query2,
                                           "UNION", "combined",
                                           all=True)
        sql, params = union_all.to_sql()
        print_sql("UNION ALL", sql, params)

        intersect = SetOperationExpression(dialect,
                                           query1, query2,
                                           "INTERSECT", "both")
        sql, params = intersect.to_sql()
        print_sql("INTERSECT", sql, params)

        intersect_all = SetOperationExpression(dialect,
                                               query1, query2,
                                               "INTERSECT", "both",
                                               all=True)
        sql, params = intersect_all.to_sql()
        print_sql("INTERSECT ALL", sql, params)

        except_op = SetOperationExpression(dialect,
                                           query1, query2,
                                           "EXCEPT", "difference")
        sql, params = except_op.to_sql()
        print_sql("EXCEPT", sql, params)

        except_all = SetOperationExpression(dialect,
                                            query1, query2,
                                            "EXCEPT", "difference",
                                            all=True)
        sql, params = except_all.to_sql()
        print_sql("EXCEPT ALL", sql, params)


    def demo_grouping():
        """Demonstrate grouping operations including advanced features."""
        print("=" * 70)
        print("GROUPING OPERATIONS")
        print("=" * 70)
        print()

        # Basic GROUP BY
        group = GroupExpression(dialect, [Column(dialect, "department")])
        sql, params = group.to_sql()
        print_sql("GROUP BY Single Column", sql, params)

        # Multiple columns
        group = GroupExpression(dialect, [
            Column(dialect, "department"),
            Column(dialect, "category")
        ])
        sql, params = group.to_sql()
        print_sql("GROUP BY Multiple Columns", sql, params)

        # ROLLUP
        rollup = GroupingExpression(dialect, "ROLLUP", [
            Column(dialect, "year"),
            Column(dialect, "quarter"),
            Column(dialect, "month")
        ])
        sql, params = rollup.to_sql()
        print_sql("ROLLUP", sql, params)

        # CUBE
        cube = GroupingExpression(dialect, "CUBE", [
            Column(dialect, "region"),
            Column(dialect, "product")
        ])
        sql, params = cube.to_sql()
        print_sql("CUBE", sql, params)

        # GROUPING SETS
        grouping_sets = GroupingExpression(dialect, "GROUPING SETS", [
            Column(dialect, "country"),
            Column(dialect, "city")
        ])
        sql, params = grouping_sets.to_sql()
        print_sql("GROUPING SETS", sql, params)


    def demo_values():
        """Demonstrate VALUES expressions."""
        print("=" * 70)
        print("VALUES EXPRESSIONS")
        print("=" * 70)
        print()

        values = ValuesExpression(dialect,
                                  [(1, "John"), (2, "Jane"), (3, "Bob")],
                                  "v",
                                  ["id", "name"])
        sql, params = values.to_sql()
        print_sql("Simple VALUES", sql, params)

        values = ValuesExpression(dialect,
                                  [(1, "Product A", 29.99),
                                   (2, "Product B", 39.99),
                                   (3, "Product C", 49.99)],
                                  "products",
                                  ["id", "name", "price"])
        sql, params = values.to_sql()
        print_sql("VALUES with Multiple Types", sql, params)


    def demo_table_functions():
        """Demonstrate table functions."""
        print("=" * 70)
        print("TABLE FUNCTIONS")
        print("=" * 70)
        print()

        # UNNEST function (PostgreSQL)
        func = TableFunctionExpression(dialect,
                                       "UNNEST",
                                       Column(dialect, "tags"),
                                       alias="t",
                                       column_names=["tag"])
        sql, params = func.to_sql()
        print_sql("UNNEST Array", sql, params)

        # JSON_TABLE (MySQL/Oracle)
        func = TableFunctionExpression(dialect,
                                       "JSON_TABLE",
                                       Column(dialect, "data"),
                                       alias="jt",
                                       column_names=["id", "name", "value"])
        sql, params = func.to_sql()
        print_sql("JSON_TABLE", sql, params)

        # generate_series (PostgreSQL)
        func = TableFunctionExpression(dialect,
                                       "generate_series",
                                       Literal(dialect, 1),
                                       Literal(dialect, 10),
                                       alias="series",
                                       column_names=["n"])
        sql, params = func.to_sql()
        print_sql("generate_series", sql, params)


    def demo_lateral():
        """Demonstrate LATERAL joins."""
        print("=" * 70)
        print("LATERAL JOINS")
        print("=" * 70)
        print()

        # LATERAL with subquery
        lateral_sub = Subquery(dialect,
                               "SELECT * FROM orders o WHERE o.user_id = u.id ORDER BY created_at DESC LIMIT 3",
                               ())
        lateral = LateralExpression(dialect,
                                    lateral_sub,
                                    "recent_orders",
                                    "CROSS")
        sql, params = lateral.to_sql()
        print_sql("CROSS JOIN LATERAL", sql, params)

        # LEFT JOIN LATERAL
        lateral = LateralExpression(dialect,
                                    lateral_sub,
                                    "recent_orders",
                                    "LEFT")
        sql, params = lateral.to_sql()
        print_sql("LEFT JOIN LATERAL", sql, params)

        # LATERAL with table function
        lateral_func = TableFunctionExpression(dialect,
                                               "UNNEST",
                                               Column(dialect, "tags", "p"),
                                               alias="t",
                                               column_names=["tag"])
        lateral = LateralExpression(dialect,
                                    lateral_func,
                                    "tag_list",
                                    "CROSS")
        sql, params = lateral.to_sql()
        print_sql("LATERAL with Table Function", sql, params)


    def demo_merge_statement():
        """Demonstrate MERGE statements."""
        print("=" * 70)
        print("MERGE STATEMENTS")
        print("=" * 70)
        print()

        # Source data: VALUES expression
        source_values = ValuesExpression(dialect,
                                         [(1, "New Product A", 15.0),
                                          (4, "New Product D", 25.0)], # 4 is new, 1 is existing
                                         "new_products",
                                         ["id", "name", "price"])

        # Target table
        target_table = TableExpression(dialect, "products", "p")

        # ON condition
        on_cond = ComparisonPredicate(dialect, "=",
                                      Column(dialect, "id", "p"),
                                      Column(dialect, "id", "new_products"))

        # WHEN MATCHED THEN UPDATE
        when_matched_update = MergeAction(
            action_type=MergeActionType.UPDATE,
            assignments={
                "name": Column(dialect, "name", "new_products"),
                "price": Column(dialect, "price", "new_products")
            },
            condition=ComparisonPredicate(dialect, "!=",
                                          Column(dialect, "price", "p"),
                                          Column(dialect, "price", "new_products")) # Update only if price changed
        )

        # WHEN NOT MATCHED THEN INSERT
        when_not_matched_insert = MergeAction(
            action_type=MergeActionType.INSERT,
            assignments={ # Using assignments to carry column names for INSERT for DummyDialect
                "id": Column(dialect, "id", "new_products"),
                "name": Column(dialect, "name", "new_products"),
                "price": Column(dialect, "price", "new_products")
            }
        )

        merge_expr = MergeExpression(dialect,
                                     target_table=target_table,
                                     source=source_values,
                                     on_condition=on_cond,
                                     when_matched=[when_matched_update],
                                     when_not_matched=[when_not_matched_insert])
        sql, params = merge_expr.to_sql()
        print_sql("Simple MERGE (Update existing, Insert new)", sql, params)


    def demo_temporal_tables():
        """Demonstrate temporal table queries."""
        print("=" * 70)
        print("TEMPORAL TABLE QUERIES")
        print("=" * 70)
        print()

        # FOR SYSTEM_TIME AS OF
        table_as_of = TableExpression(dialect,
                                      name="employees",
                                      alias="e",
                                      temporal_options={"as_of": "2024-01-01T00:00:00Z"})
        sql, params = table_as_of.to_sql()
        print_sql("FOR SYSTEM_TIME AS OF", sql, params)

        # FOR SYSTEM_TIME BETWEEN ... AND ...
        table_between = TableExpression(dialect,
                                        name="employees",
                                        alias="e",
                                        temporal_options={"between": "2023-01-01", "and": "2023-12-31"})
        sql, params = table_between.to_sql()
        print_sql("FOR SYSTEM_TIME BETWEEN", sql, params)

        # FOR SYSTEM_TIME FROM ... TO ...
        table_from_to = TableExpression(dialect,
                                        name="employees",
                                        alias="e",
                                        temporal_options={"from": "2023-01-01", "to": "2023-12-31"})
        sql, params = table_from_to.to_sql()
        print_sql("FOR SYSTEM_TIME FROM ... TO", sql, params)


    def demo_qualify_clause():
        """Demonstrate QUALIFY clause."""
        print("=" * 70)
        print("QUALIFY CLAUSE")
        print("=" * 70)
        print()

        # SELECT with QUALIFY
        query = QueryExpression(dialect,
                                select=[Column(dialect, "id"),
                                        Column(dialect, "name"),
                                        WindowExpression(dialect,
                                                       FunctionCall(dialect, "ROW_NUMBER"),
                                                       partition_by=[Column(dialect, "department")],
                                                       order_by=[Column(dialect, "salary")],
                                                       alias="rn")],
                                from_=TableExpression(dialect, "employees"),
                                qualify=ComparisonPredicate(dialect, "=", Column(dialect, "rn"), Literal(dialect, 1)))
        sql, params = query.to_sql()
        print_sql("SELECT with QUALIFY", sql, params)


    def demo_for_update_skip_locked():
        """Demonstrate FOR UPDATE SKIP LOCKED clause."""
        print("=" * 70)
        print("FOR UPDATE SKIP LOCKED CLAUSE")
        print("=" * 70)
        print()

        # Basic FOR UPDATE
        query = QueryExpression(dialect,
                                select=[Column(dialect, "id"),
                                        Column(dialect, "name")],
                                from_=TableExpression(dialect, "products"),
                                for_update_options={})
        sql, params = query.to_sql()
        print_sql("Basic FOR UPDATE", sql, params)

        # FOR UPDATE SKIP LOCKED
        query_skip_locked = QueryExpression(dialect,
                                            select=[Column(dialect, "id"),
                                                    Column(dialect, "name")],
                                            from_=TableExpression(dialect, "products"),
                                            for_update_options={"skip_locked": True})
        sql_skip_locked, params_skip_locked = query_skip_locked.to_sql()
        print_sql("FOR UPDATE SKIP LOCKED", sql_skip_locked, params_skip_locked)

        # FOR UPDATE OF table NOWAIT
        query_nowait = QueryExpression(dialect,
                                       select=[Column(dialect, "id"),
                                               Column(dialect, "name")],
                                       from_=TableExpression(dialect, "products", alias="p"),
                                       for_update_options={"of": ["p"], "nowait": True})
        sql_nowait, params_nowait = query_nowait.to_sql()
        print_sql("FOR UPDATE OF table NOWAIT", sql_nowait, params_nowait)

    # ========== Part 6: Complete Statements ==========

    def demo_select():
        """Demonstrate complete SELECT statements."""
        print("=" * 70)
        print("SELECT STATEMENTS")
        print("=" * 70)
        print()

        # Simple SELECT
        query = QueryExpression(dialect,
                                select=[Column(dialect, "id"),
                                        Column(dialect, "name"),
                                        Column(dialect, "email")],
                                from_=TableExpression(dialect, "users"))
        sql, params = query.to_sql()
        print_sql("Simple SELECT", sql, params)

        # SELECT with WHERE
        query = QueryExpression(dialect,
                                select=[Column(dialect, "id"),
                                        Column(dialect, "name")],
                                from_=TableExpression(dialect, "users", "u"),
                                where=ComparisonPredicate(dialect, ">",
                                                          Column(dialect, "age"),
                                                          Literal(dialect, 18)))
        sql, params = query.to_sql()
        print_sql("SELECT with WHERE", sql, params)

        # SELECT with ORDER BY and LIMIT
        query = QueryExpression(dialect,
                                select=[Column(dialect, "name"),
                                        Column(dialect, "created_at")],
                                from_=TableExpression(dialect, "users"),
                                order_by=[Column(dialect, "created_at")],
                                limit=10,
                                offset=5)
        sql, params = query.to_sql()
        print_sql("SELECT with ORDER BY, LIMIT and OFFSET", sql, params)

        # SELECT with GROUP BY and HAVING
        query = QueryExpression(dialect,
                                select=[Column(dialect, "department"),
                                        FunctionCall(dialect, "COUNT",
                                                     Column(dialect, "id"),
                                                     alias="emp_count")],
                                from_=TableExpression(dialect, "employees"),
                                group_by=[Column(dialect, "department")],
                                having=ComparisonPredicate(dialect, ">",
                                                           FunctionCall(dialect, "COUNT",
                                                                        Column(dialect, "id")),
                                                           Literal(dialect, 5)))
        sql, params = query.to_sql()
        print_sql("SELECT with GROUP BY and HAVING", sql, params)

        # SELECT with multiple aggregates
        query = QueryExpression(dialect,
                                select=[
                                    Column(dialect, "category"),
                                    FunctionCall(dialect, "COUNT", Column(dialect, "id"), alias="total"),
                                    FunctionCall(dialect, "AVG", Column(dialect, "price"), alias="avg_price"),
                                    FunctionCall(dialect, "MAX", Column(dialect, "price"), alias="max_price"),
                                    FunctionCall(dialect, "MIN", Column(dialect, "price"), alias="min_price")
                                ],
                                from_=TableExpression(dialect, "products"),
                                group_by=[Column(dialect, "category")])
        sql, params = query.to_sql()
        print_sql("SELECT with Multiple Aggregates", sql, params)


    def demo_insert():
        """Demonstrate INSERT statements."""
        print("=" * 70)
        print("INSERT STATEMENTS")
        print("=" * 70)
        print()

        insert = InsertExpression(dialect,
                                  "users",
                                  ["name", "email", "age"],
                                  [Literal(dialect, "John Doe"),
                                   Literal(dialect, "john@example.com"),
                                   Literal(dialect, 30)])
        sql, params = insert.to_sql()
        print_sql("Simple INSERT", sql, params)

        # INSERT with RETURNING
        print("--- INSERT with RETURNING ---")
        print(f"SQL: {sql} RETURNING id, created_at")
        if params:
            print(f"Parameters: {params}")
        print()

        # INSERT with more columns
        insert = InsertExpression(dialect,
                                  "products",
                                  ["name", "description", "price", "stock", "category"],
                                  [Literal(dialect, "Widget"),
                                   Literal(dialect, "A useful widget"),
                                   Literal(dialect, 29.99),
                                   Literal(dialect, 100),
                                   Literal(dialect, "Tools")])
        sql, params = insert.to_sql()
        print_sql("INSERT with Multiple Columns", sql, params)


    def demo_update():
        """Demonstrate UPDATE statements."""
        print("=" * 70)
        print("UPDATE STATEMENTS")
        print("=" * 70)
        print()

        update = UpdateExpression(dialect,
                                  "users",
                                  {"name": Literal(dialect, "Jane Doe"),
                                   "age": Literal(dialect, 31)},
                                  ComparisonPredicate(dialect, "=",
                                                      Column(dialect, "id"),
                                                      Literal(dialect, 1)))
        sql, params = update.to_sql()
        print_sql("Simple UPDATE", sql, params)

        # UPDATE with complex WHERE
        update = UpdateExpression(dialect,
                                  "orders",
                                  {"status": Literal(dialect, "shipped"),
                                   "shipped_at": RawSQLExpression(dialect, "NOW()")},
                                  LogicalPredicate(dialect, "AND",
                                                   ComparisonPredicate(dialect, "=",
                                                                       Column(dialect, "status"),
                                                                       Literal(dialect, "pending")),
                                                   ComparisonPredicate(dialect, "<",
                                                                       Column(dialect, "created_at"),
                                                                       Literal(dialect, "2024-01-01"))))
        sql, params = update.to_sql()
        print_sql("UPDATE with Complex WHERE", sql, params)

        # UPDATE with arithmetic
        update = UpdateExpression(dialect,
                                  "products",
                                  {"stock": BinaryArithmeticExpression(dialect, "-",
                                                                       Column(dialect, "stock"),
                                                                       Literal(dialect, 1))},
                                  ComparisonPredicate(dialect, "=",
                                                      Column(dialect, "id"),
                                                      Literal(dialect, 100)))
        sql, params = update.to_sql()
        print_sql("UPDATE with Arithmetic", sql, params)


    def demo_delete():
        """Demonstrate DELETE statements."""
        print("=" * 70)
        print("DELETE STATEMENTS")
        print("=" * 70)
        print()

        delete = DeleteExpression(dialect,
                                  "users",
                                  ComparisonPredicate(dialect, "=",
                                                      Column(dialect, "id"),
                                                      Literal(dialect, 1)))
        sql, params = delete.to_sql()
        print_sql("Simple DELETE", sql, params)

        # DELETE with complex condition
        delete = DeleteExpression(dialect,
                                  "logs",
                                  LogicalPredicate(dialect, "AND",
                                                   IsNullPredicate(dialect,
                                                                   Column(dialect, "user_id")),
                                                   ComparisonPredicate(dialect, "<",
                                                                       Column(dialect, "created_at"),
                                                                       Literal(dialect, "2023-01-01"))))
        sql, params = delete.to_sql()
        print_sql("DELETE with Complex WHERE", sql, params)

        # DELETE with IN
        delete = DeleteExpression(dialect,
                                  "temp_data",
                                  InPredicate(dialect,
                                              Column(dialect, "status"),
                                              Literal(dialect, ["expired", "invalid", "duplicate"])))
        sql, params = delete.to_sql()
        print_sql("DELETE with IN", sql, params)


    def demo_explain():
        """Demonstrate EXPLAIN statements."""
        print("=" * 70)
        print("EXPLAIN STATEMENTS")
        print("=" * 70)
        print()

        query = QueryExpression(dialect,
                                select=[Column(dialect, "name")],
                                from_=TableExpression(dialect, "users"),
                                where=ComparisonPredicate(dialect, "=",
                                                          Column(dialect, "email"),
                                                          Literal(dialect, "test@example.com")))

        explain = ExplainExpression(dialect, query)
        sql, params = explain.to_sql()
        print_sql("EXPLAIN SELECT", sql, params)

        # EXPLAIN with complex query
        complex_query = QueryExpression(dialect,
                                        select=[
                                            Column(dialect, "u", "name"),
                                            FunctionCall(dialect, "COUNT",
                                                         Column(dialect, "o", "id"),
                                                         alias="order_count")
                                        ],
                                        from_=JoinExpression(dialect,
                                                             left_table=TableExpression(dialect, "users", "u"),
                                                             right_table=TableExpression(dialect, "orders", "o"),
                                                             join_type="LEFT",
                                                             condition=ComparisonPredicate(dialect, "=",
                                                                                           Column(dialect, "id", "u"),
                                                                                           Column(dialect, "user_id",
                                                                                                  "o"))),
                                        group_by=[Column(dialect, "id", "u")])

        explain = ExplainExpression(dialect, complex_query)
        sql, params = explain.to_sql()
        print_sql("EXPLAIN Complex Query", sql, params)


    # ========== Part 7: Complex Scenarios ==========

    def demo_complex_join_query():
        """Demonstrate complex query with multiple joins."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Multiple Joins with Aggregation")
        print("=" * 70)
        print()

        # Build the FROM clause with chained joins
        users_orders = JoinExpression(dialect,
                                      left_table=TableExpression(dialect, "users", "u"),
                                      right_table=TableExpression(dialect, "orders", "o"),
                                      join_type="LEFT",
                                      condition=ComparisonPredicate(dialect, "=",
                                                                    Column(dialect, "id", "u"),
                                                                    Column(dialect, "user_id", "o")))

        with_items = JoinExpression(dialect,
                                    left_table=users_orders,
                                    right_table=TableExpression(dialect, "order_items", "oi"),
                                    join_type="LEFT",
                                    condition=ComparisonPredicate(dialect, "=",
                                                                  Column(dialect, "id", "o"),
                                                                  Column(dialect, "order_id", "oi")))

        with_products = JoinExpression(dialect,
                                       left_table=with_items,
                                       right_table=TableExpression(dialect, "products", "p"),
                                       join_type="LEFT",
                                       condition=ComparisonPredicate(dialect, "=",
                                                                     Column(dialect, "product_id", "oi"),
                                                                     Column(dialect, "id", "p")))

        query = QueryExpression(dialect,
                                select=[
                                    Column(dialect, "name", "u"),
                                    Column(dialect, "email", "u"),
                                    FunctionCall(dialect, "COUNT",
                                                 Column(dialect, "id", "o"),
                                                 is_distinct=True,
                                                 alias="order_count"),
                                    FunctionCall(dialect, "SUM",
                                                 Column(dialect, "quantity", "oi"),
                                                 alias="total_items"),
                                    FunctionCall(dialect, "SUM",
                                                 BinaryArithmeticExpression(dialect, "*",
                                                                            Column(dialect, "quantity", "oi"),
                                                                            Column(dialect, "price", "p")),
                                                 alias="total_value")
                                ],
                                from_=with_products,
                                where=ComparisonPredicate(dialect, ">",
                                                          Column(dialect, "created_at", "u"),
                                                          Literal(dialect, "2024-01-01")),
                                group_by=[Column(dialect, "id", "u")],
                                having=ComparisonPredicate(dialect, ">",
                                                           FunctionCall(dialect, "COUNT",
                                                                        Column(dialect, "id", "o"),
                                                                        is_distinct=True),
                                                           Literal(dialect, 0)),
                                order_by=[FunctionCall(dialect, "SUM",
                                                       BinaryArithmeticExpression(dialect, "*",
                                                                                  Column(dialect, "quantity", "oi"),
                                                                                  Column(dialect, "price", "p")))],
                                limit=100)

        sql, params = query.to_sql()
        print_sql("Multiple Joins with Aggregation", sql, params)


    def demo_complex_cte_query():
        """Demonstrate complex query with multiple CTEs."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Multiple CTEs with Dependencies")
        print("=" * 70)
        print()

        # CTE 1: High earners
        cte1 = CTEExpression(dialect,
                             name="high_earners",
                             query=("SELECT id, name, salary, department FROM employees WHERE salary > ?",
                                    [75000]),
                             columns=["id", "name", "salary", "department"])

        # CTE 2: Department stats (depends on CTE 1)
        cte2 = CTEExpression(dialect,
                             name="dept_stats",
                             query=("""
                                    SELECT department,
                                           COUNT(*)    as emp_count,
                                           AVG(salary) as avg_salary,
                                           MAX(salary) as max_salary,
                                           MIN(salary) as min_salary
                                    FROM high_earners
                                    GROUP BY department
                                    """, []),
                             columns=["department", "emp_count", "avg_salary", "max_salary", "min_salary"])

        # CTE 3: Top departments
        cte3 = CTEExpression(dialect,
                             name="top_depts",
                             query=("SELECT department FROM dept_stats ORDER BY avg_salary DESC LIMIT ?", [5]),
                             columns=["department"])

        # Main query using all CTEs
        main_query = QueryExpression(dialect,
                                     select=[
                                         Column(dialect, "name", "he"),
                                         Column(dialect, "salary", "he"),
                                         Column(dialect, "department", "he"),
                                         Column(dialect, "emp_count", "ds"),
                                         Column(dialect, "avg_salary", "ds"),
                                         CaseExpression(dialect,
                                                        cases=[
                                                            (ComparisonPredicate(dialect, ">",
                                                                                 Column(dialect, "salary", "he"),
                                                                                 Column(dialect, "avg_salary", "ds")),
                                                             Literal(dialect, "Above Average")),
                                                            (ComparisonPredicate(dialect, "=",
                                                                                 Column(dialect, "salary", "he"),
                                                                                 Column(dialect, "avg_salary", "ds")),
                                                             Literal(dialect, "Average"))
                                                        ],
                                                        else_result=Literal(dialect, "Below Average"))
                                     ],
                                     from_=JoinExpression(dialect,
                                                          left_table=JoinExpression(dialect,
                                                                                    left_table=TableExpression(dialect,
                                                                                                               "high_earners",
                                                                                                               "he"),
                                                                                    right_table=TableExpression(dialect,
                                                                                                                "dept_stats",
                                                                                                                "ds"),
                                                                                    join_type="INNER",
                                                                                    using=["department"]),
                                                          right_table=TableExpression(dialect, "top_depts", "td"),
                                                          join_type="INNER",
                                                          condition=ComparisonPredicate(dialect, "=",
                                                                                        Column(dialect, "department",
                                                                                               "he"),
                                                                                        Column(dialect, "department",
                                                                                               "td"))))

        with_query = WithQueryExpression(dialect,
                                         ctes=[cte1, cte2, cte3],
                                         main_query=main_query)

        sql, params = with_query.to_sql()
        print_sql("Multiple CTEs with Dependencies", sql, params)


    def demo_complex_set_operations():
        """Demonstrate complex nested set operations."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Nested Set Operations")
        print("=" * 70)
        print()

        # Active premium users
        active_premium = Subquery(dialect,
                                  """SELECT user_id
                                     FROM subscriptions
                                     WHERE status = ?
                                       AND tier = ?""",
                                  ("active", "premium"))

        # Recent purchasers
        recent_buyers = Subquery(dialect,
                                 """SELECT DISTINCT user_id
                                    FROM orders
                                    WHERE created_at > ?
                                      AND total > ?""",
                                 ("2024-01-01", 100))

        # Union of active premium and recent buyers
        engaged = SetOperationExpression(dialect,
                                         active_premium,
                                         recent_buyers,
                                         "UNION",
                                         "engaged_users")

        # Active trial users
        trial_users = Subquery(dialect,
                               """SELECT user_id
                                  FROM subscriptions
                                  WHERE status = ?
                                    AND tier = ?""",
                               ("active", "trial"))

        # All valuable users (union of engaged and trial)
        valuable = SetOperationExpression(dialect,
                                          engaged,
                                          trial_users,
                                          "UNION",
                                          "valuable_users")

        # Banned users
        banned = Subquery(dialect,
                          "SELECT user_id FROM banned_users",
                          ())

        # Inactive users
        inactive = Subquery(dialect,
                            """SELECT user_id
                               FROM users
                               WHERE last_login < ?""",
                            ("2023-01-01",))

        # Users to exclude (union of banned and inactive)
        exclude = SetOperationExpression(dialect,
                                         banned,
                                         inactive,
                                         "UNION",
                                         "excluded_users")

        # Final result: valuable users minus excluded users
        final = SetOperationExpression(dialect,
                                       valuable,
                                       exclude,
                                       "EXCEPT",
                                       "target_users")

        sql, params = final.to_sql()
        print_sql("Complex Nested Set Operations", sql, params)


    def demo_complex_subqueries():
        """Demonstrate complex correlated and scalar subqueries."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Correlated and Scalar Subqueries")
        print("=" * 70)
        print()

        # --- Subquery 1: Order Count ---
        order_count_sql = "SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id"
        order_count_params = ()

        # Version for WHERE clause (no alias)
        order_count_sub_for_where = Subquery(dialect, order_count_sql, order_count_params)
        # Version for SELECT list (with alias)
        order_count_sub_for_select = Subquery(dialect, order_count_sql, order_count_params, alias="order_count")

        # --- Subquery 2: Total Spent ---
        total_spent_sql = "SELECT COALESCE(SUM(total), 0) FROM orders o WHERE o.user_id = u.id AND o.status = ?"
        total_spent_params = ("completed",)

        # Version for WHERE clause (no alias)
        total_spent_sub_for_where = Subquery(dialect, total_spent_sql, total_spent_params)
        # Version for SELECT list (with alias)
        total_spent_sub_for_select = Subquery(dialect, total_spent_sql, total_spent_params, alias="total_spent")

        # --- Subquery 3: Average Order Value (only used in SELECT) ---
        avg_order_sub_for_select = Subquery(dialect,
                                            "SELECT AVG(total) FROM orders o WHERE o.user_id = u.id",
                                            (),
                                            alias="avg_order_value")

        query = QueryExpression(dialect,
                                select=[
                                    Column(dialect, "id", "u"),
                                    Column(dialect, "name", "u"),
                                    Column(dialect, "email", "u"),
                                    order_count_sub_for_select,
                                    total_spent_sub_for_select,
                                    avg_order_sub_for_select
                                ],
                                from_=TableExpression(dialect, "users", "u"),
                                where=LogicalPredicate(dialect, "AND",
                                                       ComparisonPredicate(dialect, ">",
                                                                           order_count_sub_for_where,
                                                                           Literal(dialect, 0)),
                                                       ComparisonPredicate(dialect, ">",
                                                                           total_spent_sub_for_where,
                                                                           Literal(dialect, 1000))))

        sql, params = query.to_sql()
        print_sql("Scalar Subqueries in SELECT", sql, params)

        # EXISTS with correlated subquery
        exists_sub = Subquery(dialect,
                              """SELECT 1
                                 FROM orders o
                                 WHERE o.user_id = u.id
                                   AND o.total > ?
                                   AND o.created_at > ?""",
                              (1000, "2024-01-01"))
        exists_pred = ExistsExpression(dialect, exists_sub)

        query = QueryExpression(dialect,
                                select=[Column(dialect, "name", "u"),
                                        Column(dialect, "email", "u"),
                                        Column(dialect, "created_at", "u")],
                                from_=TableExpression(dialect, "users", "u"),
                                where=LogicalPredicate(dialect, "AND",
                                                       exists_pred,
                                                       ComparisonPredicate(dialect, ">",
                                                                           Column(dialect, "created_at", "u"),
                                                                           Literal(dialect, "2023-01-01"))))

        sql, params = query.to_sql()
        print_sql("EXISTS with Correlated Subquery", sql, params)


    def demo_complex_window_query():
        """Demonstrate complex window functions with frames."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Window Functions with Multiple Partitions")
        print("=" * 70)
        print()

        # Row number within partition
        row_num = FunctionCall(dialect, "ROW_NUMBER")
        window1 = WindowExpression(dialect,
                                   row_num,
                                   partition_by=[Column(dialect, "department")],
                                   order_by=[Column(dialect, "salary")],
                                   alias="dept_rank")

        # Running total with frame
        sum_func = FunctionCall(dialect, "SUM", Column(dialect, "salary"))
        window2 = WindowExpression(dialect,
                                   sum_func,
                                   partition_by=[Column(dialect, "department")],
                                   order_by=[Column(dialect, "hire_date")],
                                   frame_type="ROWS",
                                   frame_start="UNBOUNDED PRECEDING",
                                   frame_end="CURRENT ROW",
                                   alias="cumulative_salary")

        # Moving average (3-row window)
        avg_func = FunctionCall(dialect, "AVG", Column(dialect, "salary"))
        window3 = WindowExpression(dialect,
                                   avg_func,
                                   partition_by=[Column(dialect, "department")],
                                   order_by=[Column(dialect, "hire_date")],
                                   frame_type="ROWS",
                                   frame_start="2 PRECEDING",
                                   frame_end="CURRENT ROW",
                                   alias="moving_avg")

        # LAG to compare with previous
        lag_func = FunctionCall(dialect, "LAG", Column(dialect, "salary"), Literal(dialect, 1))
        window4 = WindowExpression(dialect,
                                   lag_func,
                                   partition_by=[Column(dialect, "department")],
                                   order_by=[Column(dialect, "hire_date")],
                                   alias="prev_salary")

        query = QueryExpression(dialect,
                                select=[
                                    Column(dialect, "id"),
                                    Column(dialect, "name"),
                                    Column(dialect, "department"),
                                    Column(dialect, "salary"),
                                    Column(dialect, "hire_date"),
                                    window1,
                                    window2,
                                    window3,
                                    window4,
                                    BinaryArithmeticExpression(dialect, "-",
                                                               Column(dialect, "salary"),
                                                               window4)
                                ],
                                from_=TableExpression(dialect, "employees"))

        sql, params = query.to_sql()
        print_sql("Complex Window Functions", sql, params)


    # ========== Main Execution ==========

    print("\n")
    print("=" * 70)
    print("Dummy Dialect - Complete Expression Demonstrations")
    print("=" * 70)
    print("\n")

    # Part 1: Basic Expressions
    demo_literals()
    demo_identifiers()
    demo_columns()
    demo_tables()
    demo_functions()
    demo_filter_clause()
    demo_subqueries()

    # Part 2: Operators
    demo_arithmetic()
    demo_binary_operators()
    demo_unary_operators()
    demo_raw_sql()
    demo_sql_operations()

    # Part 3: Predicates
    demo_comparisons()
    demo_logical()
    demo_in_predicate()
    demo_between()
    demo_is_null()
    demo_like()

    # Part 4: Advanced Functions
    demo_case()
    demo_cast()
    demo_exists()
    demo_any_all()
    demo_window()
    demo_json()
    demo_array()
    demo_ordered_set_aggregation()

    # Part 5: Query Clauses
    demo_joins()
    demo_cte()
    demo_set_operations()
    demo_grouping()
    demo_values()
    demo_table_functions()
    demo_json_table()
    demo_lateral()

    # Part 6: Complete Statements
    demo_select()
    demo_insert()
    demo_update()
    demo_delete()
    demo_explain()
    demo_merge_statement()
    demo_temporal_tables()
    demo_qualify_clause()
    demo_for_update_skip_locked()

    # Part 7: Complex Scenarios
    demo_complex_join_query()
    demo_complex_cte_query()
    demo_complex_set_operations()
    demo_complex_subqueries()
    demo_complex_window_query()

    print("=" * 70)
    print("All demonstrations completed successfully!")
    print("=" * 70)