# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

SQLite is a lightweight database with limited support for advanced SQL features.
This dialect implements only the protocols for features that SQLite actually supports.
"""
from typing import Any, List, Optional, Tuple

from rhosocial.activerecord.backend.dialect import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport,
    ReturningSupport,
    JSONSupport
)


class SQLiteDialect(
    BaseDialect,
    CTESupport,
    ReturningSupport,
    JSONSupport
):
    """
    SQLite dialect implementation.

    SQLite supports:
    - Basic and recursive CTEs (since 3.8.3)
    - RETURNING clause (since 3.35.0)
    - JSON operations (with JSON1 extension, since 3.38.0)

    SQLite does NOT support:
    - Window functions (requires 3.25.0+, not implemented here for minimum version)
    - Advanced grouping (ROLLUP, CUBE, GROUPING SETS)
    - LATERAL joins
    - Array types
    - UPSERT with ON CONFLICT syntax (has INSERT OR REPLACE but different semantics)
    """

    def get_placeholder(self) -> str:
        """SQLite uses '?' for placeholders."""
        return "?"

    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since SQLite 3.8.3."""
        return True

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since SQLite 3.8.3."""
        return True

    def supports_materialized_cte(self) -> bool:
        """SQLite does not support MATERIALIZED hint."""
        return False

    def supports_returning_clause(self) -> bool:
        """RETURNING clause is supported since SQLite 3.35.0."""
        return True

    def format_returning_clause(
        self,
        columns: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format RETURNING clause for SQLite.

        Args:
            columns: List of column names

        Returns:
            Tuple of (SQL string, empty parameters tuple)
        """
        cols = [self.format_identifier(c) for c in columns]
        return f"RETURNING {', '.join(cols)}", ()

    def supports_json_type(self) -> bool:
        """JSON is supported with JSON1 extension."""
        return True

    def get_json_access_operator(self) -> str:
        """SQLite uses '->' for JSON access."""
        return "->"

    def format_limit_offset(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[Optional[str], List[Any]]:
        """
        Format LIMIT/OFFSET clause with SQLite-specific handling.

        SQLite requires LIMIT when using OFFSET alone, so we use LIMIT -1
        to indicate "no limit" when only OFFSET is specified.

        Args:
            limit: Optional row limit
            offset: Optional row offset

        Returns:
            Tuple of (SQL string or None, parameters list)
        """
        if offset is not None and limit is None:
            return "LIMIT -1 OFFSET ?", [offset]
        return super().format_limit_offset(limit, offset)


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
        ExplainExpression, SQLOperation
    )

    dialect = SQLiteDialect()


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

        # Integer literal
        lit = Literal(dialect, 42)
        sql, params = lit.to_sql()
        print_sql("Integer Literal", sql, params)

        # String literal
        lit = Literal(dialect, "hello world")
        sql, params = lit.to_sql()
        print_sql("String Literal", sql, params)

        # NULL literal
        lit = Literal(dialect, None)
        sql, params = lit.to_sql()
        print_sql("NULL Literal", sql, params)

        # List literal (for IN clause)
        lit = Literal(dialect, [1, 2, 3])
        sql, params = lit.to_sql()
        print_sql("List Literal", sql, params)


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

        expr = BinaryArithmeticExpression(dialect, "*",
                                          Column(dialect, "quantity"),
                                          Column(dialect, "unit_price"))
        sql, params = expr.to_sql()
        print_sql("Multiplication", sql, params)

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
        print_sql("Negation", sql, params)


    def demo_raw_sql():
        """Demonstrate raw SQL expressions."""
        print("=" * 70)
        print("RAW SQL EXPRESSIONS")
        print("=" * 70)
        print()

        expr = RawSQLExpression(dialect, "CURRENT_TIMESTAMP")
        sql, params = expr.to_sql()
        print_sql("Current Timestamp", sql, params)

        expr = RawSQLExpression(dialect, "datetime('now', 'localtime')")
        sql, params = expr.to_sql()
        print_sql("SQLite Date Function", sql, params)


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
        print_sql("BETWEEN", sql, params)

        pred = BetweenPredicate(dialect,
                                Column(dialect, "created_at"),
                                Literal(dialect, "2024-01-01"),
                                Literal(dialect, "2024-12-31"))
        sql, params = pred.to_sql()
        print_sql("BETWEEN Dates", sql, params)


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
        print_sql("LIKE", sql, params)

        pred = LikePredicate(dialect, "NOT LIKE",
                             Column(dialect, "email"),
                             Literal(dialect, "%@spam.com"))
        sql, params = pred.to_sql()
        print_sql("NOT LIKE", sql, params)


    # ========== Part 4: Advanced Functions ==========

    def demo_case():
        """Demonstrate CASE expressions."""
        print("=" * 70)
        print("CASE EXPRESSIONS")
        print("=" * 70)
        print()

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


    def demo_cast():
        """Demonstrate CAST expressions."""
        print("=" * 70)
        print("CAST EXPRESSIONS")
        print("=" * 70)
        print()

        expr = CastExpression(dialect, Column(dialect, "price"), "INTEGER")
        sql, params = expr.to_sql()
        print_sql("CAST to INTEGER", sql, params)

        expr = CastExpression(dialect, Column(dialect, "amount"), "REAL")
        sql, params = expr.to_sql()
        print_sql("CAST to REAL", sql, params)


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
        print_sql("ANY", sql, params)

        all_expr = AllExpression(dialect,
                                 Column(dialect, "price"),
                                 ">",
                                 Literal(dialect, [50, 75]))
        sql, params = all_expr.to_sql()
        print_sql("ALL", sql, params)


    def demo_window():
        """Demonstrate window functions (SQLite 3.25.0+)."""
        print("=" * 70)
        print("WINDOW FUNCTIONS (SQLite 3.25.0+)")
        print("=" * 70)
        print()

        version = dialect.get_server_version() if hasattr(dialect, 'get_server_version') else (3, 35, 0)

        if version >= (3, 25, 0):
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
            print_sql("ROW_NUMBER() OVER (ORDER BY ...)", sql, params)
        else:
            print("Window functions not supported in SQLite < 3.25.0")
            print()


    def demo_json():
        """Demonstrate JSON operations (SQLite with JSON1 extension)."""
        print("=" * 70)
        print("JSON OPERATIONS (JSON1 extension)")
        print("=" * 70)
        print()

        json_expr = JSONExpression(dialect,
                                   Column(dialect, "data"),
                                   "$.name")
        sql, params = json_expr.to_sql()
        print_sql("JSON Extract", sql, params)

        json_expr = JSONExpression(dialect,
                                   Column(dialect, "metadata"),
                                   "$.settings.theme",
                                   operation="->>")
        sql, params = json_expr.to_sql()
        print_sql("JSON Extract as Text", sql, params)


    def demo_array():
        """Demonstrate array operations (not natively supported in SQLite)."""
        print("=" * 70)
        print("ARRAY OPERATIONS (Not Natively Supported)")
        print("=" * 70)
        print()

        print("SQLite does not natively support array types.")
        print("Arrays must be stored as JSON or delimited strings.")
        print()

        # Array constructor (would work in PostgreSQL)
        array = ArrayExpression(dialect, "CONSTRUCTOR",
                                elements=[Literal(dialect, 1),
                                          Literal(dialect, 2),
                                          Literal(dialect, 3)])
        sql, params = array.to_sql()
        print_sql("Array Constructor (PostgreSQL syntax)", sql, params)


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

        # USING clause
        join = JoinExpression(dialect,
                              left_table=TableExpression(dialect, "orders", "o"),
                              right_table=TableExpression(dialect, "order_items", "oi"),
                              join_type="INNER",
                              using=["order_id"])
        sql, params = join.to_sql()
        print_sql("JOIN with USING", sql, params)


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


    def demo_set_operations():
        """Demonstrate set operations (UNION, INTERSECT, EXCEPT)."""
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

        except_op = SetOperationExpression(dialect,
                                           query1, query2,
                                           "EXCEPT", "difference")
        sql, params = except_op.to_sql()
        print_sql("EXCEPT", sql, params)


    def demo_grouping():
        """Demonstrate grouping operations."""
        print("=" * 70)
        print("GROUPING OPERATIONS")
        print("=" * 70)
        print()

        # Basic GROUP BY
        group = GroupExpression(dialect, [Column(dialect, "department")])
        sql, params = group.to_sql()
        print_sql("GROUP BY", sql, params)

        # Multiple columns
        group = GroupExpression(dialect, [
            Column(dialect, "department"),
            Column(dialect, "category")
        ])
        sql, params = group.to_sql()
        print_sql("GROUP BY Multiple", sql, params)

        # Advanced grouping - Demonstrating lack of support
        print("--- ROLLUP (Demonstrating lack of support) ---")
        try:
            rollup = GroupingExpression(dialect, "ROLLUP", [
                Column(dialect, "year"),
                Column(dialect, "quarter"),
                Column(dialect, "month")
            ])
            rollup.to_sql()
        except UnsupportedFeatureError as e:
            print(f"Correctly failed as expected: {e}")
        print()

        print("--- CUBE (Demonstrating lack of support) ---")
        try:
            cube = GroupingExpression(dialect, "CUBE", [
                Column(dialect, "region"),
                Column(dialect, "product")
            ])
            cube.to_sql()
        except UnsupportedFeatureError as e:
            print(f"Correctly failed as expected: {e}")
        print()

        print("--- GROUPING SETS (Demonstrating lack of support) ---")
        try:
            grouping_sets = GroupingExpression(dialect, "GROUPING SETS", [
                Column(dialect, "country"),
                Column(dialect, "city")
            ])
            grouping_sets.to_sql()
        except UnsupportedFeatureError as e:
            print(f"Correctly failed as expected: {e}")
        print()


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
        print_sql("VALUES", sql, params)


    def demo_table_functions():
        """Demonstrate table functions (limited in SQLite)."""
        print("=" * 70)
        print("TABLE FUNCTIONS")
        print("=" * 70)
        print()

        print("SQLite has limited table function support.")
        print("Example: json_each() for JSON arrays")
        print()

        func = TableFunctionExpression(dialect,
                                       "json_each",
                                       Column(dialect, "json_data"),
                                       alias="j",
                                       column_names=["key", "value"])
        sql, params = func.to_sql()
        print_sql("json_each() Table Function", sql, params)


    def demo_lateral():
        """Demonstrate LATERAL joins (not supported in SQLite)."""
        print("=" * 70)
        print("LATERAL JOINS (NOT SUPPORTED)")
        print("=" * 70)
        print()

        print("SQLite does not support LATERAL joins")
        print()


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
                                limit=10)
        sql, params = query.to_sql()
        print_sql("SELECT with ORDER BY and LIMIT", sql, params)

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

        # INSERT with RETURNING (SQLite 3.35.0+)
        version = (3, 35, 0)  # Assume supported version
        if version >= (3, 35, 0):
            print("--- INSERT with RETURNING (SQLite 3.35.0+) ---")
            print(f"SQL: {sql} RETURNING id, created_at")
            if params:
                print(f"Parameters: {params}")
            print()


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
                                  {"status": Literal(dialect, "shipped")},
                                  LogicalPredicate(dialect, "AND",
                                                   ComparisonPredicate(dialect, "=",
                                                                       Column(dialect, "status"),
                                                                       Literal(dialect, "pending")),
                                                   ComparisonPredicate(dialect, "<",
                                                                       Column(dialect, "created_at"),
                                                                       Literal(dialect, "2024-01-01"))))
        sql, params = update.to_sql()
        print_sql("UPDATE with Complex WHERE", sql, params)


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
                                                                   Column(dialect, "user_id"),
                                                                   is_not=False),
                                                   ComparisonPredicate(dialect, "<",
                                                                       Column(dialect, "created_at"),
                                                                       Literal(dialect, "2023-01-01"))))
        sql, params = delete.to_sql()
        print_sql("DELETE with Complex WHERE", sql, params)


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


    # ========== Part 7: Complex Scenarios ==========

    def demo_complex_join_query():
        """Demonstrate complex query with multiple joins."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Multiple Joins")
        print("=" * 70)
        print()

        # Build the FROM clause with joins
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

        query = QueryExpression(dialect,
                                select=[
                                    Column(dialect, "name", "u"),
                                    FunctionCall(dialect, "COUNT",
                                                 Column(dialect, "id", "o"),
                                                 alias="order_count"),
                                    FunctionCall(dialect, "SUM",
                                                 Column(dialect, "quantity", "oi"),
                                                 alias="total_items")
                                ],
                                from_=with_items,
                                group_by=[Column(dialect, "id", "u")],
                                order_by=[FunctionCall(dialect, "COUNT",
                                                       Column(dialect, "id", "o"))])

        sql, params = query.to_sql()
        print_sql("Multiple Joins with Aggregation", sql, params)


    def demo_complex_cte_query():
        """Demonstrate complex query with CTEs."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Multiple CTEs")
        print("=" * 70)
        print()

        # First CTE: high earners
        cte1 = CTEExpression(dialect,
                             name="high_earners",
                             query=("SELECT id, name, salary, department FROM employees WHERE salary > ?",
                                    [75000]),
                             columns=["id", "name", "salary", "department"])

        # Second CTE: department stats
        cte2 = CTEExpression(dialect,
                             name="dept_stats",
                             query=("""
                                    SELECT department,
                                           COUNT(*)    as emp_count,
                                           AVG(salary) as avg_salary
                                    FROM high_earners
                                    GROUP BY department
                                    """, []),
                             columns=["department", "emp_count", "avg_salary"])

        # Main query using both CTEs
        main_query = QueryExpression(dialect,
                                     select=[
                                         Column(dialect, "name", "he"),
                                         Column(dialect, "salary", "he"),
                                         Column(dialect, "emp_count", "ds"),
                                         Column(dialect, "avg_salary", "ds")
                                     ],
                                     from_=JoinExpression(dialect,
                                                          left_table=TableExpression(dialect, "high_earners", "he"),
                                                          right_table=TableExpression(dialect, "dept_stats", "ds"),
                                                          join_type="INNER",
                                                          using=["department"]))

        with_query = WithQueryExpression(dialect,
                                         ctes=[cte1, cte2],
                                         main_query=main_query)

        sql, params = with_query.to_sql()
        print_sql("Multiple CTEs with Join", sql, params)


    def demo_complex_set_operations():
        """Demonstrate complex set operations."""
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
                                    WHERE created_at > ?""",
                                 ("2024-01-01",))

        # Union of both
        union_result = SetOperationExpression(dialect,
                                              active_premium,
                                              recent_buyers,
                                              "UNION",
                                              "engaged_users")

        # Exclude banned users
        banned = Subquery(dialect,
                          "SELECT user_id FROM banned_users",
                          ())

        final_result = SetOperationExpression(dialect,
                                              union_result,
                                              banned,
                                              "EXCEPT",
                                              "target_users")

        sql, params = final_result.to_sql()
        print_sql("Nested Set Operations", sql, params)


    def demo_complex_subqueries():
        """Demonstrate complex subqueries."""
        print("=" * 70)
        print("COMPLEX SCENARIO: Correlated Subqueries")
        print("=" * 70)
        print()

        # Subquery in SELECT
        subquery = Subquery(dialect,
                            """SELECT COUNT(*)
                               FROM orders o
                               WHERE o.user_id = u.id""",
                            ())

        query = QueryExpression(dialect,
                                select=[
                                    Column(dialect, "name", "u"),
                                    FunctionCall(dialect, "SUBQUERY", subquery, alias="order_count")
                                ],
                                from_=TableExpression(dialect, "users", "u"))

        sql, params = query.to_sql()
        print_sql("Subquery in SELECT", sql, params)

        # EXISTS subquery
        exists_sub = Subquery(dialect,
                              """SELECT 1
                                 FROM orders o
                                 WHERE o.user_id = u.id
                                   AND o.total > ?""",
                              (1000,))
        exists_pred = ExistsExpression(dialect, exists_sub)

        query = QueryExpression(dialect,
                                select=[Column(dialect, "name", "u"),
                                        Column(dialect, "email", "u")],
                                from_=TableExpression(dialect, "users", "u"),
                                where=exists_pred)

        sql, params = query.to_sql()
        print_sql("Correlated Subquery with EXISTS", sql, params)


    # ========== Main Execution ==========

    print("\n")
    print("=" * 70)
    print("SQLite Dialect - Complete Expression Demonstrations")
    print("=" * 70)
    print("\n")

    # Part 1: Basic Expressions
    demo_literals()
    demo_identifiers()
    demo_columns()
    demo_tables()
    demo_functions()

    # Part 2: Operators
    demo_arithmetic()
    demo_binary_operators()
    demo_unary_operators()
    demo_raw_sql()

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

    # Part 5: Query Clauses
    demo_joins()
    demo_cte()
    demo_set_operations()
    demo_grouping()
    demo_values()
    demo_table_functions()
    demo_lateral()

    # Part 6: Complete Statements
    demo_select()
    demo_insert()
    demo_update()
    demo_delete()
    demo_explain()

    # Part 7: Complex Scenarios
    demo_complex_join_query()
    demo_complex_cte_query()
    demo_complex_set_operations()
    demo_complex_subqueries()

    print("=" * 70)
    print("All demonstrations completed successfully!")
    print("=" * 70)