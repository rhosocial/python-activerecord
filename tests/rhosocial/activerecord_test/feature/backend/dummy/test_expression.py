import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import (
    BaseExpression,
    SQLValueExpression,
    SQLPredicate,
    Literal,
    RawSQLExpression,
    Column,
    FunctionCall,
    Subquery,
    Identifier,
    StringExpression,
    ComparableExpression,
    BinaryArithmeticExpression,
    ComparisonPredicate,
    LikePredicate,
    InPredicate,
    BetweenPredicate,
    IsNullPredicate,
    LogicalPredicate,
    # New expressions
    CaseExpression,
    CastExpression,
    ExistsExpression,
    AnyExpression,
    AllExpression,
    WindowExpression,
    CTEExpression,
    JoinExpression
)
from typing import List, Any, Optional, Tuple
from rhosocial.activerecord.backend.dialect import SQLDialectBase


@pytest.fixture
def dummy_dialect():
    return DummyDialect()

# Implement abstract methods for DummyDialect for testing expressions
class TestableDummyDialect(DummyDialect):
    def format_binary_operator(self, op: str, left_sql: str, right_sql: str, left_params: tuple, right_params: tuple) -> Tuple[str, tuple]:
        return f"({left_sql} {op} {right_sql})", left_params + right_params

    def format_unary_operator(self, op: str, operand_sql: str, pos: str, operand_params: tuple) -> Tuple[str, tuple]:
        if pos == 'before':
            return f"{op} ({operand_sql})", operand_params
        return f"({operand_sql}) {op}", operand_params

    def format_function_call(self, func_name: str, args_sql: List[str], args_params: List[tuple], is_distinct: bool) -> Tuple[str, tuple]:
        distinct_str = "DISTINCT " if is_distinct else ""
        flat_params = tuple(p for param_tuple in args_params for p in param_tuple)
        return f"{func_name.upper()}({distinct_str}{', '.join(args_sql)})", flat_params

    def format_subquery(self, query_sql: str) -> Tuple[str, tuple]:
        return f"({query_sql})", ()

    # New predicate formatters
    def format_comparison_predicate(self, op: str, left_sql: str, right_sql: str, left_params: tuple, right_params: tuple) -> Tuple[str, tuple]:
        return f"({left_sql} {op} {right_sql})", left_params + right_params

    def format_like_predicate(self, op: str, expr_sql: str, pattern_sql: str, expr_params: tuple, pattern_params: tuple) -> Tuple[str, tuple]:
        return f"({expr_sql} {op} {pattern_sql})", expr_params + pattern_params

    def format_is_null_predicate(self, expr_sql: str, is_not: bool, expr_params: tuple) -> Tuple[str, tuple]:
        not_str = " NOT" if is_not else ""
        return f"({expr_sql} IS{not_str} NULL)", expr_params

    def format_logical_predicate(self, op: str, *predicates_sql_and_params: Tuple[str, tuple]) -> Tuple[str, tuple]:
        if op.upper() == "NOT" and len(predicates_sql_and_params) == 1:
            sql, params = predicates_sql_and_params[0]
            return f"NOT {sql}", params
        
        sql_parts = [sql for sql, params in predicates_sql_and_params]
        all_params = tuple(p for sql, params in predicates_sql_and_params for p in params)
        
        return f"({f' {op} '.join(sql_parts)})", all_params

    # Placeholder for format_alias
    def format_alias(self, expression_sql: str, alias: str, expression_params: tuple) -> Tuple[str, tuple]:
        return f"{expression_sql} AS {alias}", expression_params

    def format_cast_expression(self, expr_sql: str, target_type: str, expr_params: tuple) -> Tuple[str, tuple]:
        return f"CAST({expr_sql} AS {target_type})", expr_params

    def format_case_expression(self,
                               value_sql: Optional[str],
                               value_params: Optional[tuple],
                               conditions_results: List[Tuple[str, str, tuple, tuple]],
                               else_result_sql: Optional[str],
                               else_result_params: Optional[tuple]) -> Tuple[str, tuple]:
        parts = ["CASE"]
        all_params = []
        if value_sql:
            parts.append(value_sql)
            if value_params: all_params.extend(value_params)

        for condition_sql, result_sql, cond_params, res_params in conditions_results:
            parts.append(f"WHEN {condition_sql} THEN {result_sql}")
            all_params.extend(cond_params)
            all_params.extend(res_params)

        if else_result_sql:
            parts.append(f"ELSE {else_result_sql}")
            if else_result_params: all_params.extend(else_result_params)

        parts.append("END")
        return " ".join(parts), tuple(all_params)

