# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_aliasable_mixin.py
"""
Tests for the AliasableMixin functionality in core expression classes.
This tests the as_() method and alias initialization for various expression classes.
"""

import pytest

from rhosocial.activerecord.backend.expression import Literal, Column, FunctionCall, Subquery, TableExpression
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression
from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
from rhosocial.activerecord.backend.expression.advanced_functions import (
    JSONExpression,
    ArrayExpression,
    OrderedSetAggregation,
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
        """Test cast() method with alias specified during initialization."""
        cast = Column(dummy_dialect, "id", alias="id_text").cast("TEXT")
        assert cast.alias == "id_text"
        sql, params = cast.to_sql()
        assert sql == 'CAST("id" AS TEXT) AS "id_text"'
        assert params == ()

    def test_cast_expression_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test cast() method with alias specified using as_() method."""
        cast = Column(dummy_dialect, "id").as_("id_text").cast("TEXT")
        assert cast.alias == "id_text"
        sql, params = cast.to_sql()
        assert sql == 'CAST("id" AS TEXT) AS "id_text"'
        assert params == ()

    def test_json_expression_alias_initialization(self, dummy_dialect: DummyDialect):
        """Test JSONExpression with alias specified during initialization."""
        json_expr = JSONExpression(dummy_dialect, Column(dummy_dialect, "data"), "$.name", alias="name_field")
        assert json_expr.alias == "name_field"
        sql, params = json_expr.to_sql()
        assert sql == 'JSON_EXTRACT("data", \'$.name\') AS "name_field"'
        assert params == ()

    def test_json_expression_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test JSONExpression with alias specified using as_() method."""
        json_expr = JSONExpression(dummy_dialect, Column(dummy_dialect, "data"), "$.name").as_("name_field")
        assert json_expr.alias == "name_field"
        sql, params = json_expr.to_sql()
        assert sql == 'JSON_EXTRACT("data", \'$.name\') AS "name_field"'
        assert params == ()

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
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        ord_agg = OrderedSetAggregation(
            dummy_dialect,
            "PERCENTILE_CONT",
            [Literal(dummy_dialect, 0.5)],
            OrderByClause(dummy_dialect, [Column(dummy_dialect, "value")]),
            alias="percentile_50",
        )
        assert ord_agg.alias == "percentile_50"
        sql, params = ord_agg.to_sql()
        assert sql == 'PERCENTILE_CONT(?) WITHIN GROUP (ORDER BY "value") AS "percentile_50"'
        assert params == (0.5,)

    def test_ordered_set_aggregation_alias_with_as_method(self, dummy_dialect: DummyDialect):
        """Test OrderedSetAggregation with alias specified using as_() method."""
        from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

        ord_agg = OrderedSetAggregation(
            dummy_dialect,
            "PERCENTILE_CONT",
            [Literal(dummy_dialect, 0.5)],
            OrderByClause(dummy_dialect, [Column(dummy_dialect, "value")]),
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


class TestAliasNonContamination:
    """Tests that ``as_()`` returns a new aliased copy without mutating the
    original, so aliases never leak across reuse or nesting."""

    def test_original_untouched_after_as(self, dummy_dialect: DummyDialect):
        col = Column(dummy_dialect, "name")
        aliased = col.as_("user_name")
        assert aliased.alias == "user_name"
        assert col.alias is None
        assert aliased is not col
        # Original renders without AS; the copy renders with AS.
        assert col.to_sql()[0] == '"name"'
        assert aliased.to_sql()[0] == '"name" AS "user_name"'

    def test_reuse_in_two_contexts_no_leak(self, dummy_dialect: DummyDialect):
        # Same expression used in SELECT (aliased) and ORDER BY (unaliased).
        dist = BinaryArithmeticExpression(
            dummy_dialect, "<=>", Column(dummy_dialect, "embedding"),
            Literal(dummy_dialect, "[1, 2, 3]"),
        )
        select_expr = dist.as_("cosine_distance")
        order_by_expr = dist  # original, must stay unaliased
        assert 'AS "cosine_distance"' in select_expr.to_sql()[0]
        assert "AS" not in order_by_expr.to_sql()[0]

    def test_nested_parent_no_contamination(self, dummy_dialect: DummyDialect):
        # Aliasing a child copy must not contaminate the parent expression that
        # still references the unaliased original.
        child = Column(dummy_dialect, "embedding")
        child_aliased = child.as_("emb")
        parent = BinaryArithmeticExpression(
            dummy_dialect, "-", Literal(dummy_dialect, 1), child
        )
        parent_sql = parent.to_sql()[0]
        # The parent uses the unaliased original -> no AS inside parentheses.
        assert "AS" not in parent_sql
        assert child_aliased.to_sql()[0] == '"embedding" AS "emb"'

    def test_multi_level_nested_alias(self, dummy_dialect: DummyDialect):
        # Aliasing the top of a multi-level tree renders AS at the top only;
        # reusing the aliased copy nested does not leak into the base.
        leaf = Column(dummy_dialect, "embedding")
        inner = BinaryArithmeticExpression(
            dummy_dialect, "<=>", leaf, Literal(dummy_dialect, "[1, 2, 3]")
        )
        outer = BinaryArithmeticExpression(
            dummy_dialect, "-", Literal(dummy_dialect, 1), inner
        )
        outer_aliased = outer.as_("cosine_similarity")
        # Aliased top renders with AS at the outermost position only.
        outer_sql = outer_aliased.to_sql()[0]
        assert outer_sql.endswith('AS "cosine_similarity"')
        assert outer_sql.count(" AS ") == 1
        # The base tree is untouched.
        assert "AS" not in outer.to_sql()[0]

    def test_independent_aliases_from_same_source(self, dummy_dialect: DummyDialect):
        col = Column(dummy_dialect, "name")
        a = col.as_("a")
        b = col.as_("b")
        assert a.alias == "a"
        assert b.alias == "b"
        assert col.alias is None
        assert a is not b

    def test_chained_as_then_cast_keeps_alias(self, dummy_dialect: DummyDialect):
        cast = Column(dummy_dialect, "id").as_("id_text").cast("TEXT")
        assert cast.alias == "id_text"
        assert cast.to_sql()[0] == 'CAST("id" AS TEXT) AS "id_text"'

    @pytest.mark.parametrize(
        "factory",
        [
            lambda d: Literal(d, 1),
            lambda d: Column(d, "name"),
            lambda d: FunctionCall(d, "UPPER", Column(d, "name")),
            lambda d: Subquery(d, "SELECT 1"),
            lambda d: TableExpression(d, "users"),
            lambda d: JoinExpression(
                d,
                left_table=TableExpression(d, "users"),
                right_table=TableExpression(d, "items"),
                join_type="INNER JOIN",
                condition=Column(d, "id", "u") == Column(d, "user_id", "i"),
            ),
        ],
        ids=["Literal", "Column", "FunctionCall", "Subquery", "TableExpression", "JoinExpression"],
    )
    def test_as_returns_copy_for_each_expression_type(
        self, dummy_dialect: DummyDialect, factory
    ):
        expr = factory(dummy_dialect)
        aliased = expr.as_("the_alias")
        assert aliased is not expr
        assert aliased.alias == "the_alias"
        assert expr.alias is None
        assert "AS \"the_alias\"" in aliased.to_sql()[0]
        assert "AS" not in expr.to_sql()[0]

    def test_re_aliasing_copy_is_independent(self, dummy_dialect: DummyDialect):
        col = Column(dummy_dialect, "name")
        first = col.as_("first")
        second = first.as_("second")
        assert second.alias == "second"
        assert first.alias == "first"
        assert col.alias is None
        assert second.to_sql()[0] == '"name" AS "second"'
        assert first.to_sql()[0] == '"name" AS "first"'

    def test_cast_on_aliased_copy_does_not_leak_to_original(
        self, dummy_dialect: DummyDialect
    ):
        col = Column(dummy_dialect, "id")
        aliased = col.as_("id_text")
        aliased.cast("TEXT")
        assert aliased.to_sql()[0] == 'CAST("id" AS TEXT) AS "id_text"'
        assert col.to_sql()[0] == '"id"'
        assert col.alias is None

    def test_cast_on_original_does_not_leak_to_aliased_copy(
        self, dummy_dialect: DummyDialect
    ):
        col = Column(dummy_dialect, "amount").cast("MONEY")
        aliased = col.as_("m")
        col.cast("NUMERIC")
        # The copy snapshots the cast list at as_() time.
        assert aliased.to_sql()[0] == 'CAST("amount" AS MONEY) AS "m"'
        assert col.to_sql()[0] == 'CAST(CAST("amount" AS MONEY) AS NUMERIC)'
        assert col.alias is None
