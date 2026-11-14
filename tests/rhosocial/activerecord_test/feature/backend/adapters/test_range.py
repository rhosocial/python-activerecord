# tests/rhosocial/activerecord_test/feature/backend/adapters/test_range.py
"""DB-free tests for the neutral Range/Multirange types and adapter base."""

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Type, Union

import pytest

from rhosocial.activerecord.backend.adapters.json_codec import AdapterJSONCodec
from rhosocial.activerecord.backend.adapters.range import (
    Multirange,
    Range,
    RangeAdapterBase,
)
from rhosocial.activerecord.backend.errors import TypeConversionError

# ---------------------------------------------------------------------------
# Construction and validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bounds", ["", "[", "]", "(,)", "[]]", 1, None])
def test_invalid_bounds_rejected(bounds):
    with pytest.raises(ValueError):
        Range(1, 10, bounds=bounds)


def test_empty_range_requires_absent_endpoints():
    assert Range(empty=True) == Range(empty=True, bounds="[)")

    with pytest.raises(ValueError):
        Range(lower=1, empty=True)
    with pytest.raises(ValueError):
        Range(upper=10, empty=True)
    with pytest.raises(ValueError):
        Range(lower=1, upper=10, empty=True)


def test_lower_must_not_exceed_upper():
    with pytest.raises(ValueError):
        Range(10, 1)

    # A single-point range is valid when both sides include the value.
    single = Range(1, 1, bounds="[]")
    assert single.contains(1)


def test_incomparable_bounds_rejected():
    with pytest.raises(ValueError):
        Range(1, date(2024, 1, 1))
    with pytest.raises(ValueError):
        Range(date(2024, 1, 1), 1)


def test_range_is_hashable():
    first = Range(1, 10, bounds="[)")
    second = Range(1, 10, bounds="[)")
    assert first == second
    assert hash(first) == hash(second)


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


def test_contains_respects_exclusive_lower():
    value = Range(1, 10, bounds="[)")
    assert value.contains(1) is True
    assert value.contains(0) is False
    assert value.contains(5) is True
    assert value.contains(10) is False


def test_contains_respects_inclusive_upper():
    value = Range(1, 10, bounds="(]")
    assert value.contains(1) is False
    assert value.contains(10) is True
    assert value.contains(10.5) is False


def test_contains_both_exclusive():
    value = Range(1, 10, bounds="()")
    assert value.contains(1) is False
    assert value.contains(10) is False
    assert value.contains(5) is True


def test_contains_unbounded_directions():
    upper_bounded = Range(upper=5, bounds="(]")
    assert upper_bounded.contains(5) is True
    assert upper_bounded.contains(6) is False

    lower_bounded = Range(lower=5)
    assert lower_bounded.contains(5) is True
    assert lower_bounded.contains(4) is False

    fully_unbounded = Range()
    assert fully_unbounded.contains(object()) is True


def test_empty_range_contains_nothing():
    assert Range(empty=True).contains(1) is False
    assert Range(empty=True).contains(object()) is False


def test_contains_incomparable_value_raises():
    with pytest.raises(ValueError):
        Range(1, 10).contains("not-a-number")


# ---------------------------------------------------------------------------
# PostgreSQL literal rendering
# ---------------------------------------------------------------------------


def test_postgres_literal_basic():
    assert Range(1, 10).to_postgres_literal() == "[1,10)"
    assert Range(1, 10, bounds="[]").to_postgres_literal() == "[1,10]"
    assert Range(1, 10, bounds="()").to_postgres_literal() == "(1,10)"


def test_postgres_literal_empty():
    assert Range(empty=True).to_postgres_literal() == "empty"


def test_postgres_literal_unbounded():
    assert Range(upper=5, bounds="(]").to_postgres_literal() == "(,5]"
    assert Range(lower=1).to_postgres_literal() == "[1,)"
    assert Range().to_postgres_literal() == "(,)"


def test_postgres_literal_quotes_text_and_temporal_endpoints():
    # PostgreSQL range bounds use double quotes; a single quote is part of the
    # bound value to the range input parser.
    assert Range("a", "c").to_postgres_literal() == '["a","c")'
    assert Range("O'Reilly", "z").to_postgres_literal() == '["O\'Reilly","z")'