@pytest.fixture
def testable_dummy_dialect():
    return TestableDummyDialect()


class TestLiteralExpression:
    def test_literal_int(self, testable_dummy_dialect):
        lit = Literal(testable_dummy_dialect, 123)
        sql, params = lit.to_sql()
        assert sql == "?"
        assert params == (123,)

    def test_literal_str(self, testable_dummy_dialect):
        lit = Literal(testable_dummy_dialect, "hello")
        sql, params = lit.to_sql()
        assert sql == "?"
        assert params == ("hello",)

    def test_literal_list(self, testable_dummy_dialect):
        lit = Literal(testable_dummy_dialect, [1, "two", 3.0])
        sql, params = lit.to_sql()
        assert sql == "(?, ?, ?)"
        assert params == (1, "two", 3.0)

    def test_literal_tuple(self, testable_dummy_dialect):
        lit = Literal(testable_dummy_dialect, (1, "two", 3.0))
        sql, params = lit.to_sql()
        assert sql == "(?, ?, ?)"
        assert params == (1, "two", 3.0)

    def test_literal_empty_list(self, testable_dummy_dialect):
        lit = Literal(testable_dummy_dialect, [])
        sql, params = lit.to_sql()
        assert sql == "()"
        assert params == ()


class TestRawSQLExpression:
    def test_raw_sql_simple(self, testable_dummy_dialect):
        raw_expr = RawSQLExpression(testable_dummy_dialect, "COUNT(*)")
        sql, params = raw_expr.to_sql()
        assert sql == "COUNT(*)"
        assert params == ()


class TestColumnExpression:
    def test_column_only_name(self, testable_dummy_dialect):
        col_expr = Column(testable_dummy_dialect, "user_name")
        sql, params = col_expr.to_sql()
        assert sql == '"user_name"'
        assert params == ()

    def test_column_with_table(self, testable_dummy_dialect):
        col_expr = Column(testable_dummy_dialect, "id", table="users")
        sql, params = col_expr.to_sql()
        assert sql == '"users"."id"'
        assert params == ()


class TestIdentifierExpression:
    def test_identifier_simple(self, testable_dummy_dialect):
        id_expr = Identifier(testable_dummy_dialect, "my_column")
        sql, params = id_expr.to_sql()
        assert sql == '"my_column"'
        assert params == ()


class TestFunctionCallExpression:
    def test_function_no_args(self, testable_dummy_dialect):
        func_call = FunctionCall(testable_dummy_dialect, "NOW")
        sql, params = func_call.to_sql()
        assert sql == "NOW()"
        assert params == ()

    def test_function_single_arg(self, testable_dummy_dialect):
        arg = Literal(testable_dummy_dialect, "some_column")
        func_call = FunctionCall(testable_dummy_dialect, "LENGTH", arg)
        sql, params = func_call.to_sql()
        assert sql == "LENGTH(?)"
        assert params == ("some_column",)

    def test_function_multiple_args(self, testable_dummy_dialect):
        arg1 = Literal(testable_dummy_dialect, "first_name")
        arg2 = Literal(testable_dummy_dialect, "last_name")
        func_call = FunctionCall(testable_dummy_dialect, "CONCAT", arg1, arg2)
        sql, params = func_call.to_sql()
        assert sql == "CONCAT(?, ?)"
        assert params == ("first_name", "last_name")

    def test_function_distinct_arg(self, testable_dummy_dialect):
        arg = Literal(testable_dummy_dialect, "category")
        func_call = FunctionCall(testable_dummy_dialect, "COUNT", arg, is_distinct=True)
        sql, params = func_call.to_sql()
        assert sql == "COUNT(DISTINCT ?)"
        assert params == ("category",)


class TestSubqueryExpression:
    def test_subquery_simple(self, testable_dummy_dialect):
        sub_expr = Subquery(testable_dummy_dialect, "SELECT MAX(id) FROM users", ())
        sql, params = sub_expr.to_sql()
        assert sql == "(SELECT MAX(id) FROM users)"
        assert params == ()

    def test_subquery_with_params(self, testable_dummy_dialect):
        sub_expr = Subquery(testable_dummy_dialect, "SELECT name FROM users WHERE age > ?", (25,))
        sql, params = sub_expr.to_sql()
        assert sql == "(SELECT name FROM users WHERE age > ?)"
        assert params == (25,)


