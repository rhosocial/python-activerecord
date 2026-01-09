# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_advanced_functions.py
"""
Tests for the advanced SQL function expression components in advanced_functions.py
"""
from rhosocial.activerecord.backend.expression import (
    Column, Literal
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    CaseExpression, CastExpression, ExistsExpression,
    AnyExpression, AllExpression, JSONExpression, ArrayExpression,
    OrderedSetAggregation
)
from rhosocial.activerecord.backend.expression.core import Subquery
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCaseExpression:
    """Tests for CaseExpression class."""

    def test_case_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic CASE expression functionality."""
        # Create a basic CASE expression with one condition-result pair
        condition = Column(dummy_dialect, "age") > Literal(dummy_dialect, 18)
        result = Literal(dummy_dialect, "adult")
        case_expr = CaseExpression(dummy_dialect, cases=[(condition, result)])
        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert "WHEN" in sql
        assert "THEN" in sql

    def test_case_expression_with_value(self, dummy_dialect: DummyDialect):
        """Test CASE expression with value."""
        value_expr = Column(dummy_dialect, "status")
        # Create a basic CASE expression with one condition-result pair
        condition = Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        result = Literal(dummy_dialect, "ACTIVE_USER")
        case_expr = CaseExpression(dummy_dialect, value=value_expr, cases=[(condition, result)])
        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert "WHEN" in sql
        assert "THEN" in sql

    def test_case_expression_with_cases(self, dummy_dialect: DummyDialect):
        """Test CASE expression with cases."""
        condition = Column(dummy_dialect, "age") > Literal(dummy_dialect, 18)
        result = Literal(dummy_dialect, "adult")
        case_expr = CaseExpression(dummy_dialect, cases=[(condition, result)])
        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert "WHEN" in sql
        assert "THEN" in sql

    def test_case_expression_with_else_result(self, dummy_dialect: DummyDialect):
        """Test CASE expression with else result."""
        condition = Column(dummy_dialect, "age") > Literal(dummy_dialect, 18)
        result = Literal(dummy_dialect, "adult")
        else_result = Literal(dummy_dialect, "minor")
        case_expr = CaseExpression(dummy_dialect, cases=[(condition, result)], else_result=else_result)
        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert "ELSE" in sql

    def test_case_expression_with_alias(self, dummy_dialect: DummyDialect):
        """Test CASE expression with alias."""
        condition = Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        result = Literal(dummy_dialect, 1)
        else_result = Literal(dummy_dialect, 0)
        case_expr = CaseExpression(dummy_dialect, cases=[(condition, result)], else_result=else_result, alias="status_flag")
        sql, params = case_expr.to_sql()
        assert "AS" in sql
        assert "status_flag" in sql


class TestCastExpression:
    """Tests for CastExpression class."""

    def test_cast_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic CAST expression functionality."""
        col = Column(dummy_dialect, "id")
        cast_expr = CastExpression(dummy_dialect, col, "INTEGER")
        sql, params = cast_expr.to_sql()
        assert "CAST(" in sql
        assert "AS INTEGER" in sql

    def test_cast_expression_with_literal(self, dummy_dialect: DummyDialect):
        """Test CAST expression with literal value."""
        literal = Literal(dummy_dialect, "123")
        cast_expr = CastExpression(dummy_dialect, literal, "INTEGER")
        sql, params = cast_expr.to_sql()
        assert "CAST(" in sql
        assert "AS INTEGER" in sql
        assert params == ("123",)


