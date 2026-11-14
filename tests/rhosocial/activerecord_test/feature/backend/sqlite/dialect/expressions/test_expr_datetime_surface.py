# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/expressions/test_expr_datetime_surface.py
"""SQLite datetime rendering: extraction, truncation and collation gates."""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.collation import CollateFunction
from rhosocial.activerecord.backend.expression.datetime import (
    DateTruncExpression,
    ExtractExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

DIALECT = SQLiteDialect(version=(3, 53, 0))
SOURCE = Literal(DIALECT, "2026-11-13 10:20:30")


def test_every_declared_field_has_an_extract_spelling():
    for field in ("year", "month", "week", "day", "hour", "minute", "second", "dow", "doy"):
        sql, params = ExtractExpression(DIALECT, field, SOURCE).to_sql()
        assert sql.startswith("CAST(strftime(")
        assert params == ("2026-11-13 10:20:30",)


def test_extract_refuses_a_field_outside_its_table():
    """A field can arrive on a node whose value bypassed the constructor.

    ``ExtractExpression`` normalises its field at construction, so this is the
    guard's own surface: any token the dialect has no ``strftime`` format for
    is refused instead of rendered as an empty format.
    """
    from types import SimpleNamespace

    expr = SimpleNamespace(
        field=SimpleNamespace(value="epoch"),
        source=SOURCE,
        alias=None,
    )
    with pytest.raises(UnsupportedFeatureError, match="EXTRACT"):
        DIALECT.format_extract_expression(expr)


@pytest.mark.parametrize("field", ["year", "month", "day"])
def test_date_trunc_to_a_calendar_unit_uses_datetime_modifier(field):
    sql, params = DateTruncExpression(DIALECT, field, SOURCE).to_sql()
    assert sql.startswith("datetime(")
    assert f"'start of {field}'" in sql
    assert params == ("2026-11-13 10:20:30",)


@pytest.mark.parametrize("field", ["hour", "minute", "second"])
def test_date_trunc_to_a_clock_unit_uses_strftime(field):
    sql, params = DateTruncExpression(DIALECT, field, SOURCE).to_sql()
    assert sql.startswith("strftime(")
    assert params == ("2026-11-13 10:20:30",)


def test_date_trunc_refuses_units_it_cannot_spell():
    with pytest.raises(UnsupportedFeatureError, match="DATE_TRUNC"):
        DateTruncExpression(DIALECT, "week", SOURCE).to_sql()


def test_collate_expression_renders_a_bare_name():
    assert DIALECT.supports_collate_expression() is True
    sql, params = CollateFunction(DIALECT, Column(DIALECT, "name"), "NOCASE").to_sql()
    assert sql == '"name" COLLATE NOCASE'
    assert params == ()


def test_schema_qualified_collation_is_refused():
    with pytest.raises(UnsupportedFeatureError, match="COLLATE"):
        CollateFunction(DIALECT, Column(DIALECT, "name"), "NOCASE", schema="main").to_sql()


def test_collation_name_must_be_an_identifier():
    with pytest.raises(ValueError, match="Unsupported SQLite collation"):
        CollateFunction(DIALECT, Column(DIALECT, "name"), "NOCASE); DROP TABLE users; --").to_sql()