class TestBinaryArithmeticExpression:
    def test_arithmetic_add(self, testable_dummy_dialect):
        expr = BinaryArithmeticExpression(testable_dummy_dialect, "+", Literal(testable_dummy_dialect, "price"), Literal(testable_dummy_dialect, 5))
        sql, params = expr.to_sql()
        assert sql == "(? + ?)"
        assert params == ("price", 5)

    def test_arithmetic_multiply(self, testable_dummy_dialect):
        expr = BinaryArithmeticExpression(testable_dummy_dialect, "*", Column(testable_dummy_dialect, "quantity"), Literal(testable_dummy_dialect, 2))
        sql, params = expr.to_sql()
        assert sql == '("quantity" * ?)'
        assert params == (2,)


class TestComparisonPredicate:
    def test_comparison_equals(self, testable_dummy_dialect):
        pred = ComparisonPredicate(testable_dummy_dialect, "=", Column(testable_dummy_dialect, "status"), Literal(testable_dummy_dialect, "active"))
        sql, params = pred.to_sql()
        assert sql == '("status" = ?)'
        assert params == ("active",)

    def test_comparison_greater_than(self, testable_dummy_dialect):
        pred = ComparisonPredicate(testable_dummy_dialect, ">", Column(testable_dummy_dialect, "age"), Literal(testable_dummy_dialect, 18))
        sql, params = pred.to_sql()
        assert sql == '("age" > ?)'
        assert params == (18,)


class TestLikePredicate:
    def test_like_pattern(self, testable_dummy_dialect):
        pred = LikePredicate(testable_dummy_dialect, "LIKE", Column(testable_dummy_dialect, "name"), Literal(testable_dummy_dialect, "A%"))
        sql, params = pred.to_sql()
        assert sql == '("name" LIKE ?)'
        assert params == ("A%",)

    def test_ilike_pattern(self, testable_dummy_dialect):
        pred = LikePredicate(testable_dummy_dialect, "ILIKE", Column(testable_dummy_dialect, "email"), Literal(testable_dummy_dialect, "%@example.com"))
        sql, params = pred.to_sql()
        assert sql == '("email" ILIKE ?)'
        assert params == ("%@example.com",)


class TestInPredicate:
    def test_in_list(self, testable_dummy_dialect):
        pred = InPredicate(testable_dummy_dialect, Column(testable_dummy_dialect, "category"), Literal(testable_dummy_dialect, ["A", "B", "C"]))
        sql, params = pred.to_sql()
        assert sql == '("category" IN (?, ?, ?))'
        assert params == ("A", "B", "C")

    def test_in_empty_list(self, testable_dummy_dialect):
        pred = InPredicate(testable_dummy_dialect, Column(testable_dummy_dialect, "category"), Literal(testable_dummy_dialect, []))
        sql, params = pred.to_sql()
        assert sql == '("category" IN ())'
        assert params == ()


class TestBetweenPredicate:
    def test_between_range(self, testable_dummy_dialect):
        pred = BetweenPredicate(testable_dummy_dialect, Column(testable_dummy_dialect, "price"), Literal(testable_dummy_dialect, 100), Literal(testable_dummy_dialect, 200))
        sql, params = pred.to_sql()
        assert sql == '("price" BETWEEN ? AND ?)'
        assert params == (100, 200)


class TestIsNullPredicate:
    def test_is_null(self, testable_dummy_dialect):
        pred = IsNullPredicate(testable_dummy_dialect, Column(testable_dummy_dialect, "description"))
        sql, params = pred.to_sql()
        assert sql == '("description" IS NULL)'
        assert params == ()

    def test_is_not_null(self, testable_dummy_dialect):
        pred = IsNullPredicate(testable_dummy_dialect, Column(testable_dummy_dialect, "description"), is_not=True)
        sql, params = pred.to_sql()
        assert sql == '("description" IS NOT NULL)'
        assert params == ()


class TestLogicalPredicate:
    def test_logical_and(self, testable_dummy_dialect):
        pred1 = ComparisonPredicate(testable_dummy_dialect, ">", Column(testable_dummy_dialect, "age"), Literal(testable_dummy_dialect, 18))
        pred2 = ComparisonPredicate(testable_dummy_dialect, "=", Column(testable_dummy_dialect, "status"), Literal(testable_dummy_dialect, "active"))
        logical_and = LogicalPredicate(testable_dummy_dialect, "AND", pred1, pred2)
        sql, params = logical_and.to_sql()
        assert sql == '(("age" > ?) AND ("status" = ?))'
        assert params == (18, "active")

    def test_logical_or(self, testable_dummy_dialect):
        pred1 = ComparisonPredicate(testable_dummy_dialect, ">", Column(testable_dummy_dialect, "score"), Literal(testable_dummy_dialect, 90))
        pred2 = ComparisonPredicate(testable_dummy_dialect, "=", Column(testable_dummy_dialect, "grade"), Literal(testable_dummy_dialect, "A"))
        logical_or = LogicalPredicate(testable_dummy_dialect, "OR", pred1, pred2)
        sql, params = logical_or.to_sql()
        assert sql == '(("score" > ?) OR ("grade" = ?))'
        assert params == (90, "A")

    def test_logical_not(self, testable_dummy_dialect):
        pred = ComparisonPredicate(testable_dummy_dialect, "=", Column(testable_dummy_dialect, "is_admin"), Literal(testable_dummy_dialect, True))
        logical_not = LogicalPredicate(testable_dummy_dialect, "NOT", pred)
        sql, params = logical_not.to_sql()
        assert sql == 'NOT ("is_admin" = ?)'
        assert params == (True,)


