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
        assert DateTimeType(precision=6) == DateTimeType(precision=6)
        assert DateTimeType(precision=6) != DateTimeType(precision=0)
        assert DateTimeType(precision=6) != TimeType(precision=6)

    def test_datetime_types_hash(self):
        assert hash(DateTimeType(precision=6)) == hash(DateTimeType(precision=6))
        assert hash(TimeType(precision=6)) == hash(TimeType(precision=6))
        assert hash(TimestampType(precision=3)) == hash(TimestampType(precision=3))
        assert hash(TimestampTzType(precision=0)) == hash(TimestampTzType(precision=0))
        assert hash(TimeTzType(precision=2)) == hash(TimeTzType(precision=2))

    def test_time_equality(self):
        assert TimeType(precision=3) == TimeType(precision=3)
        assert TimeType(precision=3) != TimeType(precision=6)

    def test_interval_type_equality_hash(self):
        assert IntervalType(fields="DAY TO SECOND") == IntervalType(fields="DAY TO SECOND")
        assert IntervalType(fields="YEAR") != IntervalType(fields="DAY TO SECOND")
        assert hash(IntervalType(fields="YEAR")) == hash(IntervalType(fields="YEAR"))

    def test_string_types_equality_hash(self):
        assert CharType(length=10) == CharType(length=10)
        assert CharType(length=10) != CharType(length=20)
        assert hash(VarCharType(length=255)) == hash(VarCharType(length=255))
        assert VarCharType(length=255) == VarCharType(length=255)

    def test_numeric_types_equality_hash(self):
        assert DecimalType(precision=10, scale=2) == DecimalType(precision=10, scale=2)
        assert DecimalType(precision=10, scale=2) != DecimalType(precision=10, scale=3)
        assert hash(FloatType(precision=53)) == hash(FloatType(precision=53))
        assert FloatType(precision=24) == FloatType(precision=24)

    def test_custom_type_equality_hash(self):
        assert CustomType(raw="geometry") == CustomType(raw="geometry")
        assert CustomType(raw="geometry") != CustomType(raw="geography")
        assert hash(CustomType(raw="geometry")) == hash(CustomType(raw="geometry"))

    def test_custom_type_roundtrip_sql(self, dialect):
        t = CustomType(dialect=dialect, raw="GEOMETRY")
        assert t.to_sql() == ("GEOMETRY", ())

    def test_data_type_without_dialect_raises(self):
        with pytest.raises(ValueError):
            IntegerType().to_sql()

    def test_data_type_to_sql_with_dialect_arg(self, dialect):
        assert IntType().to_sql(dialect) == ("INT", ())

    def test_cross_type_inequality(self):
        assert IntegerType() != CharType(length=10)


class TestArrayType:
    """Array container type semantics."""

    def test_array_equality(self):
        assert ArrayType(element_type=IntegerType()) == ArrayType(element_type=IntegerType())
        assert ArrayType(element_type=IntegerType(), dimensions=2) != ArrayType(element_type=IntegerType())

    def test_array_hash(self):
        assert hash(ArrayType(element_type=IntegerType())) == hash(ArrayType(element_type=IntegerType()))

    def test_array_is_equivalent(self):
        assert ArrayType(element_type=IntegerType()).is_equivalent(ArrayType(element_type=IntegerType()))
        assert not ArrayType(element_type=IntegerType(), dimensions=2).is_equivalent(ArrayType(element_type=IntegerType()))

    def test_array_is_element_type_equivalent_with_array(self):
        assert ArrayType(element_type=IntegerType()).is_element_type_equivalent(ArrayType(element_type=IntegerType(), dimensions=2))

    def test_array_is_element_type_equivalent_with_plain_type(self):
        assert ArrayType(element_type=IntegerType()).is_element_type_equivalent(IntegerType())
        assert not ArrayType(element_type=IntegerType()).is_element_type_equivalent(CharType(length=10))

    def test_array_type_params(self):
        assert ArrayType(element_type=IntegerType(), dimensions=2)._type_params() == (IntegerType(), 2)

    def test_array_repr(self):
        assert "ArrayType" in repr(ArrayType(element_type=IntegerType()))

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
