# tests/rhosocial/activerecord_test/feature/backend/adapters/test_json_codec.py
"""
Tests for the neutral-adapter JSON codec.

The neutral type families are represented by local stubs here: the codec is
duck-typed, so these tests exercise the contract (``to_json_value`` plus a
stable tag) without importing geometry/vector/... implementations.
"""

import json

import pytest

from rhosocial.activerecord.backend.adapters.json_codec import (
    AdapterJSONCodec,
    register_type,
    unregister_type,
)


class _StubEquality:
    def __eq__(self, other):
        return type(self) is type(other) and self.__dict__ == other.__dict__

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__!r})"


class StubGeometry(_StubEquality):
    json_type_tag = "geometry"

    def __init__(self, type_, coordinates, srid=None):
        self.type_ = type_
        self.coordinates = list(coordinates)
        self.srid = srid

    def to_json_value(self):
        value = {"type": self.type_, "coordinates": self.coordinates}
        if self.srid is not None:
            value["srid"] = self.srid
        return value

    @classmethod
    def from_json_value(cls, value):
        return cls(value["type"], value["coordinates"], value.get("srid"))


class StubVector(_StubEquality):
    json_type_tag = "vector"

    def __init__(self, values):
        self.values = tuple(values)

    def to_json_value(self):
        return list(self.values)

    @classmethod
    def from_json_value(cls, value):
        return cls(value)


class StubBitString(_StubEquality):
    json_type_tag = "bitstring"

    def __init__(self, data, bit_length):
        self.data = bytes(data)
        self.bit_length = bit_length

    def to_json_value(self):
        # Deliberately keeps a leading zero nibble: the codec must not rewrite
        # the family's canonical value.
        return {"hex": self.data.hex(), "bit_length": self.bit_length}

    @classmethod
    def from_json_value(cls, value):
        return cls(bytes.fromhex(value["hex"]), value["bit_length"])


class StubRange(_StubEquality):
    json_type_tag = "range"

    def __init__(self, lower=None, upper=None, bounds="[)", empty=False, element_type="int"):
        self.lower = lower
        self.upper = upper
        self.bounds = bounds
        self.empty = empty
        self.element_type = element_type

    def to_json_value(self):
        return {
            "lower": self.lower,
            "upper": self.upper,
            "bounds": self.bounds,
            "empty": self.empty,
            "element_type": self.element_type,
        }

    @classmethod
    def from_json_value(cls, value):
        return cls(
            value.get("lower"),
            value.get("upper"),
            value["bounds"],
            value["empty"],
            value["element_type"],
        )


class StubMultirange(_StubEquality):
    json_type_tag = "multirange"

    def __init__(self, ranges):
        self.ranges = tuple(ranges)

    def to_json_value(self):
        return [item.to_json_value() for item in self.ranges]

    @classmethod
    def from_json_value(cls, value):
        return cls(StubRange.from_json_value(item) for item in value)


class StubMacAddress(_StubEquality):
    json_type_tag = "mac_address"

    def __init__(self, text):
        self.text = text.lower()

    def to_json_value(self):
        return self.text

    @classmethod
    def from_json_value(cls, value):
        return cls(value)


STUB_TYPES = {
    "geometry": StubGeometry,
    "vector": StubVector,
    "bitstring": StubBitString,
    "range": StubRange,
    "multirange": StubMultirange,
    "mac_address": StubMacAddress,
}


@pytest.fixture(autouse=True)
def registered_stub_types():
    """Register local stubs for decoding, and clean up afterwards."""
    for tag, cls in STUB_TYPES.items():
        register_type(tag, cls)
    yield
    for tag in STUB_TYPES:
        unregister_type(tag)


def test_tagged_is_off_by_default():
    """Tagged mode must default to off, both on the class and an instance."""
    assert AdapterJSONCodec.tagged is False
    assert AdapterJSONCodec().tagged is False


def test_default_serializes_untagged_canonical_value():
    """default() returns to_json_value() unchanged when tagging is off."""
    codec = AdapterJSONCodec()

    assert codec.dumps(StubVector((1.0, 2.5))) == json.dumps([1.0, 2.5])
    assert codec.dumps(StubMacAddress("AA:BB:CC:DD:EE:FF")) == json.dumps("aa:bb:cc:dd:ee:ff")

    geometry = json.loads(codec.dumps(StubGeometry("Point", [1.0, 2.0], 4326)))
    assert geometry == {"type": "Point", "coordinates": [1.0, 2.0], "srid": 4326}
    assert "__type__" not in geometry


def test_default_works_as_json_default_hook():
    """The hook composes with plain json.dumps, without patching the stdlib."""
    codec = AdapterJSONCodec()
    text = json.dumps({"payload": StubVector((3.0,))}, default=codec.default)
    assert json.loads(text) == {"payload": [3.0]}
    assert json.dumps({"plain": [1, 2]}) == '{"plain": [1, 2]}'


def test_tagged_default_merges_marker_into_dict_payload():
    codec = AdapterJSONCodec(tagged=True)
    value = json.loads(codec.dumps(StubGeometry("Point", [1.0, 2.0], 4326)))
    assert value == {
        "__type__": "geometry",
        "type": "Point",
        "coordinates": [1.0, 2.0],
        "srid": 4326,
    }


def test_tagged_default_wraps_non_dict_payload_under_value():
    codec = AdapterJSONCodec(tagged=True)

    assert json.loads(codec.dumps(StubVector((1.0, 2.0)))) == {
        "__type__": "vector",
        "value": [1.0, 2.0],
    }
    assert json.loads(codec.dumps(StubMacAddress("AA:BB:CC:DD:EE:FF"))) == {
        "__type__": "mac_address",
        "value": "aa:bb:cc:dd:ee:ff",
    }


