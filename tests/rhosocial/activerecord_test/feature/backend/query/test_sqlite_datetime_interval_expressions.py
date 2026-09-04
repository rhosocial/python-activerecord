# tests/rhosocial/activerecord_test/feature/backend/query/test_sqlite_datetime_interval_expressions.py
"""Tests for SQLite datetime interval expressions."""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal, QueryExpression
from rhosocial.activerecord.backend.expression.datetime import (
    DateTimeField,
    IntervalUnit,
    normalize_datetime_field,
    normalize_interval_unit,
)
from rhosocial.activerecord.backend.expression.functions import (
    date_add,
    date_diff,
    date_part,
    date_sub,
    date_trunc,
    extract,
    interval,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteDateTimeIntervalExpressions:
    @pytest.mark.parametrize(
        "field,fmt",
        [
            ("year", "%Y"),
            ("month", "%m"),
            ("day", "%d"),
            ("hour", "%H"),
            ("minute", "%M"),
            ("second", "%S"),
        ],
    )
    def test_extract_datetime_fields(self, sqlite_dialect_3_8_0: SQLiteDialect, field: str, fmt: str):
        expr = extract(sqlite_dialect_3_8_0, field, Column(sqlite_dialect_3_8_0, "created_at"))

        sql, params = expr.to_sql()

        assert sql == f"CAST(strftime('{fmt}', \"created_at\") AS INTEGER)"
        assert params == ()

    def test_extract_literal_source_params(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = extract(sqlite_dialect_3_8_0, "month", Literal(sqlite_dialect_3_8_0, "2026-06-04"))

        sql, params = expr.to_sql()

        assert sql == "CAST(strftime('%m', ?) AS INTEGER)"
        assert params == ("2026-06-04",)

    def test_date_part_uses_extract_mapping(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = date_part(sqlite_dialect_3_8_0, "day", Column(sqlite_dialect_3_8_0, "created_at"))

        sql, params = expr.to_sql()

        assert sql == "CAST(strftime('%d', \"created_at\") AS INTEGER)"
        assert params == ()

    @pytest.mark.parametrize(
        "field,expected",
        [
            ("year", "datetime(\"created_at\", 'start of year')"),
            ("month", "datetime(\"created_at\", 'start of month')"),
            ("day", "datetime(\"created_at\", 'start of day')"),
            ("hour", "strftime('%Y-%m-%d %H:00:00', \"created_at\")"),
            ("minute", "strftime('%Y-%m-%d %H:%M:00', \"created_at\")"),
            ("second", "strftime('%Y-%m-%d %H:%M:%S', \"created_at\")"),
        ],
    )
    def test_date_trunc_datetime_fields(self, sqlite_dialect_3_8_0: SQLiteDialect, field: str, expected: str):
        expr = date_trunc(sqlite_dialect_3_8_0, field, Column(sqlite_dialect_3_8_0, "created_at"))

        sql, params = expr.to_sql()

        assert sql == expected
        assert params == ()

    def test_standalone_interval_is_unsupported(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = interval(sqlite_dialect_3_8_0, 1, "day")

        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_date_add_column_source(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = date_add(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "created_at"), 1, "day")

        sql, params = expr.to_sql()

        assert sql == 'datetime("created_at", ?)'
        assert params == ("+1 day",)

    def test_date_sub_interval_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = date_sub(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "created_at"),
            interval(sqlite_dialect_3_8_0, 2, "hour"),
        )

        sql, params = expr.to_sql()

        assert sql == 'datetime("created_at", ?)'
        assert params == ("-2 hour",)

    def test_date_add_literal_source_params_order(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = date_add(
            sqlite_dialect_3_8_0,
            Literal(sqlite_dialect_3_8_0, "2026-06-04 10:00:00"),
            30,
            "minute",
        )

        sql, params = expr.to_sql()

        assert sql == "datetime(?, ?)"
        assert params == ("2026-06-04 10:00:00", "+30 minute")

    def test_date_add_week_converts_to_days(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = date_add(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "created_at"), 2, "week")

        sql, params = expr.to_sql()

        assert sql == 'datetime("created_at", ?)'
        assert params == ("+14 day",)

    @pytest.mark.parametrize(
        "unit,expected",
        [
            ("day", '(julianday("ended_at") - julianday("started_at"))'),
            ("hour", '((julianday("ended_at") - julianday("started_at")) * 24)'),
            ("minute", '((julianday("ended_at") - julianday("started_at")) * 1440)'),
            ("second", '((julianday("ended_at") - julianday("started_at")) * 86400)'),
        ],
    )
    def test_date_diff_supported_units(self, sqlite_dialect_3_8_0: SQLiteDialect, unit: str, expected: str):
        expr = date_diff(
            sqlite_dialect_3_8_0,
            unit,
            Column(sqlite_dialect_3_8_0, "started_at"),
            Column(sqlite_dialect_3_8_0, "ended_at"),
        )

        sql, params = expr.to_sql()

        assert sql == expected
        assert params == ()

    @pytest.mark.parametrize("unit", ["month", "year"])
    def test_date_diff_calendar_units_are_unsupported(self, sqlite_dialect_3_8_0: SQLiteDialect, unit: str):
        expr = date_diff(
            sqlite_dialect_3_8_0,
            unit,
            Column(sqlite_dialect_3_8_0, "started_at"),
            Column(sqlite_dialect_3_8_0, "ended_at"),
        )

        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    @pytest.mark.parametrize(
        "field,expected",
        [
            (DateTimeField.YEAR, DateTimeField.YEAR),
            (" years ", DateTimeField.YEAR),
            ("yyyy", DateTimeField.YEAR),
            ("weekday", DateTimeField.DOW),
        ],
    )
    def test_normalize_datetime_field_aliases(self, field, expected):
        assert normalize_datetime_field(field) is expected

    @pytest.mark.parametrize("field", ["", "   ", "quarter"])
    def test_invalid_datetime_field_fails_during_construction(self, sqlite_dialect_3_8_0: SQLiteDialect, field: str):
        with pytest.raises(ValueError):
            extract(
                sqlite_dialect_3_8_0,
                field,
                Column(sqlite_dialect_3_8_0, "created_at"),
            )

    @pytest.mark.parametrize(
        "unit,expected",
        [
            (IntervalUnit.WEEK, IntervalUnit.WEEK),
            (" weeks ", IntervalUnit.WEEK),
            ("mins", IntervalUnit.MINUTE),
        ],
    )
    def test_normalize_interval_unit_aliases(self, unit, expected):
        assert normalize_interval_unit(unit) is expected

    @pytest.mark.parametrize("unit", ["", "   ", "quarter"])
    def test_invalid_interval_unit_fails_during_construction(self, sqlite_dialect_3_8_0: SQLiteDialect, unit: str):
        with pytest.raises(ValueError):
            interval(sqlite_dialect_3_8_0, 1, unit)

    @pytest.mark.parametrize("value", [True, "1"])
    def test_invalid_interval_value_type_fails(self, sqlite_dialect_3_8_0: SQLiteDialect, value):
        with pytest.raises(TypeError):
            interval(sqlite_dialect_3_8_0, value, "day")

    @pytest.mark.parametrize("value", [float("nan"), float("inf")])
    def test_invalid_interval_value_must_be_finite(self, sqlite_dialect_3_8_0: SQLiteDialect, value: float):
        with pytest.raises(ValueError):
            interval(sqlite_dialect_3_8_0, value, "day")

    def test_interval_expression_rejects_extra_unit(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = interval(sqlite_dialect_3_8_0, 1, "day")

        with pytest.raises(ValueError):
            date_add(
                sqlite_dialect_3_8_0,
                Column(sqlite_dialect_3_8_0, "created_at"),
                expr,
                "day",
            )

    def test_numeric_interval_requires_unit(self, sqlite_dialect_3_8_0: SQLiteDialect):
        with pytest.raises(ValueError):
            date_sub(
                sqlite_dialect_3_8_0,
                Column(sqlite_dialect_3_8_0, "created_at"),
                1,
            )

    def test_alias_and_cast(self, sqlite_dialect_3_8_0: SQLiteDialect):
        expr = (
            extract(sqlite_dialect_3_8_0, "year", Column(sqlite_dialect_3_8_0, "created_at"))
            .cast("TEXT")
            .as_("created_year")
        )

        sql, params = expr.to_sql()

        expected = 'CAST(CAST(strftime(\'%Y\', "created_at") AS INTEGER) AS TEXT) AS "created_year"'
        assert sql == expected
        assert params == ()

    def test_query_expression_integration(self, sqlite_dialect_3_8_0: SQLiteDialect):
        shifted = date_add(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "created_at"),
            1,
            "day",
        )
        query = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[
                extract(
                    sqlite_dialect_3_8_0,
                    "year",
                    Column(sqlite_dialect_3_8_0, "created_at"),
                )
            ],
            from_="events",
            where=shifted > Literal(sqlite_dialect_3_8_0, "2026-01-01"),
        )

        sql, params = query.to_sql()

        assert "CAST(strftime('%Y', \"created_at\") AS INTEGER)" in sql
        assert 'datetime("created_at", ?) > ?' in sql
        assert params == ("+1 day", "2026-01-01")
