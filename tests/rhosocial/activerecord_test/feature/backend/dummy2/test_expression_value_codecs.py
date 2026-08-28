# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_value_codecs.py
"""
JSON value codec round-trip tests.

The goal is "expression <-> JSON string" via the standard library ``json``.
Non-JSON-native Python values (datetime/date/time/Decimal/bytes/UUID/set/
Enum/...) go through the ``register_codec`` codecs using json.dumps(default=)
and json.loads(object_hook=).
"""

import datetime as dt
import fractions
import json
from decimal import Decimal
from enum import Enum
from uuid import uuid4

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.serialization import (
    deserialize,
    deserialize_json,
    deserialize_xml,
    register_codec,
    serialize,
    serialize_json,
    serialize_xml,
)


class Status(Enum):
    A = 1
    B = 2


NON_NATIVE_VALUES = [
    dt.datetime(2026, 1, 1, 10, 30),
    dt.date(2026, 1, 1),
    dt.time(10, 30, 15),
    Decimal("3.5"),
    b"\x00\x01\x02",
    bytearray(b"\x01\x02"),
    uuid4(),
    {1, 2, 3},
    frozenset([4, 5]),
    Status.B,
]


class TestLiteralValueCodecRoundtrip:
    """Literal values of non-JSON-native types survive serialize_json """

    @pytest.mark.parametrize("value", NON_NATIVE_VALUES, ids=lambda v: type(v).__name__)
    def test_json_roundtrip(self, dummy_dialect, value):
        lit = Literal(dummy_dialect, value)
        spec = serialize_json(lit)
        json.loads(spec)  # must be valid JSON string
        restored = deserialize_json(spec, dummy_dialect)
        assert type(restored.value) is type(value)
        assert restored.value == value

    @pytest.mark.parametrize("value", NON_NATIVE_VALUES, ids=lambda v: type(v).__name__)
    def test_dict_roundtrip(self, dummy_dialect, value):
        lit = Literal(dummy_dialect, value)
        restored = deserialize(serialize(lit), dummy_dialect)
        assert type(restored.value) is type(value)
        assert restored.value == value

    def test_json_nested_expression(self, dummy_dialect):
        expr = Column(dummy_dialect, "t") > dt.datetime(2026, 1, 1)
        restored = deserialize_json(serialize_json(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_json_combined_with_cast_chain(self, dummy_dialect):
        expr = Column(dummy_dialect, "amount").cast("numeric")
        restored = deserialize_json(serialize_json(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_json_container_values(self, dummy_dialect):
        lit = Literal(dummy_dialect, [dt.date(2026, 1, 1), Decimal("1.5"), "x"])
        restored = deserialize_json(serialize_json(lit), dummy_dialect)
        assert restored.value == [dt.date(2026, 1, 1), Decimal("1.5"), "x"]
        assert isinstance(restored.value[0], dt.date)


class TestXmlCodecRoundtrip:
    """Expression <-> XML document round-trips for the same spec layer."""

    @pytest.mark.parametrize("value", NON_NATIVE_VALUES, ids=lambda v: type(v).__name__)
    def test_xml_roundtrip(self, dummy_dialect, value):
        lit = Literal(dummy_dialect, value)
        spec = serialize_xml(lit)
        restored = deserialize_xml(spec, dummy_dialect)
        assert type(restored.value) is type(value)
        assert restored.value == value

    def test_xml_scalars(self, dummy_dialect):
        for value in [42, "hello", True, 3.14, None]:
            restored = deserialize_xml(serialize_xml(Literal(dummy_dialect, value)), dummy_dialect)
            assert restored.value == value
            assert type(restored.value) is type(value)

    def test_xml_string_whitespace_preserved(self, dummy_dialect):
        """XML round-trip must not strip leading/trailing whitespace in strings."""
        for value in [" .+*#", "hello world  ", "  x", "a b", "", "   "]:
            restored = deserialize_xml(serialize_xml(Literal(dummy_dialect, value)), dummy_dialect)
            assert restored.value == value, f"{value!r} -> {restored.value!r}"

    def test_xml_tuple_preserved(self, dummy_dialect):
        lit = Literal(dummy_dialect, (1, "a", 2.0))
        restored = deserialize_xml(serialize_xml(lit), dummy_dialect)
        assert isinstance(restored.value, tuple)
        assert restored.value == (1, "a", 2.0)

    def test_xml_nested_expression(self, dummy_dialect):
        expr = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "t"),
                                   Literal(dummy_dialect, dt.date(2026, 1, 1)))
        restored = deserialize_xml(serialize_xml(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_xml_cast_chain(self, dummy_dialect):
        expr = Column(dummy_dialect, "amount").cast("numeric")
        restored = deserialize_xml(serialize_xml(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_xml_dict_and_list_values(self, dummy_dialect):
        lit = Literal(dummy_dialect, [1, {"k": "v"}])
        restored = deserialize_xml(serialize_xml(lit), dummy_dialect)
        assert restored.value == [1, {"k": "v"}]


class TestCustomCodecRegistration:
    """register_codec extends serialization for developer-defined types."""

    def test_custom_fraction(self, dummy_dialect):
        register_codec(
            "fract",
            fractions.Fraction,
            encode=lambda v: f"{v.numerator}/{v.denominator}",
            decode=lambda p: fractions.Fraction(*map(int, p.split("/"))),
        )
        lit = Literal(dummy_dialect, fractions.Fraction(3, 4))
        restored = deserialize_json(serialize_json(lit), dummy_dialect)
        assert restored.value == fractions.Fraction(3, 4)

    def test_custom_codec_non_str_scalar_payload(self, dummy_dialect):
        """A codec whose payload is a non-str scalar (int) round-trips through
        dict / JSON / XML; the XML layer tags scalar payloads by type."""
        from rhosocial.activerecord.backend.expression.codec import _CODECS

        class Intish(int):
            pass

        register_codec("_intish", Intish, encode=int, decode=Intish)
        try:
            lit = Literal(dummy_dialect, Intish(21))
            assert deserialize(serialize(lit), dummy_dialect).value == Intish(21)
            assert deserialize_json(serialize_json(lit), dummy_dialect).value == Intish(21)
            assert deserialize_xml(serialize_xml(lit), dummy_dialect).value == Intish(21)
        finally:
            _CODECS.pop("_intish", None)

    def test_duplicate_tag_rejected(self):
        from rhosocial.activerecord.backend.expression.codec import _CODECS

        register_codec("_dup_check", str, encode=str, decode=str)
        try:
            with pytest.raises(ValueError, match="already registered"):
                register_codec("_dup_check", str, encode=str, decode=str)
        finally:
            _CODECS.pop("_dup_check", None)

    def test_catch_all_codec_lowest_priority(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.codec import decode_value, encode_value, _CODECS

        # py_type=None registers a catch-all used during decode only.
        register_codec(
            "_catch_all",
            None,
            encode=lambda v: {"marked": True},
            decode=lambda p: p["marked"],
        )
        try:
            # A known type must win over the catch-all during encode.
            assert encode_value(dt.datetime(2026, 1, 1))["__value__"][0] == "dt"
            # py_type=None table entry is skipped during encode (line 85).
            assert encode_value(slice(1, 2)) is None
            # During decode the catch-all handles unknown tags.
            assert decode_value({"__value__": ["_catch_all", {"marked": True}]}) is True
        finally:
            _CODECS.pop("_catch_all", None)

    def test_decode_unknown_tag_passthrough(self):
        from rhosocial.activerecord.backend.expression.codec import decode_value

        # Unknown __value__ tag must fall through untouched (not crash).
        result = decode_value({"__value__": ["no_such_tag", "x"]})
        assert result == {"__value__": ["no_such_tag", "x"]}