def test_postgres_literal_escapes_quotes_and_backslashes_in_bounds():
    assert Range('a"b', "c").to_postgres_literal() == '["a\\"b","c")'
    assert Range("a\\b", "c").to_postgres_literal() == '["a\\\\b","c")'
    assert Range("a b", "c d").to_postgres_literal() == '["a b","c d")'


def test_postgres_literal_quotes_temporal_endpoints():
    start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)
    literal = Range(start, end).to_postgres_literal()
    assert literal == '["2024-01-01T12:00:00+00:00","2024-01-02T12:00:00+00:00")'

    dates = Range(date(2024, 1, 1), date(2024, 12, 31)).to_postgres_literal()
    assert dates == '["2024-01-01","2024-12-31")'

    times = Range(time(9, 0), time(17, 30)).to_postgres_literal()
    assert times == '["09:00:00","17:30:00")'


def test_postgres_multirange_literal():
    assert Multirange((Range(1, 2), Range(3, 4))).to_postgres_literal() == "{[1,2),[3,4)}"
    assert Multirange().to_postgres_literal() == "{}"


# ---------------------------------------------------------------------------
# JSON round-trips
# ---------------------------------------------------------------------------


def test_json_roundtrip_int():
    value = Range(1, 10)
    payload = value.to_json_value()
    assert payload == {
        "lower": 1,
        "upper": 10,
        "bounds": "[)",
        "empty": False,
        "element_type": "int",
    }
    assert Range.from_json_value(payload) == value


def test_json_roundtrip_datetime():
    lower = datetime(2024, 1, 1, 8, 30, tzinfo=timezone.utc)
    upper = datetime(2024, 1, 2, 18, 0, tzinfo=timezone.utc)
    value = Range(lower, upper)

    payload = value.to_json_value()
    assert payload["element_type"] == "datetime"
    assert payload["lower"] == "2024-01-01T08:30:00+00:00"
    assert payload["upper"] == "2024-01-02T18:00:00+00:00"

    restored = Range.from_json_value(payload)
    assert restored == value
    assert isinstance(restored.lower, datetime)
    assert restored.lower.utcoffset() == timezone.utc.utcoffset(None)


def test_json_roundtrip_decimal():
    value = Range(Decimal("1.50"), Decimal("2.50"))
    payload = value.to_json_value()
    assert payload["element_type"] == "decimal"
    assert payload["lower"] == "1.50"
    assert payload["upper"] == "2.50"

    restored = Range.from_json_value(payload)
    assert restored == value
    assert isinstance(restored.lower, Decimal)


def test_json_roundtrip_date_and_time():
    date_range = Range(date(2024, 1, 1), date(2024, 12, 31))
    payload = date_range.to_json_value()
    assert payload["element_type"] == "date"
    assert payload["lower"] == "2024-01-01"
    assert Range.from_json_value(payload) == date_range

    time_range = Range(time(9, 0), time(17, 0))
    payload = time_range.to_json_value()
    assert payload["element_type"] == "time"
    assert payload["lower"] == "09:00:00"
    assert Range.from_json_value(payload) == time_range


def test_json_roundtrip_text_and_unbounded():
    value = Range("a", "c")
    payload = value.to_json_value()
    assert payload["element_type"] == "str"
    assert Range.from_json_value(payload) == value

    one_sided = Range(lower=1)
    payload = one_sided.to_json_value()
    assert payload["upper"] is None
    assert payload["element_type"] == "int"
    assert Range.from_json_value(payload) == one_sided


def test_json_roundtrip_empty():
    value = Range(empty=True, bounds="(]")
    payload = value.to_json_value()
    assert payload == {
        "lower": None,
        "upper": None,
        "bounds": "(]",
        "empty": True,
        "element_type": None,
    }
    assert Range.from_json_value(payload) == value


def test_json_requires_element_type_without_endpoints():
    with pytest.raises(ValueError):
        Range().to_json_value()


def test_json_type_tags_declared():
    assert Range.json_type_tag == "range"
    assert Multirange.json_type_tag == "multirange"


def test_tagged_codec_roundtrip_range():
    codec = AdapterJSONCodec(tagged=True)
    value = Range(1, 10)

    payload = json.loads(codec.dumps(value))
    assert payload["__type__"] == "range"
    assert payload["element_type"] == "int"

    restored = codec.loads(codec.dumps(value))
    assert isinstance(restored, Range)
    assert restored == value