def test_default_rejects_non_neutral_objects():
    codec = AdapterJSONCodec()

    with pytest.raises(TypeError, match="not JSON serializable"):
        codec.default(object())
    with pytest.raises(TypeError, match="not JSON serializable"):
        codec.dumps({"value": object()})


def test_default_rejects_neutral_like_object_without_tag():
    """to_json_value alone is not enough: a stable tag is part of the contract."""

    class NoTag:
        def to_json_value(self):
            return 1

    codec = AdapterJSONCodec()
    with pytest.raises(TypeError, match="type tag"):
        codec.default(NoTag())


def test_default_rejects_tagged_object_without_to_json_value():
    class NoJSONValue:
        json_type_tag = "vector"

    codec = AdapterJSONCodec()
    with pytest.raises(TypeError, match="not JSON serializable"):
        codec.default(NoJSONValue())


def test_tagged_round_trip_of_all_stub_families():
    codec = AdapterJSONCodec(tagged=True)
    original = {
        "geometry": StubGeometry("LineString", [[0.0, 0.0], [1.0, 1.0]]),
        "vector": StubVector((1.0, 2.0, 3.0)),
        "bitstring": StubBitString(b"\x0f\xa0", 12),
        "range": StubRange(1, 5, "[)", False, "int"),
        "multirange": StubMultirange([StubRange(1, 2), StubRange(5, 9, "(]")]),
        "mac": StubMacAddress("aa:bb:cc:dd:ee:ff"),
    }

    restored = codec.loads(codec.dumps(original))

    assert restored == original
    assert isinstance(restored["geometry"], StubGeometry)
    assert isinstance(restored["multirange"].ranges[0], StubRange)


def test_tagged_round_trip_keeps_bitstring_payload_exact():
    codec = AdapterJSONCodec(tagged=True)
    original = StubBitString(b"\x0a\xf0", 20)
    encoded = json.loads(codec.dumps(original))
    assert encoded == {"__type__": "bitstring", "hex": "0af0", "bit_length": 20}
    assert codec.loads(codec.dumps(original)) == original


def test_untagged_decode_leaves_dict_untouched():
    """JSON produced without tags decodes to plain dicts."""
    codec = AdapterJSONCodec()
    geometry = StubGeometry("Point", [1.0, 2.0])

    text = codec.dumps(geometry)
    restored = codec.loads(text)

    assert restored == {"type": "Point", "coordinates": [1.0, 2.0]}
    assert isinstance(restored, dict)
    assert not isinstance(restored, StubGeometry)
    assert "__type__" not in restored


def test_object_hook_leaves_dicts_without_marker_untouched():
    codec = AdapterJSONCodec()
    value = {"type": "Point", "coordinates": [1.0, 2.0]}
    assert codec.object_hook(value) == value


def test_object_hook_leaves_unknown_tag_untouched():
    codec = AdapterJSONCodec()
    value = {"__type__": "not_a_neutral_type", "value": 1}
    assert codec.object_hook(value) == value


def test_object_hook_reconstructs_marked_payloads():
    codec = AdapterJSONCodec()
    assert codec.object_hook({"__type__": "vector", "value": [1.0, 2.0]}) == StubVector((1.0, 2.0))
    assert codec.object_hook({"__type__": "geometry", "type": "Point", "coordinates": [1.0, 2.0]}) == (
        StubGeometry("Point", [1.0, 2.0])
    )


def test_dumps_and_loads_of_nested_structures():
    codec = AdapterJSONCodec(tagged=True)
    original = {
        "items": [
            {"vector": StubVector((1.0, 2.0)), "labels": ["a", "b"]},
            {"window": StubRange(0, 10)},
            {"mac": StubMacAddress("11:22:33:44:55:66")},
        ],
        "meta": {
            "nested": {
                "geometry": StubGeometry("Point", [3.5, 4.5]),
                "numbers": [1, 2, 3],
            }
        },
    }

    restored = codec.loads(codec.dumps(original))

    assert restored == original
    assert isinstance(restored["items"][0]["vector"], StubVector)
    assert isinstance(restored["items"][1]["window"], StubRange)
    assert isinstance(restored["meta"]["nested"]["geometry"], StubGeometry)
    assert restored["meta"]["nested"]["numbers"] == [1, 2, 3]


def test_non_neutral_nested_values_stay_plain():
    codec = AdapterJSONCodec(tagged=True)
    original = {
        "plain": {"alpha": 1, "beta": [True, None, "text"]},
        "vector": StubVector((0.5,)),
    }

    restored = codec.loads(codec.dumps(original))

    assert restored["plain"] == original["plain"]
    assert isinstance(restored["vector"], StubVector)


def test_registered_class_without_tag_attribute():
    class RegisteredOnly:
        def __init__(self, number):
            self.number = number

        def to_json_value(self):
            return {"number": self.number}

        @classmethod
        def from_json_value(cls, value):
            return cls(value["number"])

        def __eq__(self, other):
            return type(self) is type(other) and self.number == other.number

    register_type("custom", RegisteredOnly)
    try:
        codec = AdapterJSONCodec(tagged=True)
        assert json.loads(codec.dumps(RegisteredOnly(7))) == {"__type__": "custom", "number": 7}
        assert codec.loads(codec.dumps(RegisteredOnly(7))) == RegisteredOnly(7)
    finally:
        unregister_type("custom")


def test_register_type_validates_input():
    class NoJSONMethods:
        pass

    with pytest.raises(ValueError, match="non-empty"):
        register_type("", StubVector)
    with pytest.raises(TypeError, match="must define"):
        register_type("invalid", NoJSONMethods)
    with pytest.raises(TypeError, match="must be a class"):
        register_type("invalid", StubVector((1.0,)))
