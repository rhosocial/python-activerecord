# tests/rhosocial/activerecord_test/feature/backend/adapters/test_vector.py
"""DB-free tests for the neutral Vector type and its adapter base."""

import json
import math
from dataclasses import FrozenInstanceError

import pytest

from rhosocial.activerecord.backend.adapters.json_codec import AdapterJSONCodec
from rhosocial.activerecord.backend.adapters.vector import (
    Vector,
    VectorAdapterBase,
)
from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter


class JSONTextVectorAdapter(VectorAdapterBase):
    """A backend-style adapter that stores vectors as JSON text."""

    def _encode(self, vector, target_type, options):
        if target_type is not str:
            raise TypeError(f"unsupported target type {target_type!r}")
        return json.dumps(vector.to_json_value())

    def _decode(self, value, options):
        if not isinstance(value, str):
            raise TypeError(f"expected JSON text, got {type(value).__name__}")
        return Vector.from_json_value(json.loads(value))


class ListVectorAdapter(VectorAdapterBase):
    """Stores vectors as native lists (for example in a JSON column)."""

    def _encode(self, vector, target_type, options):
        if target_type is not list:
            raise TypeError(f"unsupported target type {target_type!r}")
        return vector.to_json_value()

    def _decode(self, value, options):
        return Vector.from_json_value(value)


class BrokenVectorAdapter(VectorAdapterBase):
    """Returns a non-neutral value from its decode hook."""

    def _encode(self, vector, target_type, options):
        return vector.to_json_value()

    def _decode(self, value, options):
        return list(value)


@pytest.mark.parametrize(
    "values",
    [
        (1.0, 2.5),
        [1.0, 2.5],
        (0, 1, 2),
        (-1, 0.0),
        (0.5,),
    ],
)
def test_accepts_numeric_sequences(values):
    vector = Vector(values)
    assert vector.values == tuple(values)
    assert vector.dimension == len(values)


def test_dimension_tracks_component_count():
    assert Vector((1.0,)).dimension == 1
    assert Vector((1.0, 2.0, 3.0, 4.0)).dimension == 4


@pytest.mark.parametrize("values", [(), []])
def test_rejects_empty_sequences(values):
    with pytest.raises(ValueError, match="at least one"):
        Vector(values)


@pytest.mark.parametrize("values", ["1,2", b"\x01\x02", 3, None, {1: 1.0}])
def test_rejects_non_sequence_values(values):
    with pytest.raises(TypeError, match="tuple or list"):
        Vector(values)


@pytest.mark.parametrize(
    "values",
    [
        (True, 1.0),
        ("1.0", 2.0),
        (None,),
        (1.0, [2.0]),
        (object(),),
    ],
)
def test_rejects_non_numeric_components(values):
    with pytest.raises(TypeError, match="int or float"):
        Vector(values)


@pytest.mark.parametrize(
    "value, json_name",
    [
        (float("nan"), "NaN"),
        (float("inf"), "Infinity"),
        (float("-inf"), "-Infinity"),
    ],
)
def test_rejects_non_finite_by_default(value, json_name):
    with pytest.raises(ValueError, match="allow_non_finite"):
        Vector((1.0, value))


@pytest.mark.parametrize(
    "value, json_name",
    [
        (float("nan"), "NaN"),
        (float("inf"), "Infinity"),
        (float("-inf"), "-Infinity"),
    ],
)
def test_accepts_non_finite_only_when_explicit(value, json_name):
    vector = Vector((value,), allow_non_finite=True)
    assert vector.to_json_value() == [json_name]


def test_allow_non_finite_must_be_bool():
    with pytest.raises(TypeError, match="allow_non_finite must be bool"):
        Vector((1.0,), allow_non_finite=1)


def test_is_immutable():
    vector = Vector((1.0, 2.0))
    with pytest.raises(FrozenInstanceError):
        vector.values = (3.0,)
    with pytest.raises(FrozenInstanceError):
        vector.allow_non_finite = True


def test_equality_and_hash_use_normalized_values():
    from_list = Vector([1.0, 2.0])
    from_tuple = Vector((1.0, 2.0))
    permitted = Vector((1.0, 2.0), allow_non_finite=True)

    for other in (from_tuple, permitted):
        assert from_list == other
        assert hash(from_list) == hash(other)

    assert len({from_list, from_tuple, permitted}) == 1
    assert from_list != Vector((1.0, 2.5))
    assert from_list != [1.0, 2.0]


