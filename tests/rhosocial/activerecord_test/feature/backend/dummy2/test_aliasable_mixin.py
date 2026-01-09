# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_aliasable_mixin.py
"""
Tests for the AliasableMixin functionality in core expression classes.
This tests the as_() method and alias initialization for various expression classes.
"""
from rhosocial.activerecord.backend.expression import (
    Literal, Column, FunctionCall, Subquery
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    CastExpression, JSONExpression, ArrayExpression, OrderedSetAggregation
)
from rhosocial.activerecord.backend.expression.aggregates import AggregateFunctionCall
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestAliasableMixin:
    """Tests for AliasableMixin functionality across expression classes."""

    def test_column_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test Column with alias specified during initialization."""
        col = Column(dummy_dialect, "name", alias="user_name")
        assert col.alias == "user_name"
        sql, params = col.to_sql()
        assert sql == '"name" AS "user_name"'
        assert params == ()

    def test_column_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test Column with alias specified using as_() method."""
        col = Column(dummy_dialect, "name").as_("user_name")
        assert col.alias == "user_name"
        sql, params = col.to_sql()
        assert sql == '"name" AS "user_name"'
        assert params == ()

    def test_function_call_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with alias specified during initialization."""
        func = FunctionCall(dummy_dialect, "UPPER", Column(dummy_dialect, "name"), alias="upper_name")
        assert func.alias == "upper_name"
        sql, params = func.to_sql()
        assert sql == 'UPPER("name") AS "upper_name"'
        assert params == ()

    def test_function_call_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with alias specified using as_() method."""
        func = FunctionCall(dummy_dialect, "UPPER", Column(dummy_dialect, "name")).as_("upper_name")
        assert func.alias == "upper_name"
        sql, params = func.to_sql()
        assert sql == 'UPPER("name") AS "upper_name"'
        assert params == ()

    def test_subquery_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test Subquery with alias specified during initialization."""
        subq = Subquery(dummy_dialect, "SELECT 1", alias="subquery_alias")
        assert subq.alias == "subquery_alias"
        sql, params = subq.to_sql()
        assert sql == '(SELECT 1) AS "subquery_alias"'
        assert params == ()

    def test_subquery_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test Subquery with alias specified using as_() method."""
        subq = Subquery(dummy_dialect, "SELECT 1").as_("subquery_alias")
        assert subq.alias == "subquery_alias"
        sql, params = subq.to_sql()
        assert sql == '(SELECT 1) AS "subquery_alias"'
        assert params == ()

    def test_aggregate_function_call_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test AggregateFunctionCall with alias specified during initialization."""
        agg = AggregateFunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "*"), alias="total_count")
        assert agg.alias == "total_count"
        sql, params = agg.to_sql()
        assert sql == 'COUNT("*") AS "total_count"'
        assert params == ()

    def test_aggregate_function_call_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test AggregateFunctionCall with alias specified using as_() method."""
        agg = AggregateFunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "*")).as_("total_count")
        assert agg.alias == "total_count"
        sql, params = agg.to_sql()
        assert sql == 'COUNT("*") AS "total_count"'
        assert params == ()

    def test_cast_expression_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test CastExpression with alias specified during initialization."""
        cast = CastExpression(dummy_dialect, Column(dummy_dialect, "id"), "TEXT", alias="id_text")
        assert cast.alias == "id_text"
        sql, params = cast.to_sql()
        assert sql == 'CAST("id" AS TEXT) AS "id_text"'
        assert params == ()

    def test_cast_expression_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test CastExpression with alias specified using as_() method."""
        cast = CastExpression(dummy_dialect, Column(dummy_dialect, "id"), "TEXT").as_("id_text")
        assert cast.alias == "id_text"
        sql, params = cast.to_sql()
        assert sql == 'CAST("id" AS TEXT) AS "id_text"'
        assert params == ()

    def test_json_expression_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test JSONExpression with alias specified during initialization."""
        json_expr = JSONExpression(dummy_dialect, Column(dummy_dialect, "data"), "$.name", alias="name_field")
        assert json_expr.alias == "name_field"
        sql, params = json_expr.to_sql()
        assert sql == '("data" -> ?) AS "name_field"'
        assert params == ("$.name",)

    def test_json_expression_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test JSONExpression with alias specified using as_() method."""
        json_expr = JSONExpression(dummy_dialect, Column(dummy_dialect, "data"), "$.name").as_("name_field")
        assert json_expr.alias == "name_field"
        sql, params = json_expr.to_sql()
        assert sql == '("data" -> ?) AS "name_field"'
        assert params == ("$.name",)

    def test_array_expression_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test ArrayExpression with alias specified during initialization."""
        arr = ArrayExpression(dummy_dialect, "CONSTRUCTOR", elements=[Column(dummy_dialect, "a")], alias="arr_alias")
        assert arr.alias == "arr_alias"
        sql, params = arr.to_sql()
        assert sql == 'ARRAY["a"] AS "arr_alias"'
        assert params == ()

    def test_array_expression_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test ArrayExpression with alias specified using as_() method."""
        arr = ArrayExpression(dummy_dialect, "CONSTRUCTOR", elements=[Column(dummy_dialect, "a")]).as_("arr_alias")
        assert arr.alias == "arr_alias"
        sql, params = arr.to_sql()
        assert sql == 'ARRAY["a"] AS "arr_alias"'
        assert params == ()

    def test_ordered_set_aggregation_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test OrderedSetAggregation with alias specified during initialization."""
        ord_agg = OrderedSetAggregation(
            dummy_dialect, 
            "PERCENTILE_CONT", 
            [Literal(dummy_dialect, 0.5)], 
            [Column(dummy_dialect, "value")], 
            alias="percentile_50"
        )
        assert ord_agg.alias == "percentile_50"
        sql, params = ord_agg.to_sql()
        assert sql == 'PERCENTILE_CONT(?) WITHIN GROUP (ORDER BY "value") AS "percentile_50"'
        assert params == (0.5,)

    def test_ordered_set_aggregation_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test OrderedSetAggregation with alias specified using as_() method."""
        ord_agg = OrderedSetAggregation(
            dummy_dialect, 
            "PERCENTILE_CONT", 
            [Literal(dummy_dialect, 0.5)], 
            [Column(dummy_dialect, "value")]
        ).as_("percentile_50")
        assert ord_agg.alias == "percentile_50"
        sql, params = ord_agg.to_sql()
        assert sql == 'PERCENTILE_CONT(?) WITHIN GROUP (ORDER BY "value") AS "percentile_50"'
        assert params == (0.5,)

    def test_alias_overrides_initialization(self, dummy_dialect: DummyDialect):
        """Test that as_() method overrides alias set during initialization."""
        col = Column(dummy_dialect, "name", alias="init_alias").as_("method_alias")
        assert col.alias == "method_alias"
        sql, params = col.to_sql()
        assert sql == '"name" AS "method_alias"'
        assert params == ()