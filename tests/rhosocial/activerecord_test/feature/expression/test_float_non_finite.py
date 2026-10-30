# tests/rhosocial/activerecord_test/feature/expression/test_float_non_finite.py
"""The two members of the float type JSON cannot carry, and the kinds that do.

NaN and +/-Infinity are ordinary members of a float -- IEEE 754 defines them,
Python's Decimal has them, and arithmetic produces them without asking. They are
not errors and not edge cases, so refusing to write one omits part of the type
rather than enforcing a rule.

What makes them awkward is narrower: JSON's number grammar (RFC 8259) has no
literal for them. `json.dumps` emits a bare `NaN` anyway, which its own
documentation calls non-compliant, and that went unnoticed for as long as the
only reader of a Python artifact was a Python program.

The answer is the one this vocabulary already uses for every other host type
JSON cannot represent natively -- date, time, interval, binary, decimal all
travel as text under a kind that names how to read them back. So do these. A
port reads a string under a known kind, and no parser needs a special case.
"""

import json
import math

import pytest

from rhosocial.activerecord.backend.expression import serialization as ser
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.values import LiteralKind
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

NON_FINITE = [("nan", float("nan")), ("+inf", float("inf")), ("-inf", float("-inf"))]


@pytest.fixture
def dialect():
    return DummyDialect()


@pytest.mark.parametrize("label,value", NON_FINITE)
def test_each_gets_a_kind_of_its_own(dialect, label, value):
    """The host type is the same float in all three cases; the kind differs."""
    encoded = ser.encode_artifact(Literal(dialect, value))
    expected = "nan_value" if math.isnan(value) else "infinity_value"
    assert encoded["kind"] == expected


def test_the_payloads_are_json_strings_not_bare_literals(dialect):
    """The whole point: strict JSON can parse what this port writes."""
    for _, value in NON_FINITE:
        text = json.dumps(ser.encode_artifact(Literal(dialect, value)),
                          separators=(",", ":"), ensure_ascii=False)
        assert "NaN" not in text and "Infinity" not in text
        json.loads(text)  # raises if any parser-worthy rule was broken


def test_the_infinity_sign_is_spelled_not_inferred(dialect):
    """The sign is the content of the value, so it travels."""
    assert ser.encode_artifact(Literal(dialect, float("inf")))["params"]["value"] == "+inf"
    assert ser.encode_artifact(Literal(dialect, float("-inf")))["params"]["value"] == "-inf"


def test_nan_carries_no_spellings_to_disagree_about(dialect):
    """A NaN is a NaN; giving it a payload that could say otherwise would be
    a place for two ports to differ for no reason."""
    encoded = ser.encode_artifact(Literal(dialect, float("nan")))
    assert encoded["params"]["value"] == "nan"


@pytest.mark.parametrize("label,value", NON_FINITE)
def test_every_one_round_trips(dialect, label, value):
    encoded = ser.encode_artifact(Literal(dialect, value))
    back = ser.decode_artifact(encoded, dialect).value
    if math.isnan(value):
        assert math.isnan(back)
    else:
        assert back == value
        assert math.copysign(1, back) == math.copysign(1, value), "the sign must survive"


@pytest.mark.parametrize("label,value", NON_FINITE)
def test_inline_travels_with_them_too(dialect, label, value):
    """inline is a property of the position; a new kind must carry it like the rest."""
    encoded = ser.encode_artifact(Literal(dialect, value, inline=True))
    assert encoded["params"]["inline"] is True


@pytest.mark.parametrize("label,value", NON_FINITE)
def test_it_still_binds_at_runtime(dialect, label, value):
    """The node exists so the artifact can carry the value; binding never stopped working."""
    sql, params = Literal(dialect, value).to_sql()
    assert sql == "?"
    assert params == (value,)


class TestFloatValueStaysAFiniteNumber:
    """The split has to be clean, or float_value becomes the thing it replaced."""

    def test_a_finite_float_is_still_a_json_number(self, dialect):
        encoded = ser.encode_artifact(Literal(dialect, 1.5))
        assert encoded["kind"] == "float_value"
        assert encoded["params"]["value"] == 1.5
        assert isinstance(encoded["params"]["value"], float)

    @pytest.mark.parametrize("payload", [
        '{"kind":"float_value","params":{"value":NaN,"inline":false}}',
        '{"kind":"float_value","params":{"value":Infinity,"inline":false}}',
        '{"kind":"float_value","params":{"value":-Infinity,"inline":false}}',
    ])
    def test_reading_a_non_finite_float_value_is_refused(self, dialect, payload):
        """Not because the value is invalid, but because the kind is wrong for it."""
        with pytest.raises(ValueError, match="nan_value or infinity_value"):
            ser.decode_artifact(json.loads(payload), dialect)

    @pytest.mark.parametrize("raw", ['"NaN"', '"1.5"', "true", "null", "{}", "[]"])
    def test_reading_a_non_number_is_refused(self, dialect, raw):
        """It would bind as a string and fail as a database error, naming neither
        the artifact nor the position."""
        with pytest.raises(ValueError):
            ser.decode_artifact(
                json.loads('{"kind":"float_value","params":{"value":%s,"inline":false}}' % raw),
                dialect,
            )

    @pytest.mark.parametrize("value", [1.5, -0.25, 0.0, -0.0, 3.14159, 1e300])
    def test_finite_floats_survive_the_round_trip(self, dialect, value):
        encoded = ser.encode_artifact(Literal(dialect, value))
        assert ser.decode_artifact(encoded, dialect).value == value


def test_a_non_finite_operand_in_a_predicate_travels(dialect):
    """Not only at the top level -- the values nest, so the kind has to work there."""
    tree = ComparisonPredicate(dialect, ">", Column(dialect, "score"), Literal(dialect, float("inf")))
    assert ser.encode_artifact(tree)["params"]["right"]["kind"] == "infinity_value"


def test_decimal_text_is_not_subject_to_any_of_this(dialect):
    """Decimal travels as text, which *is* JSON, so its NaN and Infinity need
    nothing new -- and the host type considers them ordinary numbers."""
    import decimal

    for value in (decimal.Decimal("NaN"), decimal.Decimal("Infinity")):
        kind = LiteralKind.of(value)
        assert kind.wire == "decimal_value"
        assert kind.pack(value) in ("NaN", "Infinity")


def test_the_kinds_are_in_the_registry(dialect):
    """A kind that is not registered cannot be resolved on the way back."""
    registry = ser.default_registry()
    for wire in ("nan_value", "infinity_value"):
        assert wire in registry.node_kinds()