def test_tagged_codec_roundtrip_datetime_multirange():
    codec = AdapterJSONCodec(tagged=True)
    value = Multirange(
        (
            Range(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 31, tzinfo=timezone.utc),
            ),
            Range(
                datetime(2024, 3, 1, tzinfo=timezone.utc),
                datetime(2024, 3, 31, tzinfo=timezone.utc),
            ),
        )
    )

    payload = json.loads(codec.dumps(value))
    assert payload["__type__"] == "multirange"
    assert payload["value"][0]["element_type"] == "datetime"

    restored = codec.loads(codec.dumps(value))
    assert isinstance(restored, Multirange)
    assert restored == value
    assert all(isinstance(item.lower, datetime) for item in restored.ranges)


@pytest.mark.parametrize(
    "payload",
    [
        {"lower": 1, "upper": 10, "bounds": "[)", "empty": False},
        {
            "lower": 1,
            "upper": 10,
            "bounds": "[)",
            "empty": False,
            "element_type": "uuid",
        },
        {
            "lower": "1",
            "upper": 10,
            "bounds": "[)",
            "empty": False,
            "element_type": "int",
        },
        {"lower": 1, "upper": 10, "bounds": "[)", "empty": "no", "element_type": "int"},
        {"lower": 1, "upper": 10, "bounds": "wat", "empty": False, "element_type": "int"},
        "not-a-mapping",
    ],
)
def test_json_decode_rejects_malformed_values(payload):
    with pytest.raises(ValueError):
        Range.from_json_value(payload)


# ---------------------------------------------------------------------------
# Multirange normalization
# ---------------------------------------------------------------------------


def test_multirange_sorts_members():
    value = Multirange((Range(5, 6), Range(1, 2), Range(3, 4)))
    assert value.ranges == (Range(1, 2), Range(3, 4), Range(5, 6))


def test_multirange_merges_overlapping_members():
    value = Multirange((Range(1, 5), Range(3, 8)))
    assert value.ranges == (Range(1, 8),)


def test_multirange_merges_touching_members():
    value = Multirange((Range(1, 5, bounds="[)"), Range(5, 8, bounds="[)")))
    assert value.ranges == (Range(1, 8, bounds="[)"),)


def test_multirange_keeps_gap_when_both_sides_exclude_the_endpoint():
    value = Multirange((Range(1, 5, bounds="[)"), Range(5, 8, bounds="(]")))
    assert value.ranges == (
        Range(1, 5, bounds="[)"),
        Range(5, 8, bounds="(]"),
    )


def test_multirange_merges_nested_member():
    value = Multirange((Range(1, 10), Range(2, 5)))
    assert value.ranges == (Range(1, 10),)


def test_multirange_drops_empty_members():
    value = Multirange((Range(empty=True), Range(1, 2)))
    assert value.ranges == (Range(1, 2),)


def test_multirange_deduplicates_identical_members():
    value = Multirange((Range(1, 2), Range(1, 2)))
    assert value.ranges == (Range(1, 2),)


def test_multirange_merges_unbounded_members():
    value = Multirange((Range(upper=5, bounds="(]"), Range(lower=5)))
    assert value.ranges == (Range(None, None, bounds="()"),)


def test_multirange_takes_wider_bounds_on_merge():
    value = Multirange((Range(1, 5, bounds="[)"), Range(5, 10, bounds="[]")))
    assert value.ranges == (Range(1, 10, bounds="[]"),)

    value = Multirange((Range(1, 5, bounds="(]"), Range(5, 10, bounds="(]")))
    assert value.ranges == (Range(1, 10, bounds="(]"),)


def test_multirange_accepts_lists_and_canonicalizes_equality():
    from_list = Multirange([Range(3, 4), Range(1, 2)])
    from_tuple = Multirange((Range(3, 4), Range(1, 2)))
    assert from_list == from_tuple
    assert hash(from_list) == hash(from_tuple)


def test_multirange_rejects_incomparable_bounds():
    with pytest.raises(ValueError):
        Multirange((Range(1, 2), Range(date(2024, 1, 1), date(2024, 2, 1))))


def test_multirange_rejects_non_range_members():
    with pytest.raises(TypeError):
        Multirange((Range(1, 2), "nope"))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Multirange(42)  # type: ignore[arg-type]


def test_multirange_json_roundtrip():
    value = Multirange((Range(1, 2), Range(3, 4)))
    payload = value.to_json_value()
    assert payload == [Range(1, 2).to_json_value(), Range(3, 4).to_json_value()]
    assert Multirange.from_json_value(payload) == value


