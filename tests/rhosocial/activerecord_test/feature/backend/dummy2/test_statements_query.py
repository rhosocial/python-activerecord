# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_query.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, TableExpression, FunctionCall,
    ComparisonPredicate, LogicalPredicate, InPredicate,
    QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
    BinaryArithmeticExpression,
    # Import new classes for window functions and advanced features
    CaseExpression, CastExpression, ExistsExpression, AnyExpression, AllExpression,
    SelectModifier, ForUpdateClause,
    # Window-related classes
    WindowFrameSpecification, WindowSpecification, WindowDefinition,
    WindowClause, WindowFunctionCall,
    # Additional classes needed
    Subquery,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestQueryStatements:
    """Tests for QueryExpression and related functionality."""

    # --- QueryExpression with DISTINCT/ALL modifiers ---
    @pytest.mark.parametrize("modifier, expected_prefix", [
        (SelectModifier.DISTINCT, "SELECT DISTINCT"),
        (SelectModifier.ALL, "SELECT ALL"),
        (None, "SELECT"),  # No modifier
    ])
    def test_query_expression_select_modifier(self, dummy_dialect: DummyDialect, modifier, expected_prefix):
        """Tests QueryExpression with DISTINCT/ALL modifiers."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name"), Column(dummy_dialect, "category")],
            from_=TableExpression(dummy_dialect, "products"),
            select_modifier=modifier
        )
        sql, params = query.to_sql()
        assert sql.startswith(expected_prefix)
        assert '"name", "category" FROM "products"' in sql
        assert params == ()

    # --- FOR UPDATE clause ---
    def test_query_expression_with_for_update_clause(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with FOR UPDATE clause."""
        for_update_clause = ForUpdateClause(
            dummy_dialect,
            of_columns=[Column(dummy_dialect, "id"), "name"],
            nowait=False,
            skip_locked=True
        )
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            for_update=for_update_clause
        )
        sql, params = query.to_sql()
        assert 'SELECT "id", "name" FROM "users" FOR UPDATE OF "id", "name" SKIP LOCKED' == sql
        assert params == ()

    def test_query_expression_with_for_update_nowait(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with FOR UPDATE NOWAIT."""
        for_update_clause = ForUpdateClause(
            dummy_dialect,
            of_columns=[Column(dummy_dialect, "id")],
            nowait=True,
            skip_locked=False
        )
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "locks"),
            for_update=for_update_clause
        )
        sql, params = query.to_sql()
        assert 'SELECT "id" FROM "locks" FOR UPDATE OF "id" NOWAIT' == sql
        assert params == ()

    # --- Window Functions ---
    def test_window_function_call_inline_spec(self, dummy_dialect: DummyDialect):
        """Tests WindowFunctionCall with inline window specification."""
        # Create a window specification
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=[(Column(dummy_dialect, "salary"), "DESC")]
        )

        # Create the window function call
        window_func = WindowFunctionCall(
            dummy_dialect,
            function_name="ROW_NUMBER",
            window_spec=window_spec,
            alias="row_num"
        )

        sql, params = window_func.to_sql()
        expected = 'ROW_NUMBER() OVER (PARTITION BY "department" ORDER BY "salary" DESC) AS "row_num"'
        assert sql == expected
        assert params == ()

    def test_window_function_call_with_frame_specification(self, dummy_dialect: DummyDialect):
        """Tests WindowFunctionCall with frame specification."""
        # Create a frame specification
        frame_spec = WindowFrameSpecification(
            dummy_dialect,
            frame_type="ROWS",
            start_frame="UNBOUNDED PRECEDING",
            end_frame="CURRENT ROW"
        )

        # Create a window specification with the frame
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=[Column(dummy_dialect, "date")],
            frame=frame_spec
        )

        # Create a window function call
        window_func = WindowFunctionCall(
            dummy_dialect,
            function_name="SUM",
            args=[Column(dummy_dialect, "amount")],
            window_spec=window_spec,
            alias="running_total"
        )

        sql, params = window_func.to_sql()
        expected = 'SUM("amount") OVER (PARTITION BY "category" ORDER BY "date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS "running_total"'
        assert sql == expected
        assert params == ()

    def test_window_function_call_with_named_window_reference(self, dummy_dialect: DummyDialect):
        """Tests WindowFunctionCall with reference to named window."""
        # Create a window function that references a named window (this would be used in a query
        # where the WINDOW clause defines the named window)
        window_func = WindowFunctionCall(
            dummy_dialect,
            function_name="RANK",
            window_spec="sales_window",  # Reference to named window
            alias="sales_rank"
        )

        sql, params = window_func.to_sql()
        expected = 'RANK() OVER "sales_window" AS "sales_rank"'
        assert sql == expected
        assert params == ()

    def test_query_with_window_clause(self, dummy_dialect: DummyDialect):
        """Tests a complete query with WINDOW clause."""
        # Create a window specification
        window_spec1 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=[(Column(dummy_dialect, "salary"), "DESC")]
        )

        # Create a window definition
        window_def1 = WindowDefinition(
            dummy_dialect,
            name="dept_ranking",
            specification=window_spec1
        )

        # Create a window specification with frame
        frame_spec = WindowFrameSpecification(
            dummy_dialect,
            frame_type="ROWS",
            start_frame="UNBOUNDED PRECEDING",
            end_frame="CURRENT ROW"
        )

        window_spec2 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=[Column(dummy_dialect, "date")],
            frame=frame_spec
        )

        window_def2 = WindowDefinition(
            dummy_dialect,
            name="running_total",
            specification=window_spec2
        )

        # Create a window clause
        window_clause = WindowClause(
            dummy_dialect,
            definitions=[window_def1, window_def2]
        )

        # Create a query that would reference these named windows
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "employee_name"),
                # In a real query, these would reference the named windows
                WindowFunctionCall(dummy_dialect, "ROW_NUMBER", window_spec="dept_ranking")
            ],
            from_=TableExpression(dummy_dialect, "employees"),
            # Note: The WindowClause would need to be integrated into QueryExpression to be fully functional
        )

        # Since we are testing the window clause itself, let's test it independently
        window_sql, window_params = window_clause.to_sql()
        assert 'WINDOW "dept_ranking" AS (PARTITION BY "department" ORDER BY "salary" DESC), "running_total" AS (PARTITION BY "category" ORDER BY "date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)' == window_sql
        assert window_params == ()

    # --- Window classes individual tests ---
    def test_window_frame_specification_to_sql(self, dummy_dialect: DummyDialect):
        """Tests WindowFrameSpecification.to_sql method."""
        frame_spec = WindowFrameSpecification(
            dummy_dialect,
            frame_type="ROWS",
            start_frame="UNBOUNDED PRECEDING",
            end_frame="CURRENT ROW"
        )
        sql, params = frame_spec.to_sql()
        expected = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        assert sql == expected
        assert params == ()

        # Test frame with single boundary (no BETWEEN)
        frame_spec2 = WindowFrameSpecification(
            dummy_dialect,
            frame_type="RANGE",
            start_frame="CURRENT ROW"
        )
        sql2, params2 = frame_spec2.to_sql()
        expected2 = "RANGE CURRENT ROW"
        assert sql2 == expected2
        assert params2 == ()

    def test_window_specification_to_sql(self, dummy_dialect: DummyDialect):
        """Tests WindowSpecification.to_sql method."""
        # Test with partition and order by
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=[(Column(dummy_dialect, "salary"), "DESC")]
        )
        sql, params = window_spec.to_sql()
        expected = 'PARTITION BY "department" ORDER BY "salary" DESC'
        assert sql == expected
        assert params == ()

        # Test with frame specification
        frame_spec = WindowFrameSpecification(
            dummy_dialect,
            frame_type="ROWS",
            start_frame="CURRENT ROW",
            end_frame="UNBOUNDED FOLLOWING"
        )
        window_spec_with_frame = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=[Column(dummy_dialect, "date")],
            frame=frame_spec
        )
        sql2, params2 = window_spec_with_frame.to_sql()
        expected2 = 'PARTITION BY "category" ORDER BY "date" ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING'
        assert sql2 == expected2
        assert params2 == ()

        # Test with ORDER BY using tuples (expression, direction)
        window_spec3 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "region")],
            order_by=[
                (Column(dummy_dialect, "category"), "ASC"),
                (Column(dummy_dialect, "price"), "DESC")
            ]
        )
        sql3, params3 = window_spec3.to_sql()
        expected3 = 'PARTITION BY "region" ORDER BY "category" ASC, "price" DESC'
        assert sql3 == expected3
        assert params3 == ()

    def test_window_definition_to_sql(self, dummy_dialect: DummyDialect):
        """Tests WindowDefinition.to_sql method."""
        # Create a window specification
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=[(Column(dummy_dialect, "salary"), "DESC")]
        )

        # Create a window definition
        window_def = WindowDefinition(
            dummy_dialect,
            name="dept_ranking",
            specification=window_spec
        )
        sql, params = window_def.to_sql()
        expected = '"dept_ranking" AS (PARTITION BY "department" ORDER BY "salary" DESC)'
        assert sql == expected
        assert params == ()

        # Test with frame specification
        frame_spec = WindowFrameSpecification(
            dummy_dialect,
            frame_type="ROWS",
            start_frame="UNBOUNDED PRECEDING",
            end_frame="CURRENT ROW"
        )
        window_spec2 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "product_type")],
            order_by=[Column(dummy_dialect, "sales_date")],
            frame=frame_spec
        )
        window_def2 = WindowDefinition(
            dummy_dialect,
            name="running_total",
            specification=window_spec2
        )
        sql2, params2 = window_def2.to_sql()
        expected2 = '"running_total" AS (PARTITION BY "product_type" ORDER BY "sales_date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)'
        assert sql2 == expected2
        assert params2 == ()

    # --- QueryExpression validation tests ---
    def test_query_expression_having_without_group_by_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises ValueError when HAVING is used without GROUP BY."""
        having_condition = ComparisonPredicate(dummy_dialect, ">", FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")), Literal(dummy_dialect, 5))
        
        with pytest.raises(ValueError, match="HAVING clause requires GROUP BY clause"):
            QueryExpression(
                dummy_dialect,
                select=[Column(dummy_dialect, "category")],
                from_=TableExpression(dummy_dialect, "products"),
                having=having_condition  # HAVING without GROUP BY should raise error
            )

    def test_query_expression_offset_without_limit_with_support(self, dummy_dialect: DummyDialect, monkeypatch):
        """Tests QueryExpression with OFFSET without LIMIT where dialect supports it."""
        # Mock the dialect to return True for supports_offset_without_limit
        def mock_supports_offset_without_limit():
            return True
        monkeypatch.setattr(dummy_dialect, "supports_offset_without_limit", mock_supports_offset_without_limit)
        
        # This should not raise an error since dialect supports offset without limit
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
            offset=10  # OFFSET without LIMIT
        )
        sql, params = query.to_sql()
        assert "OFFSET ?" in sql
        assert params == (10,)

    def test_query_expression_offset_without_limit_without_support(self, dummy_dialect: DummyDialect, monkeypatch):
        """Tests that QueryExpression raises ValueError when OFFSET is used without LIMIT and dialect doesn't support it."""
        # Mock the dialect to return False for supports_offset_without_limit
        def mock_supports_offset_without_limit():
            return False
        monkeypatch.setattr(dummy_dialect, "supports_offset_without_limit", mock_supports_offset_without_limit)
        
        with pytest.raises(ValueError, match="OFFSET clause requires LIMIT clause in this dialect"):
            QueryExpression(
                dummy_dialect,
                select=[Column(dummy_dialect, "id")],
                from_=TableExpression(dummy_dialect, "users"),
                offset=10  # OFFSET without LIMIT, dialect doesn't support it
            )

    def test_query_expression_order_by_simple_expressions(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with ORDER BY using simple expressions without directions."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            order_by=[  # Simple expressions, no tuples
                Column(dummy_dialect, "name"),
                Column(dummy_dialect, "id")
            ]
        )
        sql, params = query.to_sql()
        assert 'ORDER BY "name", "id"' in sql
        assert params == ()

    def test_query_expression_with_qualify_clause(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with QUALIFY clause."""
        qualify_condition = ComparisonPredicate(dummy_dialect, ">",
                                              FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")),
                                              Literal(dummy_dialect, 5))
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "category"), FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"))],
            from_=TableExpression(dummy_dialect, "products"),
            group_by=[Column(dummy_dialect, "category")],
            qualify=qualify_condition  # QUALIFY clause
        )
        sql, params = query.to_sql()
        assert 'QUALIFY COUNT("id") > ?' in sql
        assert params == (5,)
