# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_data_types.py
"""Tests for generic SQL data types and value-object semantics.

Generic data types are dialect-independent structure/value classes used by
the expression system. They must behave correctly on any backend, including
the Dummy backend (which provides the generic formatters).
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    ComparisonPredicate,
    JSONPathMode,
    ArrayExpression,
)
from rhosocial.activerecord.backend.expression.aggregates import AggregateFunctionCall
from rhosocial.activerecord.backend.expression.functions import count, sum_
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    CharType,
    CustomType,
    DateTimeType,
    DecimalType,
    FloatType,
    IntType,
    IntegerType,
    IntervalType,
    TimeType,
    TimeTzType,
    TimestampTzType,
    TimestampType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect() -> DummyDialect:
    return DummyDialect()


class TestDataTypeValueSemantics:
    """Generic data types behave as value objects."""

    def test_datetime_types_equality(self):
        assert DateTimeType(6) == DateTimeType(6)
        assert DateTimeType(6) != DateTimeType(0)
        assert DateTimeType(6) != TimeType(6)

    def test_datetime_types_hash(self):
        assert hash(DateTimeType(6)) == hash(DateTimeType(6))
        assert hash(TimeType(6)) == hash(TimeType(6))
        assert hash(TimestampType(3)) == hash(TimestampType(3))
        assert hash(TimestampTzType(0)) == hash(TimestampTzType(0))
        assert hash(TimeTzType(2)) == hash(TimeTzType(2))

    def test_time_equality(self):
        assert TimeType(3) == TimeType(3)
        assert TimeType(3) != TimeType(6)

    def test_interval_type_equality_hash(self):
        assert IntervalType("DAY TO SECOND") == IntervalType("DAY TO SECOND")
        assert IntervalType("YEAR") != IntervalType("DAY TO SECOND")
        assert hash(IntervalType("YEAR")) == hash(IntervalType("YEAR"))

    def test_string_types_equality_hash(self):
        assert CharType(10) == CharType(10)
        assert CharType(10) != CharType(20)
        assert hash(VarCharType(255)) == hash(VarCharType(255))
        assert VarCharType(255) == VarCharType(255)

    def test_numeric_types_equality_hash(self):
        assert DecimalType(10, 2) == DecimalType(10, 2)
        assert DecimalType(10, 2) != DecimalType(10, 3)
        assert hash(FloatType(53)) == hash(FloatType(53))
        assert FloatType(24) == FloatType(24)

    def test_custom_type_equality_hash(self):
        assert CustomType("geometry") == CustomType("geometry")
        assert CustomType("geometry") != CustomType("geography")
        assert hash(CustomType("geometry")) == hash(CustomType("geometry"))

    def test_custom_type_roundtrip_sql(self, dialect):
        t = CustomType("GEOMETRY", dialect=dialect)
        assert t.to_sql() == ("GEOMETRY", ())

    def test_data_type_without_dialect_raises(self):
        with pytest.raises(ValueError):
            IntegerType().to_sql()

    def test_data_type_to_sql_with_dialect_arg(self, dialect):
        assert IntType().to_sql(dialect) == ("INT", ())

    def test_cross_type_inequality(self):
        assert IntegerType() != CharType(10)


class TestArrayType:
    """Array container type semantics."""

    def test_array_equality(self):
        assert ArrayType(IntegerType()) == ArrayType(IntegerType())
        assert ArrayType(IntegerType(), dimensions=2) != ArrayType(IntegerType())

    def test_array_hash(self):
        assert hash(ArrayType(IntegerType())) == hash(ArrayType(IntegerType()))

    def test_array_is_equivalent(self):
        assert ArrayType(IntegerType()).is_equivalent(ArrayType(IntegerType()))
        assert not ArrayType(IntegerType(), dimensions=2).is_equivalent(ArrayType(IntegerType()))

    def test_array_is_element_type_equivalent_with_array(self):
        assert ArrayType(IntegerType()).is_element_type_equivalent(ArrayType(IntegerType(), dimensions=2))

    def test_array_is_element_type_equivalent_with_plain_type(self):
        assert ArrayType(IntegerType()).is_element_type_equivalent(IntegerType())
        assert not ArrayType(IntegerType()).is_element_type_equivalent(CharType(10))

    def test_array_type_params(self):
        assert ArrayType(IntegerType(), dimensions=2)._type_params() == (IntegerType(), 2)

    def test_array_repr(self):
        assert "ArrayType" in repr(ArrayType(IntegerType()))

    def test_array_expression_constructor(self, dialect):
        expr = ArrayExpression(
            dialect,
            "CONSTRUCTOR",
            elements=[Literal(dialect, 1), Literal(dialect, 2)],
        )
        sql, params = expr.to_sql()
        assert sql == "ARRAY[?, ?]"
        assert params == (1, 2)


class TestJSONPathMode:
    """JSONPathMode coercion helper."""

    def test_from_value_none(self):
        assert JSONPathMode.from_value(None) is JSONPathMode.AUTO

    def test_from_value_enum(self):
        assert JSONPathMode.from_value(JSONPathMode.AUTO) is JSONPathMode.AUTO

    def test_from_value_str(self):
        assert JSONPathMode.from_value("arrow") is JSONPathMode.ARROW

    def test_from_value_invalid_string(self):
        with pytest.raises(ValueError):
            JSONPathMode.from_value("strict")

    def test_from_value_invalid_type(self):
        with pytest.raises(TypeError):
            JSONPathMode.from_value(42)


class TestAggregateGetParamsWithFilter:
    """AggregateFunctionCall.get_params() includes the filter predicate."""

    def test_get_params_with_filter(self, dialect):
        agg = count(dialect, "*", alias="active_count").filter(
            Column(dialect, "status") == Literal(dialect, "active")
        )
        params = agg.get_params()
        assert "filter_predicate" in params
        assert isinstance(params["filter_predicate"], ComparisonPredicate)

    def test_get_params_without_filter(self, dialect):
        agg = sum_(dialect, Column(dialect, "amount"), alias="total")
        params = agg.get_params()
        assert params.get("filter_predicate") is None

    def test_filter_returns_self(self, dialect):
        agg = AggregateFunctionCall(dialect, "COUNT", "*")
        predicate = Column(dialect, "status") == Literal(dialect, "active")
        assert agg.filter(predicate) is agg
        assert agg.get_params()["filter_predicate"] is predicate

    def test_chained_filters_combine(self, dialect):
        agg = AggregateFunctionCall(dialect, "COUNT", "*")
        agg.filter(Column(dialect, "a") == Literal(dialect, 1))
        agg.filter(Column(dialect, "b") == Literal(dialect, 2))
        assert "AND" in agg.get_params()["filter_predicate"].to_sql()[0]