def test_multirange_json_rejects_mixed_element_types():
    payload = [
        Range(1, 2).to_json_value(),
        Range(date(2024, 1, 1), date(2024, 2, 1)).to_json_value(),
    ]
    with pytest.raises(ValueError):
        Multirange.from_json_value(payload)


def test_multirange_json_rejects_non_array():
    with pytest.raises(ValueError):
        Multirange.from_json_value("[]")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Adapter base
# ---------------------------------------------------------------------------


class _LiteralRangeAdapter(RangeAdapterBase):
    """Minimal concrete adapter used to exercise the base hooks."""

    def _encode(
        self,
        value: Union[Range, Multirange],
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        if target_type is not str:
            raise TypeError(f"unsupported target type: {target_type!r}")
        return value.to_postgres_literal()

    def _decode(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Union[Range, Multirange]:
        if target_type is Multirange:
            return Multirange.from_json_value(value)
        if target_type is Range:
            return Range.from_json_value(value)
        raise TypeError(f"unsupported target type: {target_type!r}")


class _BrokenRangeAdapter(RangeAdapterBase):
    def _encode(
        self,
        value: Union[Range, Multirange],
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        raise ValueError("encode hook failed")

    def _decode(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Union[Range, Multirange]:
        raise ValueError("decode hook failed")


class _WrongResultAdapter(RangeAdapterBase):
    def _encode(
        self,
        value: Union[Range, Multirange],
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        return "encoded"

    def _decode(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Union[Range, Multirange]:
        return "not-a-neutral-value"  # type: ignore[return-value]


def test_adapter_neutral_type():
    assert RangeAdapterBase.neutral_type is Range


def test_adapter_encodes_range_and_multirange():
    adapter = _LiteralRangeAdapter()
    assert adapter.to_database(Range(1, 10), str) == "[1,10)"
    assert adapter.to_database(Multirange((Range(1, 2), Range(3, 4))), str) == "{[1,2),[3,4)}"
    assert adapter.to_database(None, str) is None


def test_adapter_decodes_range_and_multirange_json():
    adapter = _LiteralRangeAdapter()
    range_value = Range(1, 10)
    assert adapter.from_database(range_value.to_json_value(), Range) == range_value

    multi_value = Multirange((Range(1, 2), Range(3, 4)))
    assert adapter.from_database(multi_value.to_json_value(), Multirange) == multi_value

    # Optional targets are unwrapped by BaseSQLTypeAdapter before dispatch.
    optional_payload = range_value.to_json_value()
    assert adapter.from_database(optional_payload, Optional[Range]) == range_value

    # Already-neutral values pass through unchanged.
    assert adapter.from_database(range_value, Range) is range_value
    assert adapter.from_database(multi_value, Multirange) is multi_value


def test_adapter_rejects_non_neutral_encoding_input():
    adapter = _LiteralRangeAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(1, str)

    message = str(excinfo.value)
    assert message.startswith("Cannot convert int to Range: ")
    assert "expected Range or Multirange" in message


def test_adapter_wraps_encode_hook_errors():
    adapter = _BrokenRangeAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(Range(1, 10), str)

    message = str(excinfo.value)
    assert message.startswith("Cannot convert Range to Range: ")
    assert "encode hook failed" in message


def test_adapter_wraps_decode_hook_errors():
    adapter = _BrokenRangeAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database("whatever", Range)

    message = str(excinfo.value)
    assert message.startswith("Cannot convert str to Range: ")
    assert "decode hook failed" in message


def test_adapter_rejects_decoder_returning_wrong_neutral_type():
    adapter = _WrongResultAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database("whatever", Range)

    message = str(excinfo.value)
    assert "decoder must return Range or Multirange, got str" in message


def test_adapter_rejects_target_kind_mismatch():
    adapter = _LiteralRangeAdapter()
    with pytest.raises(TypeConversionError):
        adapter.from_database(Range(1, 2), Multirange)
    with pytest.raises(TypeConversionError):
        adapter.from_database(
            Multirange(
                (Range(1, 2),),
            ),
            Range,
        )


def test_adapter_wraps_json_decode_failures():
    adapter = _LiteralRangeAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database({"lower": 1}, Range)

    message = str(excinfo.value)
    assert message.startswith("Cannot convert dict to Range: ")
    assert "missing fields" in message