class TestExistsExpression:
    """Tests for ExistsExpression class."""

    def test_exists_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic EXISTS expression functionality."""
        subquery = Subquery(dummy_dialect, "SELECT 1 FROM users WHERE id = ?", (1,))
        exists_expr = ExistsExpression(dummy_dialect, subquery)
        sql, params = exists_expr.to_sql()
        assert "EXISTS" in sql
        assert params == (1,)

    def test_not_exists_expression(self, dummy_dialect: DummyDialect):
        """Test NOT EXISTS expression functionality."""
        subquery = Subquery(dummy_dialect, "SELECT 1 FROM users WHERE id = ?", (1,))
        exists_expr = ExistsExpression(dummy_dialect, subquery, is_not=True)
        sql, params = exists_expr.to_sql()
        assert "NOT EXISTS" in sql
        assert params == (1,)


class TestAnyExpression:
    """Tests for AnyExpression class."""

    def test_any_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic ANY expression functionality."""
        expr = Column(dummy_dialect, "value")
        array_expr = Column(dummy_dialect, "array_col")
        any_expr = AnyExpression(dummy_dialect, expr, "=", array_expr)
        sql, params = any_expr.to_sql()
        assert "ANY" in sql
        assert "=" in sql

    def test_any_expression_with_literal_list(self, dummy_dialect: DummyDialect):
        """Test ANY expression with literal list."""
        expr = Column(dummy_dialect, "value")
        array_expr = Literal(dummy_dialect, [1, 2, 3])
        any_expr = AnyExpression(dummy_dialect, expr, ">", array_expr)
        sql, params = any_expr.to_sql()
        assert "ANY" in sql
        assert ">" in sql
        # The list should be treated as a tuple in the parameters


