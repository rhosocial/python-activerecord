# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_advanced.py
import pytest

from rhosocial.activerecord.backend.expression import (
    Column, Literal, Subquery, ComparisonPredicate, CaseExpression, CastExpression, ExistsExpression, AnyExpression,
    AllExpression,
    WindowFunctionCall, WindowSpecification, WindowFrameSpecification, JSONExpression, ArrayExpression,
    BinaryArithmeticExpression,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestAdvancedExpressions:
    """Tests for advanced SQL expression types."""

    # --- CaseExpression ---
    def test_case_searched_expression(self, dummy_dialect: DummyDialect):
        """Tests a searched CASE expression (CASE WHEN ... THEN ... ELSE ... END)."""
        condition1 = ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 18))
        result1 = Literal(dummy_dialect, "adult")
        condition2 = ComparisonPredicate(dummy_dialect, "<=", Column(dummy_dialect, "age"), Literal(dummy_dialect, 18))
        result2 = Literal(dummy_dialect, "minor")
        
        case_expr = CaseExpression(
            dummy_dialect,
            cases=[(condition1, result1), (condition2, result2)],
            else_result=Literal(dummy_dialect, "unknown")
        )
        sql, params = case_expr.to_sql()
        expected = 'CASE WHEN "age" > ? THEN ? WHEN "age" <= ? THEN ? ELSE ? END'
        assert sql == expected
        assert params == (18, "adult", 18, "minor", "unknown")

    def test_case_simple_expression(self, dummy_dialect: DummyDialect):
        """Tests a simple CASE expression (CASE value WHEN ... THEN ... ELSE ... END)."""
        value_expr = Column(dummy_dialect, "status_code")
        case_expr = CaseExpression(
            dummy_dialect,
            value=value_expr,
            cases=[
                (Literal(dummy_dialect, 1), Literal(dummy_dialect, "Pending")),
                (Literal(dummy_dialect, 2), Literal(dummy_dialect, "Approved"))
            ],
            else_result=Literal(dummy_dialect, "Rejected")
        )
        sql, params = case_expr.to_sql()
        expected = 'CASE "status_code" WHEN ? THEN ? WHEN ? THEN ? ELSE ? END'
        assert sql == expected
        assert params == (1, "Pending", 2, "Approved", "Rejected")

    # --- CastExpression ---
    @pytest.mark.parametrize("expr_data, target_type, expected_sql, expected_params", [
        (("Column", ("price",)), "INTEGER", 'CAST("price" AS INTEGER)', ()),
        (("Literal", ("2023-01-01",)), "DATE", 'CAST(? AS DATE)', ("2023-01-01",)),
        (("BinaryArithmeticExpression", ("*", ("Column", "value"), ("Literal", 100))), "DECIMAL(10,2)", 'CAST("value" * ? AS DECIMAL(10,2))', (100,)),
    ])
    def test_cast_expression(self, dummy_dialect: DummyDialect, expr_data, target_type, expected_sql, expected_params):
        """Tests CAST expression to convert types."""
        expr_class_name, expr_args = expr_data
        
        if expr_class_name == "BinaryArithmeticExpression":
            op, left_data, right_data = expr_args
            
            def get_arg_instance(data_tuple):
                arg_class = globals()[data_tuple[0]]
                arg_value = data_tuple[1]
                if isinstance(arg_value, tuple):
                    return arg_class(dummy_dialect, *arg_value)
                return arg_class(dummy_dialect, arg_value)

            left = get_arg_instance(left_data)
            right = get_arg_instance(right_data)
            
            expr_to_cast = BinaryArithmeticExpression(dummy_dialect, op, left, right)
        else:
            expr_class = globals()[expr_class_name]
            expr_to_cast = expr_class(dummy_dialect, *expr_args)

        cast_expr = CastExpression(dummy_dialect, expr_to_cast, target_type)
        sql, params = cast_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    # --- ExistsExpression ---
    @pytest.mark.parametrize("is_not, expected_prefix", [
        (False, "EXISTS"),
        (True, "NOT EXISTS"),
    ])
    def test_exists_expression(self, dummy_dialect: DummyDialect, is_not, expected_prefix):
        """Tests EXISTS and NOT EXISTS expressions with a subquery."""
        subquery = Subquery(dummy_dialect, "SELECT 1 FROM users WHERE active = ?", (True,))
        exists_expr = ExistsExpression(dummy_dialect, subquery, is_not=is_not)
        sql, params = exists_expr.to_sql()
        assert sql == f'{expected_prefix} (SELECT 1 FROM users WHERE active = ?)'
        assert params == (True,)

    # --- AnyExpression / AllExpression ---
    @pytest.mark.parametrize("expr_type, operator, operand_list, expected_keyword, expected_sql_pattern, expected_params", [
        (AnyExpression, ">", [10, 20, 30], "ANY", '("age" > ANY?)', ((10, 20, 30),)),
        (AllExpression, "<", [5, 10], "ALL", '("age" < ALL?)', ((5, 10),)),
    ])
    def test_any_all_expressions(self, dummy_dialect: DummyDialect, expr_type, operator, operand_list, expected_keyword, expected_sql_pattern, expected_params):
        """Tests ANY and ALL expressions with a list of values."""
        col = Column(dummy_dialect, "age")
        arr_expr = Literal(dummy_dialect, operand_list)
        any_all_expr = expr_type(dummy_dialect, col, operator, arr_expr)
        sql, params = any_all_expr.to_sql()
        assert sql == expected_sql_pattern
        assert params == expected_params

    def test_any_with_subquery(self, dummy_dialect: DummyDialect):
        """Tests ANY expression with a subquery."""
        subquery = Subquery(dummy_dialect, "SELECT product_id FROM top_sellers WHERE category = ?", ("electronics",))
        any_expr = AnyExpression(dummy_dialect, Column(dummy_dialect, "item_id"), "=", subquery)
        sql, params = any_expr.to_sql()
        assert sql == '("item_id" = ANY(SELECT product_id FROM top_sellers WHERE category = ?))'
        assert params == ("electronics",)

    # --- WindowFunctionCall ---
    def test_window_function_basic(self, dummy_dialect: DummyDialect):
        """Tests a basic window function with PARTITION BY and ORDER BY."""
        # Create window specification
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")])
        )
        # Create window function call
        window_expr = WindowFunctionCall(
            dummy_dialect,
            function_name="RANK",
            window_spec=window_spec
        )
        sql, params = window_expr.to_sql()
        expected = 'RANK() OVER (PARTITION BY "department" ORDER BY "salary" DESC)'
        assert sql == expected
        assert params == ()

    def test_window_function_with_frame(self, dummy_dialect: DummyDialect):
        """Tests a window function with frame specification (ROWS BETWEEN ... AND ...)."""
        # Create frame specification
        frame_spec = WindowFrameSpecification(
            dummy_dialect,
            frame_type="ROWS",
            start_frame="UNBOUNDED PRECEDING",
            end_frame="CURRENT ROW"
        )
        # Create window specification with frame
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "user_id")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "transaction_date")]),
            frame=frame_spec
        )
        # Create window function call
        window_expr = WindowFunctionCall(
            dummy_dialect,
            function_name="SUM",
            args=[Column(dummy_dialect, "amount")],
            window_spec=window_spec,
            alias="running_total"
        )
        sql, params = window_expr.to_sql()
        expected = 'SUM("amount") OVER (PARTITION BY "user_id" ORDER BY "transaction_date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS "running_total"'
        assert sql == expected
        assert params == ()

    # --- JSONExpression ---
    @pytest.mark.parametrize("col_name, path, operation, expected_sql, expected_params", [
        ("data", "$.name", "->", '("data" -> ?)', ('$.name',)),
        ("metadata", "$.user.id", "->>", '("metadata" ->> ?)', ('$.user.id',)),
    ])
    def test_json_expression(self, dummy_dialect: DummyDialect, col_name, path, operation, expected_sql, expected_params):
        """Tests JSON path extraction operations."""
        json_col = Column(dummy_dialect, col_name)
        json_expr = JSONExpression(dummy_dialect, json_col, path, operation=operation)
        sql, params = json_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    # --- ArrayExpression ---
    def test_array_constructor(self, dummy_dialect: DummyDialect):
        """Tests array constructor (ARRAY[...])."""
        array_expr = ArrayExpression(dummy_dialect, "CONSTRUCTOR", elements=[
            Literal(dummy_dialect, 1),
            Literal(dummy_dialect, "apple"),
            Column(dummy_dialect, "item_count")
        ])
        sql, params = array_expr.to_sql()
        assert sql == 'ARRAY[?, ?, "item_count"]'
        assert params == (1, "apple")

    def test_array_access(self, dummy_dialect: DummyDialect):
        """Tests array element access (array[index])."""
        array_access_expr = ArrayExpression(dummy_dialect, "ACCESS",
                                            base_expr=Column(dummy_dialect, "tags"),
                                            index_expr=Literal(dummy_dialect, 0))
        sql, params = array_access_expr.to_sql()
        assert sql == '("tags"[?])'
        assert params == (0,)