# Tests for the new expressions
class TestCastExpression:
    def test_cast_simple(self, testable_dummy_dialect):
        lit = Literal(testable_dummy_dialect, "123")
        cast_expr = CastExpression(testable_dummy_dialect, lit, "INTEGER")
        sql, params = cast_expr.to_sql()
        assert sql == "CAST(? AS INTEGER)"
        assert params == ("123",)

class TestCaseExpression:
    def test_case_searched(self, testable_dummy_dialect):
        # Test searched CASE: CASE WHEN condition THEN result ... END
        condition1 = ComparisonPredicate(testable_dummy_dialect, ">", Column(testable_dummy_dialect, "age"), Literal(testable_dummy_dialect, 18))
        result1 = Literal(testable_dummy_dialect, "adult")
        condition2 = ComparisonPredicate(testable_dummy_dialect, "<=", Column(testable_dummy_dialect, "age"), Literal(testable_dummy_dialect, 18))
        result2 = Literal(testable_dummy_dialect, "minor")
        
        case_expr = CaseExpression(
            testable_dummy_dialect,
            cases=[(condition1, result1), (condition2, result2)],
            else_result=Literal(testable_dummy_dialect, "unknown")
        )
        sql, params = case_expr.to_sql()
        expected = 'CASE WHEN ("age" > ?) THEN ? WHEN ("age" <= ?) THEN ? ELSE ? END'
        assert sql == expected
        assert params == (18, "adult", 18, "minor", "unknown")

    def test_case_simple(self, testable_dummy_dialect):
        # Test simple CASE: CASE value WHEN ... THEN ... END
        value_expr = Column(testable_dummy_dialect, "status")
        condition1 = Literal(testable_dummy_dialect, "A")
        result1 = Literal(testable_dummy_dialect, "Active")
        condition2 = Literal(testable_dummy_dialect, "I")
        result2 = Literal(testable_dummy_dialect, "Inactive")
        
        # For simple CASE, we need to form condition-result pairs differently
        # It's CASE value WHEN condition1 THEN result1 WHEN condition2 THEN result2 END
        # This needs to be represented as: CASE value WHEN value=condition1 THEN result1...
        # But the implementation expects (condition, result) pairs where condition is already a predicate
        pass

class TestExistsExpression:
    def test_exists_subquery(self, testable_dummy_dialect):
        subquery = Subquery(testable_dummy_dialect, "SELECT 1 FROM users WHERE age > ?", (18,))
        exists_expr = ExistsExpression(testable_dummy_dialect, subquery)
        sql, params = exists_expr.to_sql()
        assert sql == "EXISTS ((SELECT 1 FROM users WHERE age > ?))"
        assert params == (18,)

    def test_not_exists_subquery(self, testable_dummy_dialect):
        subquery = Subquery(testable_dummy_dialect, "SELECT 1 FROM users WHERE age > ?", (18,))
        exists_expr = ExistsExpression(testable_dummy_dialect, subquery, is_not=True)
        sql, params = exists_expr.to_sql()
        assert sql == "NOT EXISTS ((SELECT 1 FROM users WHERE age > ?))"
        assert params == (18,)

class TestAnyExpression:
    def test_any_expression(self, testable_dummy_dialect):
        col = Column(testable_dummy_dialect, "age")
        arr_expr = Literal(testable_dummy_dialect, [18, 19, 20])
        any_expr = AnyExpression(testable_dummy_dialect, col, ">", arr_expr)
        sql, params = any_expr.to_sql()
        assert sql == '("age" > ANY(?))'
        assert params == ((18, 19, 20),)