def test_json_value_is_a_list_of_numbers():
    assert Vector((1, 2.5)).to_json_value() == [1, 2.5]


@pytest.mark.parametrize("values", [(0.0,), (1, 2, 3), (-1.5, 0.0, 2.25)])
def test_json_round_trip(values):
    original = Vector(values)
    payload = original.to_json_value()
    assert isinstance(payload, list)
    assert Vector.from_json_value(payload) == original


def test_json_round_trip_of_non_finite_values():
    original = Vector(
        (float("nan"), float("-inf"), 0.0, float("inf")),
        allow_non_finite=True,
    )
    payload = original.to_json_value()
    assert payload == ["NaN", "-Infinity", 0.0, "Infinity"]

    restored = Vector.from_json_value(payload)
    assert restored.dimension == 4
    assert math.isnan(restored.values[0])
    assert restored.values[1] == float("-inf")
    assert restored.values[2] == 0.0
    assert restored.values[3] == float("inf")


@pytest.mark.parametrize(
    "payload, exc_type",
    [
        ([], ValueError),
        (["not-a-number"], ValueError),
        (["nan"], ValueError),
        ([1, True], TypeError),
        ([1, None], TypeError),
        ("[1, 2]", TypeError),
        (b"\x01\x02", TypeError),
        (None, TypeError),
        ({"values": [1]}, TypeError),
    ],
)
def test_from_json_value_rejects_invalid_payloads(payload, exc_type):
    with pytest.raises(exc_type):
        Vector.from_json_value(payload)


def test_adapter_uses_neutral_type_and_base_class():
    adapter = JSONTextVectorAdapter()
    assert isinstance(adapter, BaseSQLTypeAdapter)
    assert adapter.neutral_type is Vector


def test_json_text_adapter_round_trip():
    adapter = JSONTextVectorAdapter()
    for vector in (Vector((1.0, 2.5)), Vector((0, 1, 2))):
        stored = adapter.to_database(vector, str)
        assert isinstance(stored, str)
        assert json.loads(stored) == vector.to_json_value()
        assert adapter.from_database(stored, Vector) == vector

    # Accepted input coercions: lists and tuples of numbers.
    assert adapter.to_database([1.0, 2.0], str) == "[1.0, 2.0]"
    assert adapter.to_database((3, 4), str) == "[3, 4]"


def test_list_adapter_round_trip():
    adapter = ListVectorAdapter()
    for vector in (Vector((1.0, 2.5)), Vector((0, 1, 2))):
        stored = adapter.to_database(vector, list)
        assert isinstance(stored, list)
        assert adapter.from_database(stored, Vector) == vector


def test_adapter_passes_none_through():
    adapter = JSONTextVectorAdapter()
    assert adapter.to_database(None, str) is None
    assert adapter.from_database(None, Vector) is None


def test_adapter_wraps_encode_failures():
    adapter = JSONTextVectorAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(Vector((1.0,)), int)
    message = str(excinfo.value)
    assert "Cannot convert Vector to Vector" in message
    assert "unsupported target type" in message


@pytest.mark.parametrize("value", [["a"], [], ["NaN", "nope"], [1, True]])
def test_adapter_wraps_invalid_python_values(value):
    adapter = JSONTextVectorAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(value, str)
    assert "to Vector" in str(excinfo.value)


def test_adapter_wraps_unsupported_python_types():
    adapter = JSONTextVectorAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(object(), str)
    assert "Cannot convert object to Vector" in str(excinfo.value)
    assert "expected Vector or a sequence of numbers" in str(excinfo.value)


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        '["a"]',
        "[1, true]",
        '{"values": [1.0]}',
        42,
        b"[1.0]",
    ],
)
def test_adapter_wraps_decode_failures(value):
    adapter = JSONTextVectorAdapter()
    with pytest.raises(TypeConversionError):
        adapter.from_database(value, Vector)


def test_adapter_rejects_non_neutral_decode_result():
    adapter = BrokenVectorAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database([1.0, 2.0], Vector)
    assert "decoder must return Vector" in str(excinfo.value)


def test_tagged_json_codec_round_trip():
    assert Vector.json_type_tag == "vector"
    codec = AdapterJSONCodec(tagged=True)
    original = Vector((1.0, 2.5, -3.0))

    encoded = json.loads(codec.dumps(original))
    assert encoded == {"__type__": "vector", "value": [1.0, 2.5, -3.0]}

    restored = codec.loads(codec.dumps(original))
    assert isinstance(restored, Vector)
    assert restored == original