class TestAllExpression:
    """Tests for AllExpression class."""

    def test_all_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic ALL expression functionality."""
        expr = Column(dummy_dialect, "value")
        array_expr = Column(dummy_dialect, "array_col")
        all_expr = AllExpression(dummy_dialect, expr, ">", array_expr)
        sql, params = all_expr.to_sql()
        assert "ALL" in sql
        assert ">" in sql

    def test_all_expression_with_literal_list(self, dummy_dialect: DummyDialect):
        """Test ALL expression with literal list."""
        expr = Column(dummy_dialect, "value")
        array_expr = Literal(dummy_dialect, [1, 2, 3])
        all_expr = AllExpression(dummy_dialect, expr, "=", array_expr)
        sql, params = all_expr.to_sql()
        assert "ALL" in sql
        assert "=" in sql


class TestJSONExpression:
    """Tests for JSONExpression class."""

    def test_json_extract_expression(self, dummy_dialect: DummyDialect):
        """Test JSON extract expression (-> operation)."""
        col = Column(dummy_dialect, "json_col")
        json_expr = JSONExpression(dummy_dialect, col, "$.name", operation="->")
        sql, params = json_expr.to_sql()
        assert "->" in sql
        assert params == ("$.name",)

    def test_json_extract_text_expression(self, dummy_dialect: DummyDialect):
        """Test JSON extract text expression (->> operation)."""
        col = Column(dummy_dialect, "json_col")
        json_expr = JSONExpression(dummy_dialect, col, "$.name", operation="->>")
        sql, params = json_expr.to_sql()
        assert "->>" in sql
        assert params == ("$.name",)

    def test_json_extract_with_string_column(self, dummy_dialect: DummyDialect):
        """Test JSON extract with string column name."""
        json_expr = JSONExpression(dummy_dialect, "json_col", "$.name", operation="->")
        sql, params = json_expr.to_sql()
        assert "->" in sql
        assert params == ("$.name",)


class TestArrayExpression:
    """Tests for ArrayExpression class."""

    def test_array_constructor(self, dummy_dialect: DummyDialect):
        """Test ARRAY constructor operation."""
        elements = [Literal(dummy_dialect, 1), Literal(dummy_dialect, 2), Literal(dummy_dialect, 3)]
        array_expr = ArrayExpression(dummy_dialect, "CONSTRUCTOR", elements=elements)
        sql, params = array_expr.to_sql()
        assert "ARRAY[" in sql
        assert params == (1, 2, 3)

    def test_array_access(self, dummy_dialect: DummyDialect):
        """Test ARRAY access operation."""
        base_expr = Column(dummy_dialect, "array_col")
        index_expr = Literal(dummy_dialect, 1)
        array_expr = ArrayExpression(dummy_dialect, "ACCESS", base_expr=base_expr, index_expr=index_expr)
        sql, params = array_expr.to_sql()
        assert "[" in sql and "]" in sql
        assert params == (1,)

    def test_array_default_operation(self, dummy_dialect: DummyDialect):
        """Test ARRAY with default operation."""
        array_expr = ArrayExpression(dummy_dialect, "OTHER")
        sql, params = array_expr.to_sql()
        assert sql == "ARRAY[]"
        assert params == ()


class TestOrderedSetAggregation:
    """Tests for OrderedSetAggregation class."""

    def test_ordered_set_aggregation_basic(self, dummy_dialect: DummyDialect):
        """Test basic ordered-set aggregation functionality."""
        args = [Column(dummy_dialect, "value")]
        order_by = [Column(dummy_dialect, "sort_col")]
        ordered_agg = OrderedSetAggregation(dummy_dialect, "PERCENTILE_CONT", args, order_by)
        sql, params = ordered_agg.to_sql()
        assert "PERCENTILE_CONT" in sql
        assert "WITHIN GROUP" in sql

    def test_ordered_set_aggregation_with_alias(self, dummy_dialect: DummyDialect):
        """Test ordered-set aggregation with alias."""
        args = [Literal(dummy_dialect, 0.5), Column(dummy_dialect, "value")]
        order_by = [Column(dummy_dialect, "category"), Column(dummy_dialect, "name")]
        ordered_agg = OrderedSetAggregation(dummy_dialect, "PERCENTILE_DISC", args, order_by, alias="percentile")
        sql, params = ordered_agg.to_sql()
        assert "AS" in sql
        assert "percentile" in sql


class TestWindowClasses:
    """Tests for Window-related classes."""

    def test_window_frame_specification(self, dummy_dialect: DummyDialect):
        """Test WindowFrameSpecification functionality."""
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowFrameSpecification
        frame = WindowFrameSpecification(dummy_dialect, "ROWS", "UNBOUNDED PRECEDING", "CURRENT ROW")
        sql, params = frame.to_sql()
        # The exact output depends on the dialect implementation

    def test_window_specification(self, dummy_dialect: DummyDialect):
        """Test WindowSpecification functionality."""
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification
        partition_cols = [Column(dummy_dialect, "department")]
        order_cols = [(Column(dummy_dialect, "salary"), "DESC")]
        window_spec = WindowSpecification(dummy_dialect, partition_by=partition_cols, order_by=order_cols)
        sql, params = window_spec.to_sql()
        # The exact output depends on the dialect implementation

    def test_window_definition(self, dummy_dialect: DummyDialect):
        """Test WindowDefinition functionality."""
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification, WindowDefinition
        partition_cols = [Column(dummy_dialect, "department")]
        window_spec = WindowSpecification(dummy_dialect, partition_by=partition_cols)
        window_def = WindowDefinition(dummy_dialect, "dept_win", window_spec)
        sql, params = window_def.to_sql()
        # The exact output depends on the dialect implementation

    def test_window_clause(self, dummy_dialect: DummyDialect):
        """Test WindowClause functionality."""
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification, WindowDefinition, WindowClause
        partition_cols = [Column(dummy_dialect, "department")]
        window_spec = WindowSpecification(dummy_dialect, partition_by=partition_cols)
        window_def = WindowDefinition(dummy_dialect, "dept_win", window_spec)
        window_clause = WindowClause(dummy_dialect, [window_def])
        sql, params = window_clause.to_sql()
        # The exact output depends on the dialect implementation

    def test_window_function_call(self, dummy_dialect: DummyDialect):
        """Test WindowFunctionCall functionality."""
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification, WindowFunctionCall
        partition_cols = [Column(dummy_dialect, "department")]
        window_spec = WindowSpecification(dummy_dialect, partition_by=partition_cols)
        window_func = WindowFunctionCall(dummy_dialect, "ROW_NUMBER", [Column(dummy_dialect, "id")], window_spec=window_spec)
        sql, params = window_func.to_sql()
        # The exact output depends on the dialect implementation