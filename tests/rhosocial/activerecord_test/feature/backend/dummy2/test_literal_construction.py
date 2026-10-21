# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_literal_construction.py
"""Tests for the three-level inline literal construction (spec §4.4).

Levels:
1. Dialect base class built-ins: NULL / boolean / numeric / string / datetime
2. Backend overrides: bytes / UUID / Interval — the base does NOT guess them
   and leaves the failure explicit
3. The literal-construction protocol: a value type renders its own complete
   inline literal through the dialect's public escape helpers

Dispatch order is built-in whitelist → protocol → explicit failure, and there
is no ``str()`` fallback.
"""

import datetime as dt
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.expression import Literal


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


class TestLevel1Builtins:
    def test_null(self):
        assert _dummy_dialect().format_literal(None) == "NULL"

    def test_boolean_renders_before_numeric(self):
        """bool is an int subclass: the keyword dispatch must run first."""
        assert _dummy_dialect().format_literal(True) == "TRUE"
        assert _dummy_dialect().format_literal(False) == "FALSE"

    def test_integers_and_decimal(self):
        d = _dummy_dialect()
        assert d.format_literal(42) == "42"
        assert d.format_literal(Decimal("1.50")) == "1.50"

    def test_float(self):
        assert _dummy_dialect().format_literal(1.5) == "1.5"

    def test_nan_is_refused(self):
        with pytest.raises(ValueError, match="NaN"):
            _dummy_dialect().format_literal(float("nan"))

    def test_infinity_is_refused(self):
        """float('inf') stringifies as 'inf' and would degrade to an identifier."""
        with pytest.raises(ValueError, match="Inf"):
            _dummy_dialect().format_literal(float("inf"))
        with pytest.raises(ValueError, match="Inf"):
            _dummy_dialect().format_literal(float("-inf"))

    def test_non_finite_decimal_is_refused(self):
        with pytest.raises(ValueError, match="non-finite"):
            _dummy_dialect().format_literal(Decimal("NaN"))

    def test_string_is_quoted_and_escaped(self):
        assert _dummy_dialect().format_literal("it's") == "'it''s'"

    def test_datetime_and_date_are_iso_strings(self):
        d = _dummy_dialect()
        assert d.format_literal(dt.datetime(2026, 1, 2, 3, 4, 5)) == "'2026-01-02 03:04:05'"
        assert d.format_literal(dt.date(2026, 1, 2)) == "'2026-01-02'"


class TestLevel2BackendDuty:
    def test_bytes_are_not_guessed_by_the_base(self):
        """The base class leaves backend-specific forms to the backend."""
        with pytest.raises(TypeError, match="no inline SQL literal form"):
            _dummy_dialect().format_literal(b"\x00\x01")


class _Point:
    """A user-defined value type implementing the construction protocol."""

    def __init__(self, x: float, y: float):
        self.x, self.y = x, y

    def __sql_literal__(self, dialect) -> str:
        inner = f"POINT({self.x} {self.y})"
        return f"'{dialect.escape_sql_string(inner)}'"


class _Broken:
    def __sql_literal__(self, dialect) -> int:
        return 7


class _Empty:
    def __sql_literal__(self, dialect) -> str:
        return ""


class TestLevel3Protocol:
    def test_protocol_value_renders_its_own_text(self):
        assert _dummy_dialect().format_literal(_Point(1.0, 2.0)) == "'POINT(1.0 2.0)'"

    def test_protocol_string_components_use_the_public_escape_helper(self):
        escaped = _dummy_dialect().escape_sql_string("it's")
        assert escaped == "it''s"
        point = _Point(1.0, 2.0)
        text = point.__sql_literal__(_dummy_dialect())
        assert text.startswith("'") and text.endswith("'")

    def test_protocol_is_dispatched_only_after_the_whitelist(self):
        """A str subclass hits the built-in whitelist first."""
        class _MyStr(str):
            def __sql_literal__(self, dialect):  # pragma: no cover
                return "SHOULD_NOT_RENDER"

        assert _dummy_dialect().format_literal(_MyStr("plain")) == "'plain'"

    def test_protocol_returning_a_non_string_is_refused(self):
        with pytest.raises(TypeError, match="literal-construction"):
            _dummy_dialect().format_literal(_Broken())

    def test_protocol_returning_an_empty_string_is_refused(self):
        with pytest.raises(TypeError, match="literal-construction"):
            _dummy_dialect().format_literal(_Empty())

    def test_no_str_fallback_for_plain_objects(self):
        class _Plain:
            pass

        with pytest.raises(TypeError, match="no inline SQL literal form"):
            _dummy_dialect().format_literal(_Plain())


class TestProtocolThroughInlineRendering:
    def test_ddl_literal_renders_a_protocol_value_inline(self):
        lit = Literal(_dummy_dialect(), _Point(1.0, 2.0), inline=True)
        assert lit.to_sql() == ("'POINT(1.0 2.0)'", ())
