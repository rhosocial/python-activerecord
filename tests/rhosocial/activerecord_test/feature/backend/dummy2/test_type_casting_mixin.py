# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_type_casting_mixin.py
"""
Tests for the TypeCastingMixin functionality in core expression classes.
This tests the cast() method for various expression classes.
"""
from rhosocial.activerecord.backend.expression import (
    Literal, Column, FunctionCall, Subquery
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestTypeCastingMixin:
    """Tests for TypeCastingMixin functionality across expression classes."""

    def test_column_cast_basic(self, dummy_dialect: DummyDialect):
        """Test Column with basic type cast."""
        col = Column(dummy_dialect, "price")
        col.cast("INTEGER")
        sql, params = col.to_sql()
        assert sql == 'CAST("price" AS INTEGER)'
        assert params == ()

    def test_column_cast_with_varchar_length(self, dummy_dialect: DummyDialect):
        """Test Column with VARCHAR type cast including length modifier."""
        col = Column(dummy_dialect, "name")
        col.cast("VARCHAR(100)")
        sql, params = col.to_sql()
        assert sql == 'CAST("name" AS VARCHAR(100))'
        assert params == ()

    def test_column_cast_with_numeric_precision(self, dummy_dialect: DummyDialect):
        """Test Column with NUMERIC type cast including precision and scale."""
        col = Column(dummy_dialect, "amount")
        col.cast("NUMERIC(10,2)")
        sql, params = col.to_sql()
        assert sql == 'CAST("amount" AS NUMERIC(10,2))'
        assert params == ()

    def test_literal_cast(self, dummy_dialect: DummyDialect):
        """Test Literal with type cast."""
        lit = Literal(dummy_dialect, "123")
        lit.cast("INTEGER")
        sql, params = lit.to_sql()
        assert sql == 'CAST(? AS INTEGER)'
        assert params == ("123",)

    def test_function_call_cast(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with type cast."""
        func = FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "price"))
        func.cast("NUMERIC")
        sql, params = func.to_sql()
        assert sql == 'CAST(SUM("price") AS NUMERIC)'
        assert params == ()

    def test_chained_type_cast(self, dummy_dialect: DummyDialect):
        """Test chained type conversions."""
        col = Column(dummy_dialect, "amount")
        col.cast("MONEY").cast("NUMERIC").cast("FLOAT8")
        sql, params = col.to_sql()
        # Each cast wraps the previous expression
        assert sql == 'CAST(CAST(CAST("amount" AS MONEY) AS NUMERIC) AS FLOAT8)'
        assert params == ()

    def test_cast_with_alias(self, dummy_dialect: DummyDialect):
        """Test type cast with alias."""
        col = Column(dummy_dialect, "value")
        col.cast("INTEGER").as_("int_value")
        sql, params = col.to_sql()
        assert sql == 'CAST("value" AS INTEGER) AS "int_value"'
        assert params == ()

    def test_cast_expression_supports_comparison(self, dummy_dialect: DummyDialect):
        """Test that casted expression supports comparison operators."""
        col = Column(dummy_dialect, "amount")
        col.cast("INTEGER")
        predicate = col > 0
        sql, params = predicate.to_sql()
        assert sql == 'CAST("amount" AS INTEGER) > ?'
        assert params == (0,)

    def test_cast_expression_supports_arithmetic(self, dummy_dialect: DummyDialect):
        """Test that casted expression supports arithmetic operators."""
        col = Column(dummy_dialect, "price")
        col.cast("NUMERIC")
        result = col * 1.1
        sql, params = result.to_sql()
        assert sql == 'CAST("price" AS NUMERIC) * ?'
        assert params == (1.1,)

    def test_cast_expression_supports_comparison_equality(self, dummy_dialect: DummyDialect):
        """Test that casted expression supports equality comparison."""
        col = Column(dummy_dialect, "status")
        col.cast("INTEGER")
        predicate = col == 1
        sql, params = predicate.to_sql()
        assert sql == 'CAST("status" AS INTEGER) = ?'
        assert params == (1,)

    def test_cast_expression_supports_comparison_in(self, dummy_dialect: DummyDialect):
        """Test that casted expression supports IN predicate."""
        col = Column(dummy_dialect, "category")
        col.cast("INTEGER")
        predicate = col.in_([1, 2, 3])
        sql, params = predicate.to_sql()
        assert sql == 'CAST("category" AS INTEGER) IN (?, ?, ?)'
        assert params == (1, 2, 3)

    def test_cast_expression_supports_aliasable(self, dummy_dialect: DummyDialect):
        """Test that casted expression inherits AliasableMixin."""
        col = Column(dummy_dialect, "value")
        col.cast("TEXT")
        # Verify as_ method exists and works
        col.as_("text_value")
        assert col.alias == "text_value"
        sql, params = col.to_sql()
        assert 'AS "text_value"' in sql

    def test_cast_expression_inheritance_chain(self, dummy_dialect: DummyDialect):
        """Test that casted expression inherits all expected mixins."""
        col = Column(dummy_dialect, "value")
        col.cast("INTEGER")

        # Verify TypeCastingMixin is inherited (for chaining)
        assert hasattr(col, 'cast')

        # Verify AliasableMixin is inherited
        assert hasattr(col, 'as_')

        # Verify ArithmeticMixin is inherited
        assert hasattr(col, '__add__')
        assert hasattr(col, '__sub__')
        assert hasattr(col, '__mul__')

        # Verify ComparisonMixin is inherited
        assert hasattr(col, '__eq__')
        assert hasattr(col, '__gt__')
        assert hasattr(col, 'in_')

    def test_cast_with_table_qualified_column(self, dummy_dialect: DummyDialect):
        """Test type cast on table-qualified column."""
        col = Column(dummy_dialect, "amount", table="orders")
        col.cast("INTEGER")
        sql, params = col.to_sql()
        assert sql == 'CAST("orders"."amount" AS INTEGER)'
        assert params == ()

    def test_nested_function_cast(self, dummy_dialect: DummyDialect):
        """Test type cast on function result."""
        inner_func = FunctionCall(dummy_dialect, "COALESCE",
                                   Column(dummy_dialect, "price"),
                                   Literal(dummy_dialect, 0))
        inner_func.cast("NUMERIC(10,2)")
        sql, params = inner_func.to_sql()
        assert sql == 'CAST(COALESCE("price", ?) AS NUMERIC(10,2))'
        assert params == (0,)

    def test_chained_cast_after_alias(self, dummy_dialect: DummyDialect):
        """Test chained cast after applying alias."""
        col = Column(dummy_dialect, "amount")
        col.cast("MONEY").as_("m").cast("NUMERIC")
        sql, params = col.to_sql()
        # The cast should wrap the previous expression
        assert 'CAST(' in sql
        assert 'AS NUMERIC)' in sql
        assert params == ()

    def test_multiple_arithmetic_with_cast(self, dummy_dialect: DummyDialect):
        """Test multiple arithmetic operations with type cast."""
        col1 = Column(dummy_dialect, "price1")
        col2 = Column(dummy_dialect, "price2")
        col1.cast("NUMERIC")
        col2.cast("NUMERIC")
        result = col1 + col2
        sql, params = result.to_sql()
        assert sql == 'CAST("price1" AS NUMERIC) + CAST("price2" AS NUMERIC)'
        assert params == ()

    def test_cast_preserves_dialect(self, dummy_dialect: DummyDialect):
        """Test that cast preserves the dialect from source expression."""
        col = Column(dummy_dialect, "value")
        col.cast("INTEGER")
        assert col.dialect is dummy_dialect

    def test_double_chained_cast_preserves_dialect(self, dummy_dialect: DummyDialect):
        """Test that double chained cast preserves the dialect."""
        col = Column(dummy_dialect, "value")
        col.cast("MONEY").cast("NUMERIC")
        assert col.dialect is dummy_dialect

    def test_cast_types_list_accumulates(self, dummy_dialect: DummyDialect):
        """Test that _cast_types list accumulates multiple casts."""
        col = Column(dummy_dialect, "value")
        assert col._cast_types == []
        col.cast("INTEGER")
        assert col._cast_types == ["INTEGER"]
        col.cast("VARCHAR")
        assert col._cast_types == ["INTEGER", "VARCHAR"]

    def test_cast_returns_self(self, dummy_dialect: DummyDialect):
        """Test that cast() returns self for method chaining."""
        col = Column(dummy_dialect, "value")
        result = col.cast("INTEGER")
        assert result is col
