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
    FunctionCall,
    JSONPathMode,
    ArrayOperation,
    NumericColumn,
    StringColumn,)
from rhosocial.activerecord.backend.expression.functions import count, sum_
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    CharType,
    CustomType,
    DateTimeType,
    DecimalType,
    FloatType,
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
        assert DateTimeType(None, 6) == DateTimeType(None, 6)
        assert DateTimeType(None, 6) != DateTimeType(None, 0)
        assert DateTimeType(None, 6) != TimeType(None, 6)

    def test_datetime_types_hash(self):
        assert hash(DateTimeType(None, 6)) == hash(DateTimeType(None, 6))
        assert hash(TimeType(None, 6)) == hash(TimeType(None, 6))
        assert hash(TimestampType(None, 3)) == hash(TimestampType(None, 3))
        assert hash(TimestampTzType(None, 0)) == hash(TimestampTzType(None, 0))
        assert hash(TimeTzType(None, 2)) == hash(TimeTzType(None, 2))

    def test_time_equality(self):
        assert TimeType(None, 3) == TimeType(None, 3)
        assert TimeType(None, 3) != TimeType(None, 6)

    def test_interval_type_equality_hash(self):
        assert IntervalType(None, "DAY TO SECOND") == IntervalType(None, "DAY TO SECOND")
        assert IntervalType(None, "YEAR") != IntervalType(None, "DAY TO SECOND")
        assert hash(IntervalType(None, "YEAR")) == hash(IntervalType(None, "YEAR"))

    def test_string_types_equality_hash(self):
        assert CharType(None, 10) == CharType(None, 10)
        assert CharType(None, 10) != CharType(None, 20)
        assert hash(VarCharType(None, 255)) == hash(VarCharType(None, 255))
        assert VarCharType(None, 255) == VarCharType(None, 255)

    def test_numeric_types_equality_hash(self):
        assert DecimalType(None, 10, 2) == DecimalType(None, 10, 2)
        assert DecimalType(None, 10, 2) != DecimalType(None, 10, 3)
        assert hash(FloatType(None, 53)) == hash(FloatType(None, 53))
        assert FloatType(None, 24) == FloatType(None, 24)

    def test_custom_type_equality_hash(self):
        assert CustomType(None, raw="geometry") == CustomType(None, raw="geometry")
        assert CustomType(None, raw="geometry") != CustomType(None, raw="geography")
        assert hash(CustomType(None, raw="geometry")) == hash(CustomType(None, raw="geometry"))

    def test_custom_type_roundtrip_sql(self, dialect):
        t = CustomType(dialect, raw="GEOMETRY")
        assert t.to_sql() == ("GEOMETRY", ())

    def test_data_type_without_dialect_raises(self):
        with pytest.raises(ValueError):
            IntegerType().to_sql()

    def test_data_type_to_sql_with_dialect_arg(self, dialect):
        assert IntegerType(dialect=dialect, spelling="int").to_sql() == ("INT", ())

    def test_cross_type_inequality(self):
        assert IntegerType() != CharType(None, 10)


class TestArrayType:
    """Array container type semantics."""

    def test_array_equality(self):
        assert ArrayType(None, element_type=IntegerType()) == ArrayType(None, element_type=IntegerType())
        assert ArrayType(None, element_type=IntegerType(), dimensions=2) != ArrayType(None, element_type=IntegerType())

    def test_array_hash(self):
        assert hash(ArrayType(None, element_type=IntegerType())) == hash(ArrayType(None, element_type=IntegerType()))

    def test_array_is_equivalent(self):
        assert ArrayType(None, element_type=IntegerType()) == ArrayType(None, element_type=IntegerType())
        assert ArrayType(None, element_type=IntegerType(), dimensions=2) != ArrayType(None, element_type=IntegerType())

    def test_array_is_element_type_equivalent_with_array(self):
        """``is_element_type_equivalent`` answers a different question from
        ``==``: not "is this the same declaration" but "does this array store
        the same kind of thing", so dimensions are ignored."""
        assert ArrayType(None, element_type=IntegerType()).is_element_type_equivalent(ArrayType(None, element_type=IntegerType(), dimensions=2))

    def test_array_is_element_type_equivalent_with_plain_type(self):
        assert ArrayType(None, element_type=IntegerType()).is_element_type_equivalent(IntegerType())
        assert not ArrayType(None, element_type=IntegerType()).is_element_type_equivalent(CharType(None, 10))

    def test_array_declares_its_identity_fields(self):
        """An array's identity is its element type and its dimensionality.

        Declared as a class constant rather than a method, so ``__eq__``,
        ``__hash__`` and ``repr`` cannot each answer the question differently.
        """
        assert ArrayType.PARAMETERS == ("element_type", "dimensions")
        arr = ArrayType(None, element_type=IntegerType(), dimensions=2)
        assert arr.identity() == (IntegerType(), 2)
        # and a dimensionality change is a change of declaration
        assert arr != ArrayType(None, element_type=IntegerType(), dimensions=1)

    def test_array_repr(self):
        assert "ArrayType" in repr(ArrayType(None, element_type=IntegerType()))

    def test_array_expression_constructor(self, dialect):
        expr = ArrayOperation(
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
    """FunctionCall.get_params() includes the filter predicate."""

    def test_get_params_with_filter(self, dialect):
        agg = count(dialect, "*", alias="active_count").filter(
            StringColumn(dialect, "status") == Literal(dialect, "active")
        )
        params = agg.get_params()
        assert "filter_predicate" in params
        assert isinstance(params["filter_predicate"], ComparisonPredicate)

    def test_get_params_without_filter(self, dialect):
        agg = sum_(dialect, Column(dialect, "amount"), alias="total")
        params = agg.get_params()
        assert params.get("filter_predicate") is None

    def test_filter_returns_self(self, dialect):
        agg = FunctionCall(dialect, "COUNT", "*", is_aggregate=True)
        predicate = StringColumn(dialect, "status") == Literal(dialect, "active")
        assert agg.filter(predicate) is agg
        assert agg.get_params()["filter_predicate"] is predicate

    def test_chained_filters_combine(self, dialect):
        agg = FunctionCall(dialect, "COUNT", "*", is_aggregate=True)
        agg.filter(NumericColumn(dialect, "a") == Literal(dialect, 1))
        agg.filter(NumericColumn(dialect, "b") == Literal(dialect, 2))
        assert "AND" in agg.get_params()["filter_predicate"].to_sql()[0]
