# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_query.py
import pytest

from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, FunctionCall,
    ComparisonPredicate, QueryExpression,  # Import new classes for window functions and advanced features
    SelectModifier,  # Window-related classes
    WindowFrameSpecification, WindowSpecification, WindowDefinition,
    WindowClause, WindowFunctionCall,
    # Additional classes needed
)
from rhosocial.activerecord.backend.expression.query_parts import (
    GroupByHavingClause, LimitOffsetClause, OrderByClause, QualifyClause, ForUpdateClause
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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")])
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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "date")]),
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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec1 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")])
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

        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec2 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "date")]),
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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")])
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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec_with_frame = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "category")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "date")]),
            frame=frame_spec
        )
        sql2, params2 = window_spec_with_frame.to_sql()
        expected2 = 'PARTITION BY "category" ORDER BY "date" ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING'
        assert sql2 == expected2
        assert params2 == ()

        # Test with ORDER BY using tuples (expression, direction)
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec3 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "region")],
            order_by=OrderByClause(dummy_dialect, [
                (Column(dummy_dialect, "category"), "ASC"),
                (Column(dummy_dialect, "price"), "DESC")
            ])
        )
        sql3, params3 = window_spec3.to_sql()
        expected3 = 'PARTITION BY "region" ORDER BY "category" ASC, "price" DESC'
        assert sql3 == expected3
        assert params3 == ()

    def test_window_definition_to_sql(self, dummy_dialect: DummyDialect):
        """Tests WindowDefinition.to_sql method."""
        # Create a window specification
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=OrderByClause(dummy_dialect, [(Column(dummy_dialect, "salary"), "DESC")])
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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
        window_spec2 = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "product_type")],
            order_by=OrderByClause(dummy_dialect, [Column(dummy_dialect, "sales_date")]),
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
        """Tests that QueryExpression with GroupByHavingClause raises ValueError when HAVING is used without GROUP BY."""
        having_condition = ComparisonPredicate(dummy_dialect, ">", FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")), Literal(dummy_dialect, 5))

        # The validation should happen in the GroupByHavingClause constructor itself, not in QueryExpression
        with pytest.raises(ValueError, match="HAVING clause requires GROUP BY clause"):
            group_by_having = GroupByHavingClause(
                dummy_dialect,
                group_by=None,  # No group_by specified
                having=having_condition  # HAVING without GROUP BY should raise error
            )

    def test_query_expression_offset_without_limit_with_support(self, dummy_dialect: DummyDialect, monkeypatch):
        """Tests QueryExpression with OFFSET without LIMIT where dialect supports it."""
        # Mock the dialect to return True for supports_offset_without_limit
        def mock_supports_offset_without_limit():
            return True
        monkeypatch.setattr(dummy_dialect, "supports_offset_without_limit", mock_supports_offset_without_limit)

        # Create a limit clause with just offset (some dialects support this)
        limit_offset_clause = LimitOffsetClause(dummy_dialect, offset=10)

        # This should not raise an error since dialect supports offset without limit
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
            limit_offset=limit_offset_clause  # Use limit/offset clause object with just offset
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

        # Creating the LimitOffsetClause with offset only should raise error when dialect doesn't support it
        # The validation happens in the LimitOffsetClause constructor
        with pytest.raises(ValueError, match="OFFSET clause requires LIMIT clause in this dialect"):
            limit_offset_clause = LimitOffsetClause(dummy_dialect, offset=10)

    def test_query_expression_order_by_simple_expressions(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with ORDER BY using simple expressions without directions."""
        # Create the ORDER BY clause object with simple expressions
        order_by_clause = OrderByClause(
            dummy_dialect,
            expressions=[
                Column(dummy_dialect, "name"),
                Column(dummy_dialect, "id")
            ]
        )

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            order_by=order_by_clause
        )
        sql, params = query.to_sql()
        assert 'ORDER BY "name", "id"' in sql
        assert params == ()

    def test_query_expression_with_qualify_clause(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with QUALIFY clause."""
        # Create the qualifying condition
        qualify_condition = ComparisonPredicate(
            dummy_dialect,
            ">",
            FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")),
            Literal(dummy_dialect, 5)
        )

        # Create GROUP BY/HAVING clause (even if just GROUP BY)
        group_by_having = GroupByHavingClause(
            dummy_dialect,
            group_by=[Column(dummy_dialect, "category")],
            having=None  # No HAVING clause here
        )

        # Create QUALIFY clause
        qualify_clause = QualifyClause(
            dummy_dialect,
            condition=qualify_condition
        )

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "category"), FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"))],
            from_=TableExpression(dummy_dialect, "products"),
            group_by_having=group_by_having,  # Use new GROUP BY/HAVING clause object
            qualify=qualify_clause   # Use new QUALIFY clause object
        )
        sql, params = query.to_sql()
        assert 'QUALIFY COUNT("id") > ?' in sql
        assert params == (5,)

    def test_comparison_mixin_methods(self, dummy_dialect: DummyDialect):
        """Test ComparisonMixin methods that are not directly tested elsewhere."""
        col = Column(dummy_dialect, "status")

        # Test is_null method
        is_null_pred = col.is_null()
        sql, params = is_null_pred.to_sql()
        assert "IS NULL" in sql.upper()
        assert params == ()

        # Test is_not_null method
        is_not_null_pred = col.is_not_null()
        sql, params = is_not_null_pred.to_sql()
        assert "IS NOT NULL" in sql.upper()
        assert params == ()

        # Test in_ method
        in_pred = col.in_(['active', 'pending'])
        sql, params = in_pred.to_sql()
        assert "IN (" in sql
        assert params == ('active', 'pending')

        # Test not_in method
        not_in_pred = col.not_in(['deleted', 'banned'])
        sql, params = not_in_pred.to_sql()
        assert "NOT" in sql.upper()
        assert "IN (" in sql.upper()
        assert params == ('deleted', 'banned')

        # Test between method
        age_col = Column(dummy_dialect, "age")
        between_pred = age_col.between(18, 65)
        sql, params = between_pred.to_sql()
        assert "BETWEEN" in sql.upper()
        assert params == (18, 65)

    def test_arithmetic_mixin_methods(self, dummy_dialect: DummyDialect):
        """Test ArithmeticMixin methods."""
        price_col = Column(dummy_dialect, "price")
        tax_rate = Literal(dummy_dialect, 0.1)

        # Test arithmetic operations
        total = price_col + (price_col * tax_rate)  # Addition and multiplication
        sql, params = total.to_sql()
        assert "+" in sql and "*" in sql
        assert params == (0.1,)

        discount = price_col - Literal(dummy_dialect, 5)  # Subtraction
        sql, params = discount.to_sql()
        assert "-" in sql
        assert params == (5,)

        division = price_col / Literal(dummy_dialect, 2)  # Division
        sql, params = division.to_sql()
        assert "/" in sql
        assert params == (2,)

        modulo = price_col % Literal(dummy_dialect, 10)  # Modulo
        sql, params = modulo.to_sql()
        assert "%" in sql
        assert params == (10,)

    def test_logical_mixin_methods(self, dummy_dialect: DummyDialect):
        """Test LogicalMixin methods."""
        # Test logical AND using & operator
        cond1 = Column(dummy_dialect, "age") > Literal(dummy_dialect, 18)
        cond2 = Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        logical_and = cond1 & cond2
        sql, params = logical_and.to_sql()
        assert "AND" in sql.upper()
        assert params == (18, "active")

        # Test logical OR using | operator
        cond3 = Column(dummy_dialect, "score") < Literal(dummy_dialect, 50)
        cond4 = Column(dummy_dialect, "category") == Literal(dummy_dialect, "low_priority")
        logical_or = cond3 | cond4
        sql, params = logical_or.to_sql()
        assert "OR" in sql.upper()
        assert params == (50, "low_priority")

        # Test logical NOT using ~ operator
        status_col = Column(dummy_dialect, "status")
        not_active = ~(status_col == Literal(dummy_dialect, "inactive"))
        sql, params = not_active.to_sql()
        assert "NOT" in sql.upper()
        assert params == ("inactive",)

    def test_string_mixin_methods(self, dummy_dialect: DummyDialect):
        """Test StringMixin methods."""
        name_col = Column(dummy_dialect, "name")

        # Test LIKE operation
        like_pred = name_col.like("John%")
        sql, params = like_pred.to_sql()
        assert "LIKE" in sql.upper()
        assert params == ("John%",)

        # Test ILIKE operation (case-insensitive LIKE)
        ilike_pred = name_col.ilike("%smith%")
        sql, params = ilike_pred.to_sql()
        assert "ILIKE" in sql.upper()
        assert params == ("%smith%",)

    def test_comparison_operators_direct_usage(self, dummy_dialect: DummyDialect):
        """Test direct usage of comparison operators that may not be covered elsewhere."""
        age_col = Column(dummy_dialect, "age")
        value = Literal(dummy_dialect, 25)

        # Test all comparison operators
        eq_pred = age_col == value  # __eq__
        sql, params = eq_pred.to_sql()
        assert "=" in sql
        assert params == (25,)

        neq_pred = age_col != value  # __ne__
        sql, params = neq_pred.to_sql()
        assert "!=" in sql or "<>" in sql
        assert params == (25,)

        gt_pred = age_col > value  # __gt__
        sql, params = gt_pred.to_sql()
        assert ">" in sql
        assert params == (25,)

        gte_pred = age_col >= value  # __ge__
        sql, params = gte_pred.to_sql()
        assert ">=" in sql
        assert params == (25,)

        lt_pred = age_col < value  # __lt__
        sql, params = lt_pred.to_sql()
        assert "<" in sql
        assert params == (25,)

        lte_pred = age_col <= value  # __le__
        sql, params = lte_pred.to_sql()
        assert "<=" in sql
        assert params == (25,)

    @pytest.mark.parametrize("op, pattern, expected_sql_part", [
        ("LIKE", "John%", '"name" LIKE ?'),
        ("ILIKE", "JOHN%", '"name" ILIKE ?'),  # Case-insensitive like
        ("LIKE", "%admin%", '"name" LIKE ?'),  # Contains pattern
        ("LIKE", "test___", '"name" LIKE ?'),  # Pattern with wildcards
    ])
    def test_query_with_like_condition(self, dummy_dialect: DummyDialect, op, pattern, expected_sql_part):
        """Tests query with LIKE/ILIKE conditions."""
        name_col = Column(dummy_dialect, "name")
        if op == "LIKE":
            like_condition = name_col.like(pattern)
        elif op == "ILIKE":
            like_condition = name_col.ilike(pattern)
        else:
            raise ValueError(f"Unsupported LIKE operation: {op}")

        query = QueryExpression(
            dummy_dialect,
            select=[name_col],
            from_="users",
            where=like_condition
        )
        sql, params = query.to_sql()

        # The actual SQL will be: SELECT "name" FROM "users" WHERE "name" LIKE ?
        expected_sql = f'SELECT "name" FROM "users" WHERE {expected_sql_part}'
        assert sql == expected_sql
        assert params == (pattern,)

    def test_query_with_combined_like_and_other_conditions(self, dummy_dialect: DummyDialect):
        """Tests query with LIKE condition combined with other conditions."""
        name_col = Column(dummy_dialect, "name")
        age_col = Column(dummy_dialect, "age")

        # Combine LIKE with comparison condition
        like_condition = name_col.like("John%")
        age_condition = age_col > Literal(dummy_dialect, 18)
        combined_condition = like_condition & age_condition

        query = QueryExpression(
            dummy_dialect,
            select=[name_col, age_col],
            from_="users",
            where=combined_condition
        )
        sql, params = query.to_sql()

        assert 'SELECT "name", "age" FROM "users" WHERE' in sql
        assert 'LIKE ?' in sql
        assert '> ?' in sql
        assert params == ("John%", 18)

    # --- Validation failure tests ---
    # Note: select and from_ parameters are automatically handled in the constructor,
    # so we focus on parameters that are not automatically converted

    def test_query_expression_invalid_select_type_after_construction(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid select parameter type after construction."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],  # Valid initial value
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.select = "invalid"  # Invalid type - should be list

        with pytest.raises(TypeError, match=r"select must be a list of expressions, got <class 'str'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_from_type_after_construction(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid from_ parameter type after construction."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")  # Valid initial value
        )
        # Manually assign invalid type to trigger validation error
        query.from_ = 123  # Invalid type

        with pytest.raises(TypeError, match=r"from_ must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_where_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid where parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.where = 456  # Invalid type - should be WhereClause or SQLPredicate

        with pytest.raises(TypeError, match=r"where must be WhereClause or SQLPredicate, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_group_by_having_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid group_by_having parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.group_by_having = 789  # Invalid type - should be GroupByHavingClause

        with pytest.raises(TypeError, match=r"group_by_having must be GroupByHavingClause, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_order_by_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid order_by parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.order_by = 999  # Invalid type - should be OrderByClause

        with pytest.raises(TypeError, match=r"order_by must be OrderByClause, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_qualify_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid qualify parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.qualify = 111  # Invalid type - should be QualifyClause

        with pytest.raises(TypeError, match=r"qualify must be QualifyClause, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_limit_offset_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid limit_offset parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.limit_offset = 222  # Invalid type - should be LimitOffsetClause

        with pytest.raises(TypeError, match=r"limit_offset must be LimitOffsetClause, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_for_update_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid for_update parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.for_update = 333  # Invalid type - should be ForUpdateClause

        with pytest.raises(TypeError, match=r"for_update must be ForUpdateClause, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_invalid_select_modifier_type(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression raises TypeError for invalid select_modifier parameter type."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type to trigger validation error
        query.select_modifier = "invalid"  # Invalid type - should be SelectModifier

        with pytest.raises(TypeError, match=r"select_modifier must be SelectModifier, got <class 'str'>"):
            query.validate(strict=True)

    def test_query_expression_validate_with_strict_false(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression.validate with strict=False skips validation."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )
        # Manually assign invalid type that would normally cause an error
        query.where = 999  # Invalid type - should be WhereClause or SQLPredicate

        # With strict=False, validation should pass without raising an error
        query.validate(strict=False)  # Should not raise any exception

        # Also test with valid parameters and strict=False
        query_valid = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name"), Column(dummy_dialect, "email")],
            from_=TableExpression(dummy_dialect, "customers"),
            where=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        query_valid.validate(strict=False)  # Should not raise any exception
        assert True  # Just to ensure the test passes

    def test_query_expression_from_invalid_type_with_strict_false(self, dummy_dialect: DummyDialect):
        """Tests that QueryExpression.from_ parameter validation respects strict=False setting."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")  # Valid initial value
        )
        # Manually assign invalid type that would normally cause an error
        query.from_ = 999  # Invalid type - should be str, TableExpression, etc.

        # With strict=False, validation should pass without raising an error
        query.validate(strict=False)  # Should not raise any exception

        # Verify that strict=True would raise an error for the same invalid parameter
        with pytest.raises(TypeError, match=r"from_ must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_with_count_distinct(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with COUNT(DISTINCT column_name) function."""
        from rhosocial.activerecord.backend.expression.functions import count

        # Create a COUNT(DISTINCT column) expression
        count_distinct_expr = count(dummy_dialect, Column(dummy_dialect, "category"), is_distinct=True)

        query = QueryExpression(
            dummy_dialect,
            select=[count_distinct_expr],
            from_=TableExpression(dummy_dialect, "products")
        )
        sql, params = query.to_sql()

        # The SQL should contain COUNT(DISTINCT "column_name")
        assert 'SELECT COUNT(DISTINCT "category") FROM "products"' == sql
        assert params == ()

    def test_query_expression_from_with_valid_list_types(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with valid types in from_ list."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

        # Test with list containing valid types: string, TableExpression, ValuesExpression
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "col1"), Column(dummy_dialect, "col2")],
            from_=[
                "users",  # String table name
                TableExpression(dummy_dialect, "orders", alias="o"),  # TableExpression with alias
                ValuesExpression(dummy_dialect, [("test",)], "values_alias", ["val"])  # ValuesExpression
            ]
        )

        sql, params = query.to_sql()

        # Verify that the query was generated successfully
        assert "SELECT" in sql
        assert "FROM" in sql
        assert '"users"' in sql
        assert '"orders"' in sql
        assert '"values_alias"' in sql
        assert params == ("test",)

    def test_query_expression_from_with_invalid_list_item_type(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression validation with invalid type in from_ list."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=[TableExpression(dummy_dialect, "users")]  # Valid initial value
        )

        # Manually assign a list with an invalid type to trigger validation error
        query.from_ = ["users", 123]  # 123 is invalid type in list context

        with pytest.raises(TypeError, match=r"from_ list item at index 1 must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression, got <class 'int'>"):
            query.validate(strict=True)

    def test_query_expression_from_with_invalid_list_item_type_complex(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression validation with complex invalid type in from_ list."""
        from rhosocial.activerecord.backend.expression import FunctionCall

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=[TableExpression(dummy_dialect, "users")]  # Valid initial value
        )

        # Manually assign a list with an invalid FunctionCall type to trigger validation error
        query.from_ = [TableExpression(dummy_dialect, "users"), FunctionCall(dummy_dialect, "NOW")]  # FunctionCall is invalid in FROM context

        with pytest.raises(TypeError, match=r"from_ list item at index 1 must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression, got <class '.*FunctionCall'>"):
            query.validate(strict=True)

    # --- Wildcard (SELECT *) tests ---
    def test_query_expression_with_wildcard(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with wildcard (SELECT *)."""
        from rhosocial.activerecord.backend.expression import WildcardExpression

        query = QueryExpression(
            dummy_dialect,
            select=[WildcardExpression(dummy_dialect)],
            from_=TableExpression(dummy_dialect, "users")
        )
        sql, params = query.to_sql()

        assert sql == 'SELECT * FROM "users"'
        assert params == ()

    def test_query_expression_with_qualified_wildcard(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with qualified wildcard (SELECT table.*)."""
        from rhosocial.activerecord.backend.expression import WildcardExpression

        query = QueryExpression(
            dummy_dialect,
            select=[WildcardExpression(dummy_dialect, table="users")],
            from_=TableExpression(dummy_dialect, "users")
        )
        sql, params = query.to_sql()

        assert sql == 'SELECT "users".* FROM "users"'
        assert params == ()

    def test_query_expression_with_multiple_wildcards_and_columns(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with multiple wildcards and columns."""
        from rhosocial.activerecord.backend.expression import WildcardExpression

        query = QueryExpression(
            dummy_dialect,
            select=[
                WildcardExpression(dummy_dialect, table="users"),
                Column(dummy_dialect, "name", "profiles")
            ],
            from_=[
                TableExpression(dummy_dialect, "users"),
                TableExpression(dummy_dialect, "profiles")
            ]
        )
        sql, params = query.to_sql()

        assert sql == 'SELECT "users".*, "profiles"."name" FROM "users", "profiles"'
        assert params == ()

    def test_query_expression_with_count_wildcard(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with COUNT(*) using WildcardExpression."""
        from rhosocial.activerecord.backend.expression import WildcardExpression, count

        # Test COUNT(*) using WildcardExpression
        count_expr = count(dummy_dialect, WildcardExpression(dummy_dialect))
        query = QueryExpression(
            dummy_dialect,
            select=[count_expr],
            from_=TableExpression(dummy_dialect, "users")
        )
        sql, params = query.to_sql()

        assert sql == 'SELECT COUNT(*) FROM "users"'
        assert params == ()

    def test_query_expression_with_count_qualified_wildcard(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with COUNT(table.*) using qualified WildcardExpression."""
        from rhosocial.activerecord.backend.expression import WildcardExpression, count

        # Test COUNT(table.*) using qualified WildcardExpression
        qualified_wildcard = WildcardExpression(dummy_dialect, table="users")
        count_expr = count(dummy_dialect, qualified_wildcard)
        query = QueryExpression(
            dummy_dialect,
            select=[count_expr],
            from_=TableExpression(dummy_dialect, "users")
        )
        sql, params = query.to_sql()

        # Note: COUNT(users.*) is not standard SQL, but this tests the integration
        # Standard SQL would use COUNT(*) or COUNT(column_name)
        assert sql == 'SELECT COUNT(*) FROM "users"'
        assert params == ()

    def test_query_expression_with_group_by_and_count_star(self, dummy_dialect: DummyDialect):
        """Tests QueryExpression with SELECT name, count(*) FROM users GROUP BY name."""
        from rhosocial.activerecord.backend.expression import count
        from rhosocial.activerecord.backend.expression import WildcardExpression

        # Create the COUNT(*) expression
        count_expr = count(dummy_dialect, WildcardExpression(dummy_dialect))

        # Create GROUP BY/HAVING clause with GROUP BY name
        group_by_having = GroupByHavingClause(
            dummy_dialect,
            group_by=[Column(dummy_dialect, "name")],  # GROUP BY name
            having=None  # No HAVING clause
        )

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name"), count_expr],  # SELECT name, count(*)
            from_=TableExpression(dummy_dialect, "users"),  # FROM users
            group_by_having=group_by_having  # GROUP BY name
        )
        sql, params = query.to_sql()

        assert sql == 'SELECT "name", COUNT(*) FROM "users" GROUP BY "name"'
        assert params == ()

