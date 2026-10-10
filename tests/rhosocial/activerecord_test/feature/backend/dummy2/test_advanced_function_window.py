# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_advanced_function_window.py
import pytest

from rhosocial.activerecord.backend.expression.types import CustomType
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    FunctionCall,
    QueryExpression,
    CaseExpression,
    ComparisonPredicate,
    ExistsExpression,
    AnyExpression,
    AllExpression,
    SelectModifier,
    ForUpdateClause,
    WindowFrameSpecification,
    WindowSpecification,
    WindowDefinition,
    WindowClause,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause, WhereClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import DecimalType


class TestAdvancedFunctionWindow:
    """Tests for advanced SQL functions and window functions."""

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
            else_result=Literal(dummy_dialect, "unknown"),
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
                (Literal(dummy_dialect, 2), Literal(dummy_dialect, "Approved")),
            ],
            else_result=Literal(dummy_dialect, "Rejected"),
        )
        sql, params = case_expr.to_sql()
        expected = 'CASE "status_code" WHEN ? THEN ? WHEN ? THEN ? ELSE ? END'
        assert sql == expected
        assert params == (1, "Pending", 2, "Approved", "Rejected")

    # --- Cast via cast() method ---
    @pytest.mark.parametrize(
        "expr_data, target_type, expected_sql, expected_params",
        [
            pytest.param(
                ("Column", ("price",)), "INTEGER", 'CAST("price" AS INTEGER)', (), id="cast_column_to_integer"
            ),
            pytest.param(
                ("Literal", ("2023-01-01",)), "DATE", "CAST(? AS DATE)", ("2023-01-01",), id="cast_literal_to_date"
            ),
        ],
    )
    def test_cast_method(self, dummy_dialect: DummyDialect, expr_data, target_type, expected_sql, expected_params):
        """Tests cast() method to convert types."""
        expr_class_name, expr_args = expr_data

        if expr_class_name == "Column":
            expr = Column(dummy_dialect, expr_args[0])
        elif expr_class_name == "Literal":
            expr = Literal(dummy_dialect, expr_args[0])
        else:
            return

        cast_expr = expr.cast(CustomType(dummy_dialect, raw=target_type))
        sql, params = cast_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_cast_method_on_arithmetic_result(self, dummy_dialect: DummyDialect):
        """Tests cast() method on arithmetic expression result (applied to operand)."""
        col = Column(dummy_dialect, "value")
        casted = col.cast(DecimalType(dummy_dialect, precision=10, scale=2))
        sql, params = casted.to_sql()
        assert sql == 'CAST("value" AS DECIMAL(10,2))'
        assert params == ()

    # --- EXISTS and related expressions ---
    def test_exists_expression(self, dummy_dialect: DummyDialect):
        """Tests EXISTS predicate."""
        subquery = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=NamedRelationRef(dummy_dialect, Table(dummy_dialect, "orders")),
            where=WhereClause(
                dummy_dialect,
        condition=ComparisonPredicate(
                    dummy_dialect, "=", Column(dummy_dialect, "user_id"), Column(dummy_dialect, "id", "u"),
                ),
            ),
        )
        exists_expr = ExistsExpression(dummy_dialect, subquery)
        sql, params = exists_expr.to_sql()
        expected = 'EXISTS (SELECT "id" FROM "orders" WHERE "user_id" = "u"."id")'
        assert sql == expected
        assert params == ()

    def test_exists_expression_invalid_subquery_type_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that ExistsExpression raises TypeError for invalid subquery parameter type."""

        # Create an object that is neither Subquery nor BaseExpression (doesn't have to_sql method)
        class InvalidObject:
            pass

        invalid_obj = InvalidObject()

        # This should raise TypeError because the object is neither Subquery nor BaseExpression
        with pytest.raises(
            TypeError, match=r"subquery must be Subquery or BaseExpression, got <class '.*InvalidObject'>"
        ):
            ExistsExpression(dummy_dialect, invalid_obj)

    def test_any_all_expressions(self, dummy_dialect: DummyDialect):
        """Tests ANY and ALL expressions."""
        # ANY expression
        any_expr = AnyExpression(
            dummy_dialect, Column(dummy_dialect, "value"), ">", Literal(dummy_dialect, [10, 20, 30])
        )
        sql, params = any_expr.to_sql()
        expected = '("value" > ANY?)'
        assert sql == expected
        assert params == ((10, 20, 30),)

        # ALL expression
        all_expr = AllExpression(
            dummy_dialect, Column(dummy_dialect, "score"), ">=", Literal(dummy_dialect, [85, 90, 95])
        )
        sql, params = all_expr.to_sql()
        expected = '("score" >= ALL?)'
        assert sql == expected
        assert params == ((85, 90, 95),)

    # --- QueryExpression with DISTINCT/ALL modifiers ---
    @pytest.mark.parametrize(
        "modifier, expected_prefix",
        [
            (SelectModifier.DISTINCT, "SELECT DISTINCT"),
            (SelectModifier.ALL, "SELECT ALL"),
            (None, "SELECT"),  # No modifier
        ],
    )
    def test_query_expression_select_modifier(self, dummy_dialect: DummyDialect, modifier, expected_prefix):
        """Tests QueryExpression with DISTINCT/ALL modifiers."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name"), Column(dummy_dialect, "category")],
            from_=NamedRelationRef(dummy_dialect, Table(dummy_dialect, "products")),
            select_modifier=modifier,
        )
        sql, params = query.to_sql()
        assert sql.startswith(expected_prefix)
        assert '"name", "category" FROM "products"' in sql
        assert params == ()

    # --- FOR UPDATE clause ---
    def test_query_expression_with_for_update_clause(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with FOR UPDATE clause."""
        for_update_clause = ForUpdateClause(
            dummy_dialect, of_columns=[Column(dummy_dialect, "id"), "name"], nowait=False, skip_locked=True
        )
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=NamedRelationRef(dummy_dialect, Table(dummy_dialect, "users")),
            for_update=for_update_clause,
        )
        sql, params = query.to_sql()
        assert 'SELECT "id", "name" FROM "users" FOR UPDATE OF "id", "name" SKIP LOCKED' == sql
        assert params == ()

    def test_query_expression_with_for_update_nowait(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with FOR UPDATE NOWAIT."""
        for_update_clause = ForUpdateClause(
            dummy_dialect, of_columns=[Column(dummy_dialect, "id")], nowait=True, skip_locked=False
        )
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=NamedRelationRef(dummy_dialect, Table(dummy_dialect, "locks")),
            for_update=for_update_clause,
        )
        sql, params = query.to_sql()
        assert 'SELECT "id" FROM "locks" FOR UPDATE OF "id" NOWAIT' == sql
        assert params == ()

    # --- Window Functions ---
    def test_window_function_call_inline_spec(self, dummy_dialect: DummyDialect):
        """Tests FunctionCall with inline window specification."""
        # Create a window specification
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")]),
        )

        # Create the window function call
        window_func = FunctionCall(
            dummy_dialect, "ROW_NUMBER", window_spec=window_spec, alias="row_num"
        )

        sql, params = window_func.to_sql()
        expected = 'ROW_NUMBER() OVER (PARTITION BY "department" ORDER BY "salary" DESC) AS "row_num"'
        assert sql == expected
        assert params == ()

    def test_window_function_call_with_frame_specification(self, dummy_dialect: DummyDialect):
        """Tests FunctionCall with frame specification."""
        # Create a frame specification
        frame_spec = WindowFrameSpecification(
            dummy_dialect, frame_type="ROWS", start_frame="UNBOUNDED PRECEDING", end_frame="CURRENT ROW"
        )

        # Create a window specification with the frame
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "date")]),
            frame=frame_spec,
        )

        # Create a window function call
        window_func = FunctionCall(
            dummy_dialect,
            "SUM",
            Column(dummy_dialect, "amount"),
            window_spec=window_spec,
            alias="running_total",
        )

        sql, params = window_func.to_sql()
        expected = 'SUM("amount") OVER (PARTITION BY "category" ORDER BY "date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS "running_total"'  # noqa: E501
        assert sql == expected
        assert params == ()

    def test_window_function_call_with_named_window_reference(self, dummy_dialect: DummyDialect):
        """Tests FunctionCall with reference to named window."""
        # Create a window function that references a named window (this would be used in a query
        # where the WINDOW clause defines the named window)
        window_func = FunctionCall(
            dummy_dialect,
            "RANK",
            window_spec="sales_window",  # Reference to named window
            alias="sales_rank",
        )

        sql, params = window_func.to_sql()
        expected = 'RANK() OVER "sales_window" AS "sales_rank"'
        assert sql == expected
        assert params == ()

    def test_query_with_window_clause(self, dummy_dialect: DummyDialect):
        """Tests a complete query with WINDOW clause."""
        # Create a window specification
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        window_spec1 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")]),
        )

        # Create a window definition
        window_def1 = WindowDefinition(dummy_dialect, name="dept_ranking", specification=window_spec1)

        # Create a window specification with frame
        frame_spec = WindowFrameSpecification(
            dummy_dialect, frame_type="ROWS", start_frame="UNBOUNDED PRECEDING", end_frame="CURRENT ROW"
        )

        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        window_spec2 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "date")]),
            frame=frame_spec,
        )

        window_def2 = WindowDefinition(dummy_dialect, name="running_total", specification=window_spec2)

        # Create a window clause
        window_clause = WindowClause(dummy_dialect, definitions=[window_def1, window_def2])

        # Create a query that would reference these named windows
        QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "employee_name"),
                # In a real query, these would reference the named windows
                FunctionCall(dummy_dialect, "ROW_NUMBER", window_spec="dept_ranking"),
            ],
            from_=NamedRelationRef(dummy_dialect, Table(dummy_dialect, "employees")),
            # Note: The WindowClause would need to be integrated into QueryExpression to be fully functional
        )

        # Since we are testing the window clause itself, let's test it independently
        window_sql, window_params = window_clause.to_sql()
        assert (
            'WINDOW "dept_ranking" AS (PARTITION BY "department" ORDER BY "salary" DESC), "running_total" AS (PARTITION BY "category" ORDER BY "date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)'  # noqa: E501
            == window_sql
        )
        assert window_params == ()

    def test_window_function_call_refuses_a_value_that_is_not_an_expression(
        self, dummy_dialect: DummyDialect
    ):
        """The renderer does not decide what an argument meant.

        A bare value used to be turned into a bind parameter at render time,
        which is the formatter manufacturing the expression it was asked to
        render. Whether ``"test"`` is a value or a column name is the factory's
        question, so the formatter refuses and the caller writes ``Literal``.
        """
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")]),
        )
        window_func = FunctionCall(
            dummy_dialect,
            "RANK",
            1,
            "test",
            3.14,  # Literal values, not BaseExpression instances
            window_spec=window_spec,
            alias="rank_val",
        )

        with pytest.raises(AttributeError):
            window_func.to_sql()

    def test_window_function_call_takes_literal_expressions(self, dummy_dialect: DummyDialect):
        """Literal arguments render as bind parameters and keep the window clause."""
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")]),
        )
        window_func = FunctionCall(
            dummy_dialect,
            "RANK",
            Literal(dummy_dialect, 1),
            Literal(dummy_dialect, "test"),
            Literal(dummy_dialect, 3.14),
            window_spec=window_spec,
            alias="rank_val",
        )

        sql, params = window_func.to_sql()
        assert "RANK(?, ?, ?)" in sql
        assert "OVER" in sql
        assert "PARTITION BY" in sql
        assert "ORDER BY" in sql
        assert params == (1, "test", 3.14)

    def test_window_clause_with_empty_definitions_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that WindowClause with empty definitions raises ValueError."""
        from rhosocial.activerecord.backend.expression import WindowClause

        # Create a WindowClause with empty definitions list
        window_clause = WindowClause(
            dummy_dialect,
            definitions=[],  # Empty list should raise an error
        )

        # Should raise ValueError when to_sql() is called
        with pytest.raises(ValueError, match=r"WindowClause must contain at least one window definition."):
            window_clause.to_sql()

    def test_case_expression_with_empty_cases_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CaseExpression with empty cases list raises ValueError."""
        from rhosocial.activerecord.backend.expression import CaseExpression

        # Create a CaseExpression with empty cases list
        case_expr = CaseExpression(
            dummy_dialect,
            cases=[],  # Empty list should raise an error
        )

        # Should raise ValueError when to_sql() is called
        with pytest.raises(
            ValueError, match=r"CASE expression must have at least one WHEN/THEN condition-result pair."
        ):
            case_expr.to_sql()

    def test_window_specification_with_invalid_order_by_type_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that WindowSpecification raises TypeError when order_by is not OrderByClause or str."""
        from rhosocial.activerecord.backend.expression import Column
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification

        # Test with invalid types that should raise TypeError
        invalid_types = [123, [Column(dummy_dialect, "value")], 3.14, {"key": "value"}]

        for invalid_type in invalid_types:
            with pytest.raises(TypeError, match=r"order_by must be OrderByClause or str, got <class '.*'>"):
                WindowSpecification(
                    dummy_dialect, partition_by=[Column(dummy_dialect, "department")], order_by=invalid_type
                )

    def test_window_specification_with_string_converts_to_order_by_clause(self, dummy_dialect: DummyDialect):
        """Tests that WindowSpecification converts string to OrderByClause."""
        from rhosocial.activerecord.backend.expression import Column
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification

        # Create a WindowSpecification with string order_by (should be converted to OrderByClause)
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by="salary",  # String should be converted to OrderByClause
        )

        # Verify that order_by is now an OrderByClause object
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        assert isinstance(window_spec.order_by, OrderByClause)
        # Verify that the OrderByClause contains the expected column
        assert len(window_spec.order_by.expressions) == 1
        # The expression should be a Column with the name "salary"

    def test_ordered_set_aggregation_with_invalid_order_by_type_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that OrderedSetAggregation raises TypeError when order_by is not OrderByClause or str."""
        from rhosocial.activerecord.backend.expression import Column, Literal
        from rhosocial.activerecord.backend.expression.advanced_functions import OrderedSetAggregation

        # Test with invalid types that should raise TypeError
        invalid_types = [123, [Column(dummy_dialect, "value")], 3.14, {"key": "value"}]

        for invalid_type in invalid_types:
            with pytest.raises(TypeError, match=r"order_by must be OrderByClause or str, got <class '.*'>"):
                OrderedSetAggregation(
                    dummy_dialect, "PERCENTILE_CONT", args=[Literal(dummy_dialect, 0.5)], order_by=invalid_type
                )

    def test_ordered_set_aggregation_with_string_converts_to_order_by_clause(self, dummy_dialect: DummyDialect):
        """Tests that OrderedSetAggregation converts string to OrderByClause."""
        from rhosocial.activerecord.backend.expression import Literal
        from rhosocial.activerecord.backend.expression.advanced_functions import OrderedSetAggregation

        # Create an OrderedSetAggregation with string order_by (should be converted to OrderByClause)
        ordered_agg = OrderedSetAggregation(
            dummy_dialect,
            "PERCENTILE_CONT",
            args=[Literal(dummy_dialect, 0.5)],
            order_by="value",  # String should be converted to OrderByClause
        )

        # Verify that order_by is now an OrderByClause object
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        assert isinstance(ordered_agg.order_by, OrderByClause)
        # Verify that the OrderByClause contains the expected column
        assert len(ordered_agg.order_by.expressions) == 1
        # The expression should be a Column with the name "value"