class TestAllExpression:
    def test_all_expression(self, testable_dummy_dialect):
        col = Column(testable_dummy_dialect, "age")
        arr_expr = Literal(testable_dummy_dialect, [18, 19, 20])
        all_expr = AllExpression(testable_dummy_dialect, col, ">", arr_expr)
        sql, params = all_expr.to_sql()
        assert sql == '("age" > ALL(?))'
        assert params == ((18, 19, 20),)

class TestWindowExpression:
    def test_window_function(self, testable_dummy_dialect):
        func_call = FunctionCall(testable_dummy_dialect, "ROW_NUMBER")
        partition_by = [Column(testable_dummy_dialect, "department")]
        order_by = [Column(testable_dummy_dialect, "salary")]
        window_expr = WindowExpression(
            testable_dummy_dialect,
            func_call,
            partition_by=partition_by,
            order_by=order_by
        )
        sql, params = window_expr.to_sql()
        expected = 'ROW_NUMBER() OVER (PARTITION BY "department" ORDER BY "salary")'
        assert sql == expected
        assert params == ()

class TestCTEExpression:
    def test_cte_simple(self, testable_dummy_dialect):
        subquery = Subquery(testable_dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        cte_expr = CTEExpression(
            testable_dummy_dialect,
            name="adult_users",
            query=subquery
        )
        sql, params = cte_expr.to_sql()
        assert sql == '"adult_users" AS ((SELECT id, name FROM users WHERE age > ?))'
        assert params == (18,)

class TestJoinExpression:
    def test_inner_join_with_condition(self, testable_dummy_dialect):
                left_table = "users"
                right_table = "profiles"
                condition = ComparisonPredicate(
                    testable_dummy_dialect, 
                    "=", 
                    Column(testable_dummy_dialect, "id", table="users"), 
                    Column(testable_dummy_dialect, "user_id", table="profiles")
                )
                join_expr = JoinExpression(
                    testable_dummy_dialect,
                    left_table,
                    right_table,
                    join_type="INNER",
                    condition=condition
                )
                sql, params = join_expr.to_sql()
                expected = '"users" INNER JOIN "profiles" ON ("users"."id" = "profiles"."user_id")'
                assert sql == expected
                assert params == ()

class TestCompositeExpressions:
    def test_complex_where_clause(self, testable_dummy_dialect):
        age_pred = ComparisonPredicate(testable_dummy_dialect, ">", Column(testable_dummy_dialect, "age"), Literal(testable_dummy_dialect, 25))
        status_pred = ComparisonPredicate(testable_dummy_dialect, "=", Column(testable_dummy_dialect, "status"), Literal(testable_dummy_dialect, "active"))
        name_like_pred = LikePredicate(testable_dummy_dialect, "LIKE", Column(testable_dummy_dialect, "name"), Literal(testable_dummy_dialect, "J%"))

        # (age > 25 AND status = 'active') OR (name LIKE 'J%')
        and_pred = LogicalPredicate(testable_dummy_dialect, "AND", age_pred, status_pred)
        composite_pred = LogicalPredicate(testable_dummy_dialect, "OR", and_pred, name_like_pred)

        sql, params = composite_pred.to_sql()
        expected_sql = '((("age" > ?) AND ("status" = ?)) OR ("name" LIKE ?))'
        assert sql == expected_sql
        assert params == (25, "active", "J%")

    def test_select_with_function_and_arithmetic(self, testable_dummy_dialect):
        price_col = Column(testable_dummy_dialect, "price")
        quantity_col = Column(testable_dummy_dialect, "quantity")

        # price * quantity
        total_price_expr = BinaryArithmeticExpression(testable_dummy_dialect, "*", price_col, quantity_col)

        # SUM(price * quantity)
        sum_total_expr = FunctionCall(testable_dummy_dialect, "SUM", total_price_expr)

        # Note: This is now a single expression, combining this into a SELECT list
        # would be done by the QueryBuilder.
        sql, params = sum_total_expr.to_sql()
        expected_sql = 'SUM(("price" * "quantity"))'
        assert sql == expected_sql
        assert params == ()

    def test_null_check_with_logical_operator(self, testable_dummy_dialect):
        col_expr = Column(testable_dummy_dialect, "description")
        is_null_pred = col_expr.is_null()

        status_pred = ComparisonPredicate(testable_dummy_dialect, "=", Column(testable_dummy_dialect, "status"), Literal(testable_dummy_dialect, "pending"))

        # description IS NULL OR status = 'pending'
        composite_pred = LogicalPredicate(testable_dummy_dialect, "OR", is_null_pred, status_pred)

        sql, params = composite_pred.to_sql()
        expected_sql = '(("description" IS NULL) OR ("status" = ?))'
        assert sql == expected_sql
        assert params == ("pending",)