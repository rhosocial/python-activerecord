# tests/rhosocial/activerecord_test/feature/backend/adapters/test_range_validation.py
"""What the neutral range classes refuse, and which endpoint type they demand.

A ``Range`` carries an ``element_type`` in its JSON form because the endpoints
cannot say it by themselves once they are stored as text: ``"1"`` is an int
endpoint in one column and a decimal one in another. The loader therefore
validates each endpoint against the declared label, and the failures are what
this file pins -- one test per label, because each has its own message.

The literal renderer is checked for the same reason: ``bool`` is an ``int``
subclass and would otherwise render as ``true`` inside a bound.
"""

import pytest

from rhosocial.activerecord.backend.adapters import Multirange, Range


def _payload(**overrides):
    payload = {"bounds": "[)", "empty": False}
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Literal rendering
# ---------------------------------------------------------------------------


def test_a_bool_endpoint_is_refused_by_name():
    with pytest.raises(ValueError, match="bool is not a supported range endpoint"):
        Range(True, 2, "[)").to_postgres_literal()


def test_a_float_endpoint_renders_with_a_decimal_point():
    assert Range(1.5, 2.5, "[)").to_postgres_literal() == "[1.5,2.5)"


def test_endpoints_that_cannot_be_compared_are_refused_at_construction():
    with pytest.raises(ValueError, match="not comparable"):
        Range([1], 2, "[)")


# ---------------------------------------------------------------------------
# The JSON loader: one label at a time
# ---------------------------------------------------------------------------


def test_an_unknown_label_is_named():
    with pytest.raises(ValueError, match="Unknown range element_type"):
        Range.from_json_value(_payload(lower=1, upper=2, element_type="bogus"))


def test_an_int_label_refuses_text():
    with pytest.raises(ValueError, match=r"element_type 'int' requires int"):
        Range.from_json_value(_payload(lower="a", upper="b", element_type="int"))


def test_a_float_label_refuses_a_bool_and_text():
    """``bool`` is an ``int`` subclass, so it needs its own refusal."""
    with pytest.raises(ValueError, match=r"element_type 'float' requires a number, got bool"):
        Range.from_json_value(_payload(lower=True, upper=2, element_type="float"))
    with pytest.raises(ValueError, match=r"element_type 'float' requires a number, got str"):
        Range.from_json_value(_payload(lower="a", upper=2, element_type="float"))


def test_a_decimal_label_refuses_a_number_and_bad_text():
    """The stored form is text, so the loader accepts text only -- a JSON number
    would have lost its precision before the loader saw it."""
    with pytest.raises(ValueError, match=r"element_type 'decimal' requires a string"):
        Range.from_json_value(_payload(lower=1, upper=2, element_type="decimal"))
    with pytest.raises(ValueError, match="Invalid Decimal range endpoint"):
        Range.from_json_value(_payload(lower="x", upper="y", element_type="decimal"))


def test_a_temporal_label_refuses_a_number_and_bad_text():
    for label in ("date", "time", "datetime"):
        with pytest.raises(ValueError, match=f"element_type '{label}' requires a string"):
            Range.from_json_value(_payload(lower=1, upper=2, element_type=label))

    with pytest.raises(ValueError, match="Invalid date range endpoint"):
        Range.from_json_value(_payload(lower="x", upper="y", element_type="date"))
    with pytest.raises(ValueError, match="Invalid time range endpoint"):
        Range.from_json_value(_payload(lower="x", upper="y", element_type="time"))


def test_a_str_label_refuses_a_number():
    with pytest.raises(ValueError, match=r"element_type 'str' requires str"):
        Range.from_json_value(_payload(lower=1, upper=2, element_type="str"))


def test_a_non_empty_range_must_declare_its_element_type():
    with pytest.raises(ValueError, match="element_type is required"):
        Range.from_json_value(_payload(lower=True, upper=False, element_type=None))


# ---------------------------------------------------------------------------
# Multirange merging
# ---------------------------------------------------------------------------


def test_an_unbounded_lower_bound_absorbs_the_next_member():
    """A range open towards -infinity overlaps everything to its upper bound,
    so the merge keeps it and widens the upper edge."""
    merged = Multirange([Range(None, 2, "(]"), Range(1, 2, "[)")])

    assert len(merged.ranges) == 1
    assert merged.ranges[0].lower is None
    assert merged.ranges[0].upper == 2
