# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_collation_datetime.py
"""Tests for collation and date/time expressions on the Dummy backend.

These are generic (standard-SQL / dialect-independent) expression behaviors.
DummyDialect implements the generic mixin formatters, so the SQL generation
must work without binding to any concrete database.

The one deliberately unsupported case is ``date_diff`` (DateTimeDiffExpression
to_sql), which is inherently backend-specific; it must raise
UnsupportedFeatureError on Dummy.
"""

from enum import Enum

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    DateTimeAddExpression,
    DateTimeDiffExpression,
    DateTimeSubtractExpression,
    DatePartExpression,
    DateTruncExpression,
    ExtractExpression,
    IntervalExpression,
    DateTimeField,
    IntervalUnit,
    collate,
    date_add,
    date_diff,
    date_sub,
    extract,
    interval,
)
from rhosocial.activerecord.backend.expression.datetime import (
    normalize_datetime_field,
    normalize_interval_unit,
    validate_interval_value,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class DummyCollation(Enum):
    NOCASE = "NOCASE"
    BINARY = "BINARY"


@pytest.fixture
def dialect() -> DummyDialect:
    return DummyDialect()


class TestCollateExpression:
    """Collation expression support (standard SQL COLLATE)."""

    def test_column_collate(self, dialect):
        expr = Column(dialect, "name", table="users").collate("NOCASE")
        sql, params = expr.to_sql()
        assert sql == '"users"."name" COLLATE NOCASE'
        assert params == ()

    def test_collate_function(self, dialect):
        expr = collate(Column(dialect, "name"), "BINARY")
        sql, params = expr.to_sql()
        assert sql == '"name" COLLATE BINARY'
        assert params == ()

    def test_enum_collation_name(self, dialect):
        expr = Column(dialect, "name").collate(DummyCollation.NOCASE)
        sql, params = expr.to_sql()
        assert sql == '"name" COLLATE NOCASE'
        assert params == ()

    def test_collate_with_alias(self, dialect):
        expr = Column(dialect, "name").collate("NOCASE").as_("n")
        sql, params = expr.to_sql()
        assert sql == '"name" COLLATE NOCASE AS "n"'
        assert params == ()

    def test_collate_with_cast(self, dialect):
        expr = Column(dialect, "name").collate("NOCASE").cast("TEXT")
        sql, params = expr.to_sql()
        assert "COLLATE NOCASE" in sql
        assert params == ()

    def test_invalid_collation_name_raises(self, dialect):
        with pytest.raises(ValueError):
            Column(dialect, "name").collate("bad collation").to_sql()

    def test_collate_expression_collation_name_property(self, dialect):
        expr = Column(dialect, "name").collate(DummyCollation.BINARY)
        assert expr.collation_name == "BINARY"


class TestExtractDatePartDateTrunc:
    """Standard-SQL EXTRACT / DATE_PART / DATE_TRUNC expressions."""

    def test_extract_expression(self, dialect):
        expr = ExtractExpression(dialect, DateTimeField.YEAR, Column(dialect, "created_at"))
        sql, params = expr.to_sql()
        assert sql == 'EXTRACT(YEAR FROM "created_at")'
        assert params == ()

    def test_extract_with_string_field(self, dialect):
        expr = ExtractExpression(dialect, "dow", Column(dialect, "created_at"))
        sql, params = expr.to_sql()
        assert sql == 'EXTRACT(DOW FROM "created_at")'
        assert params == ()

    def test_date_part_expression(self, dialect):
        expr = DatePartExpression(dialect, DateTimeField.YEAR, Column(dialect, "created_at"))
        sql, params = expr.to_sql()
        assert sql == 'EXTRACT(YEAR FROM "created_at")'
        assert params == ()

    def test_date_trunc_expression(self, dialect):
        expr = DateTruncExpression(dialect, DateTimeField.DAY, Column(dialect, "created_at"))
        sql, params = expr.to_sql()
        assert sql == "DATE_TRUNC('day', \"created_at\")"
        assert params == ()

    def test_extract_factory_with_column_name(self, dialect):
        expr = extract(dialect, "year", "created_at")
        assert isinstance(expr, ExtractExpression)
        sql, params = expr.to_sql()
        assert sql == 'EXTRACT(YEAR FROM "created_at")'
        assert params == ()

    def test_extract_factory_with_expression(self, dialect):
        expr = extract(dialect, "year", Column(dialect, "created_at"))
        assert isinstance(expr, ExtractExpression)
        assert expr.source is not None


class TestIntervalAndDateTimeArithmetic:
    """Interval construction and date/time arithmetic (standard SQL)."""

    def test_interval_expression(self, dialect):
        expr = IntervalExpression(dialect, 1, IntervalUnit.DAY)
        sql, params = expr.to_sql()
        assert sql == "INTERVAL '1' DAY"
        assert params == ()

    def test_interval_expression_float_and_alias_unit(self, dialect):
        expr = IntervalExpression(dialect, 1.5, "dd")
        sql, params = expr.to_sql()
        assert sql == "INTERVAL '1.5' DAY"
        assert params == ()

    def test_interval_factory(self, dialect):
        expr = interval(dialect, 3, "hour")
        assert isinstance(expr, IntervalExpression)
        sql, params = expr.to_sql()
        assert sql == "INTERVAL '3' HOUR"
        assert params == ()

    def test_datetime_add(self, dialect):
        interval_expr = IntervalExpression(dialect, 1, IntervalUnit.DAY)
        expr = DateTimeAddExpression(dialect, Column(dialect, "created_at"), interval_expr)
        sql, params = expr.to_sql()
        assert sql == '"created_at" + INTERVAL \'1\' DAY'
        assert params == ()

    def test_datetime_subtract(self, dialect):
        interval_expr = IntervalExpression(dialect, 1, IntervalUnit.DAY)
        expr = DateTimeSubtractExpression(dialect, Column(dialect, "created_at"), interval_expr)
        sql, params = expr.to_sql()
        assert sql == '"created_at" - INTERVAL \'1\' DAY'
        assert params == ()

    def test_date_add_factory_numeric(self, dialect):
        expr = date_add(dialect, "created_at", 1, "day")
        assert isinstance(expr, DateTimeAddExpression)
        sql, params = expr.to_sql()
        assert sql == '"created_at" + INTERVAL \'1\' DAY'
        assert params == ()

    def test_date_add_factory_interval_object(self, dialect):
        interval_expr = IntervalExpression(dialect, 2, IntervalUnit.HOUR)
        expr = date_add(dialect, Column(dialect, "created_at"), interval_expr)
        assert isinstance(expr, DateTimeAddExpression)

    def test_date_sub_factory_numeric(self, dialect):
        expr = date_sub(dialect, "created_at", 1, "day")
        assert isinstance(expr, DateTimeSubtractExpression)
        sql, params = expr.to_sql()
        assert sql == '"created_at" - INTERVAL \'1\' DAY'
        assert params == ()

    def test_date_sub_factory_interval_object(self, dialect):
        interval_expr = IntervalExpression(dialect, 2, IntervalUnit.HOUR)
        expr = date_sub(dialect, Column(dialect, "created_at"), interval_expr)
        assert isinstance(expr, DateTimeSubtractExpression)

    def test_ensure_interval_unit_conflict(self, dialect):
        with pytest.raises(ValueError):
            date_add(dialect, "created_at", IntervalExpression(dialect, 1, IntervalUnit.DAY), "day")

    def test_ensure_interval_missing_unit(self, dialect):
        with pytest.raises(ValueError):
            date_add(dialect, "created_at", 1)

    def test_date_diff_factory_constructs(self, dialect):
        expr = date_diff(dialect, "day", "created_at", "updated_at")
        assert isinstance(expr, DateTimeDiffExpression)

    def test_date_diff_to_sql_unsupported(self, dialect):
        expr = DateTimeDiffExpression(
            dialect, IntervalUnit.DAY, Column(dialect, "created_at"), Column(dialect, "updated_at")
        )
        with pytest.raises(Exception) as exc_info:
            expr.to_sql()
        assert "date_diff" in str(exc_info.value)


class TestNormalizeAndValidate:
    """Normalization / validation helpers for datetime tokens."""

    def test_normalize_datetime_field_enum_passthrough(self):
        assert normalize_datetime_field(DateTimeField.YEAR) is DateTimeField.YEAR

    def test_normalize_datetime_field_alias(self):
        assert normalize_datetime_field("yyyy") is DateTimeField.YEAR
        assert normalize_datetime_field("weekday") is DateTimeField.DOW

    def test_normalize_datetime_field_value(self):
        assert normalize_datetime_field("month") is DateTimeField.MONTH

    def test_normalize_datetime_field_invalid(self):
        with pytest.raises(ValueError):
            normalize_datetime_field("bogus")

    def test_normalize_datetime_field_empty(self):
        with pytest.raises(ValueError):
            normalize_datetime_field("")

    def test_normalize_interval_unit_enum_passthrough(self):
        assert normalize_interval_unit(IntervalUnit.DAY) is IntervalUnit.DAY

    def test_normalize_interval_unit_alias(self):
        assert normalize_interval_unit("mins") is IntervalUnit.MINUTE
        assert normalize_interval_unit("dd") is IntervalUnit.DAY

    def test_normalize_interval_unit_invalid(self):
        with pytest.raises(ValueError):
            normalize_interval_unit("bogus")

    def test_normalize_interval_unit_empty(self):
        with pytest.raises(ValueError):
            normalize_interval_unit("")

    def test_validate_interval_value_int(self):
        assert validate_interval_value(5) == 5

    def test_validate_interval_value_float(self):
        assert validate_interval_value(1.5) == 1.5

    def test_validate_interval_value_bool_rejected(self):
        with pytest.raises(TypeError):
            validate_interval_value(True)

    def test_validate_interval_value_str_rejected(self):
        with pytest.raises(TypeError):
            validate_interval_value("1")

    def test_validate_interval_value_nonfinite_rejected(self):
        with pytest.raises(ValueError):
            validate_interval_value(float("nan"))

    def test_interval_expression_invalid_value(self, dialect):
        with pytest.raises(TypeError):
            IntervalExpression(dialect, True, IntervalUnit.DAY)
