# tests/rhosocial/activerecord_test/feature/backend/adapters/test_adapter_error_contract.py
"""What the five complex-family adapters refuse, and how they say it.

Each adapter base (``GeometryAdapterBase`` and its four siblings) wraps two
jobs that a backend subclass implements:

* ``_coerce_*`` -- turn the caller's input into the neutral value class;
* ``_encode`` / ``_decode`` -- turn it into, and back from, the driver form.

The base's contract is that **a subclass hook's failure never escapes as its
own exception type**: a ``TypeError``/``ValueError`` from ``_encode`` or
``_decode`` becomes a ``TypeConversionError`` naming the value and the reason,
while a ``TypeConversionError`` the hook raised itself passes through
untouched. That is what lets one error-handling path serve ten backends.

The second half of the contract is the decode side: a hook must hand back the
neutral class it claims, so a driver-private object cannot leak into the model
layer as "some object that happens to be a Range".

The scripted adapters below are deliberately boring: they exist to raise, or
to return a wrong type, so the base's wrapping is what is under test.
"""

from typing import Any, Dict, Optional, Type

import pytest

from rhosocial.activerecord.backend.adapters import (
    BitString,
    BitStringAdapterBase,
    Geometry,
    GeometryAdapterBase,
    MacAddress,
    MacAddressAdapterBase,
    Multirange,
    Range,
    RangeAdapterBase,
    Vector,
    VectorAdapterBase,
)
from rhosocial.activerecord.backend.adapters.json_codec import (
    AdapterJSONCodec,
    register_type,
    registered_types,
)
from rhosocial.activerecord.backend.errors import TypeConversionError


class _Scripted:
    """The two knobs a scripted adapter needs: what to raise, what to return."""

    failure: Optional[Exception] = None
    decoded: Any = None


class _GeometryAdapter(_Scripted, GeometryAdapterBase):
    def _encode(self, geometry: Geometry, target_type: Type, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return geometry.to_wkt()

    def _decode(self, value: Any, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return self.decoded


class _RangeAdapter(_Scripted, RangeAdapterBase):
    def _encode(self, neutral: Any, target_type: Type, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return "encoded"

    def _decode(self, value: Any, target_type: Type, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return self.decoded


class _MacAdapter(_Scripted, MacAddressAdapterBase):
    def _encode(self, mac: MacAddress, target_type: Type, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return str(mac)

    def _decode(self, value: Any, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return self.decoded


class _VectorAdapter(_Scripted, VectorAdapterBase):
    def _encode(self, vector: Vector, target_type: Type, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return "encoded"

    def _decode(self, value: Any, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return self.decoded


class _BitStringAdapter(_Scripted, BitStringAdapterBase):
    def _encode(self, bits: BitString, target_type: Type, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return "encoded"

    def _decode(self, value: Any, options: Dict[str, Any]) -> Any:
        if self.failure is not None:
            raise self.failure
        return self.decoded


def _scripted(adapter_class, failure=None, decoded=None):
    adapter = adapter_class()
    adapter.failure = failure
    adapter.decoded = decoded
    return adapter


# ---------------------------------------------------------------------------
# 1. A hook's failure is wrapped, not leaked
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "adapter_class, value",
    [
        (_GeometryAdapter, "POINT (1 1)"),
        (_RangeAdapter, Range(1, 2, "[)")),
        (_MacAdapter, "02:00:00:00:00:01"),
        (_VectorAdapter, [1.0, 2.0]),
        (_BitStringAdapter, "1010"),
    ],
    ids=["geometry", "range", "mac", "vector", "bitstring"],
)
def test_a_hook_error_becomes_a_conversion_error(adapter_class, value):
    adapter = _scripted(adapter_class, failure=ValueError("boom"))

    with pytest.raises(TypeConversionError, match="boom"):
        adapter.to_database(value, str)


@pytest.mark.parametrize(
    "adapter_class, written, stored",
    [
        (_GeometryAdapter, "POINT (1 1)", "stored"),
        (_RangeAdapter, Range(1, 2, "[)"), "stored"),
        (_MacAdapter, "02:00:00:00:00:01", "stored"),
        (_VectorAdapter, [1.0, 2.0], "stored"),
        (_BitStringAdapter, "1010", "stored"),
    ],
    ids=["geometry", "range", "mac", "vector", "bitstring"],
)
@pytest.mark.parametrize("direction", ["write", "read"], ids=["to_database", "from_database"])
def test_a_conversion_error_raised_by_the_hook_passes_through(
    adapter_class, written, stored, direction
):
    """Wrapping a ``TypeConversionError`` again would hide which layer refused
    the value, so both directions re-raise it as-is.

    The read direction gets a stored scalar rather than the neutral value:
    the range base answers an already-neutral value before any hook runs.
    """
    original = TypeConversionError("already specific")
    adapter = _scripted(adapter_class, failure=original)

    if direction == "write":
        with pytest.raises(TypeConversionError, match="already specific") as caught:
            adapter.to_database(written, str)
    else:
        with pytest.raises(TypeConversionError, match="already specific") as caught:
            adapter.from_database(stored, str)

    assert caught.value is original


@pytest.mark.parametrize(
    "adapter_class",
    [_GeometryAdapter, _RangeAdapter, _MacAdapter, _VectorAdapter, _BitStringAdapter],
    ids=["geometry", "range", "mac", "vector", "bitstring"],
)
def test_a_read_hook_error_is_wrapped_too(adapter_class):
    adapter = _scripted(adapter_class, failure=ValueError("bad store"))

    with pytest.raises(TypeConversionError, match="bad store"):
        adapter.from_database("stored", str)


# ---------------------------------------------------------------------------
# 2. Coercion: the caller's input, before any hook runs
# ---------------------------------------------------------------------------


def test_geometry_input_must_be_a_geometry_wkt_or_geojson():
    adapter = _GeometryAdapter()

    with pytest.raises(TypeConversionError, match="expected a Geometry, WKT text, or GeoJSON"):
        adapter.to_database(42, str)


def test_invalid_wkt_names_the_position():
    adapter = _GeometryAdapter()

    with pytest.raises(TypeConversionError, match="invalid WKT"):
        adapter.to_database("POINT[1]", str)


def test_invalid_geojson_names_the_reason():
    adapter = _GeometryAdapter()

    with pytest.raises(TypeConversionError, match="invalid GeoJSON"):
        adapter.to_database({"type": "Point"}, str)


def test_geometry_accepts_the_three_shapes_its_docstring_names():
    adapter = _GeometryAdapter()

    assert adapter.to_database(Geometry.from_wkt("POINT (1 1)"), str) == "POINT (1.0 1.0)"
    assert adapter.to_database("POINT (1 1)", str) == "POINT (1.0 1.0)"
    assert adapter.to_database({"type": "Point", "coordinates": [1, 1]}, str) == "POINT (1.0 1.0)"


def test_a_range_adapter_refuses_a_value_that_is_not_a_range():
    adapter = _RangeAdapter()

    with pytest.raises(TypeConversionError, match="expected Range or Multirange"):
        adapter.to_database("11", str)


def test_mac_input_bool_is_refused_before_parsing():
    """``bool`` is an int subclass, and parsing it would silently build a
    1-octet address; the coercion refuses it by name."""
    adapter = _MacAdapter()

    with pytest.raises(TypeConversionError, match="bool is not a valid MAC address input"):
        adapter.to_database(True, str)


def test_mac_input_of_an_unlisted_type_is_refused():
    adapter = _MacAdapter()

    with pytest.raises(TypeConversionError, match="expected MacAddress, str, bytes, or int"):
        adapter.to_database(1.5, str)


def test_a_mac_text_with_a_non_hex_digit_is_refused():
    adapter = _MacAdapter()

    with pytest.raises(TypeConversionError, match="non-hexadecimal"):
        adapter.to_database("ZZZZZZZZZZZZ", str)


def test_empty_bytes_are_not_a_bit_string():
    adapter = _BitStringAdapter()

    with pytest.raises(TypeConversionError, match="bytes must not be empty"):
        adapter.to_database(b"", str)


def test_bit_string_text_must_be_binary_digits():
    adapter = _BitStringAdapter()

    with pytest.raises(TypeConversionError, match="may only contain"):
        adapter.to_database("102", str)


def test_a_vector_may_carry_a_non_finite_component():
    """The neutral class is the place a non-finite component is declared
    explicitly; the adapter must not drop that permission on the way in."""
    vector = Vector.from_json_value([float("nan"), 1.0])

    assert vector.allow_non_finite is True
    assert not all(isinstance(item, str) for item in vector.values)


def test_a_vector_refuses_a_name_that_is_not_a_non_finite_spelling():
    with pytest.raises(ValueError, match="not a recognized non-finite name"):
        Vector.from_json_value(["three"])


# ---------------------------------------------------------------------------
# 3. Decode: a hook must return the neutral class it claims
# ---------------------------------------------------------------------------


def test_a_range_decoder_must_answer_the_range_it_was_asked_for():
    adapter = _scripted(_RangeAdapter, decoded=Multirange([Range(1, 2, "[)")]))

    with pytest.raises(TypeConversionError, match="expected Range, got Multirange"):
        adapter.from_database("stored", Range)


def test_a_multirange_decoder_must_answer_a_multirange():
    adapter = _scripted(_RangeAdapter, decoded=Range(1, 2, "[)"))

    with pytest.raises(TypeConversionError, match="expected Multirange, got Range"):
        adapter.from_database("stored", Multirange)


def test_a_range_decoder_must_answer_a_range_or_multirange():
    adapter = _scripted(_RangeAdapter, decoded="not a range")

    with pytest.raises(TypeConversionError, match="decoder must return Range or Multirange"):
        adapter.from_database("stored", Multirange)


@pytest.mark.parametrize(
    "adapter_class, label, answer",
    [
        (_MacAdapter, "MacAddress", MacAddress.parse("02:00:00:00:00:01")),
        (_VectorAdapter, "Vector", Vector((1.0, 2.0))),
        (_BitStringAdapter, "BitString", BitString.from_bits("1010")),
    ],
    ids=["mac", "vector", "bitstring"],
)
def test_a_decoder_answers_the_neutral_class_or_is_refused(adapter_class, label, answer):
    adapter = _scripted(adapter_class, decoded="driver-private object")

    with pytest.raises(TypeConversionError, match=f"decoder must return {label}"):
        adapter.from_database("stored", str)

    # The same adapter answers when the hook answers correctly.
    adapter.decoded = answer
    assert adapter.from_database("stored", str) is answer


# ---------------------------------------------------------------------------
# 4. The JSON codec registry
# ---------------------------------------------------------------------------


class _Widget:
    """Registered under a tag but without a declared tag attribute, so the
    codec has to find it through the registry rather than on the object."""

    def to_json_value(self):
        return {"size": 1}

    @classmethod
    def from_json_value(cls, value):
        return cls()


def test_the_registry_lists_the_six_neutral_families():
    # Other suites (e.g. the shared feature/adapters contracts) may register
    # additional demo tags in the same process; assert the six neutral families
    # are present rather than that the registry has no other entries.
    assert {"bitstring", "geometry", "mac_address", "multirange", "range", "vector"} <= set(
        registered_types()
    )


def test_the_listing_is_a_copy():
    listing = registered_types()
    listing["sentinel"] = _Widget

    assert "sentinel" not in registered_types()


def test_a_registered_class_is_tagged_through_the_registry():
    """``default`` finds the tag two ways: on the object, or by looking the
    object's class up among the registered ones. The second is what a neutral
    class without a declared tag relies on."""
    register_type("widget", _Widget)
    codec = AdapterJSONCodec(tagged=True)

    # A mapping payload carries the marker inside it; only a non-mapping
    # payload needs the ``value`` wrapper (``default``'s other branch).
    assert codec.default(_Widget()) == {"size": 1, "__type__": "widget"}


def test_a_document_with_an_unknown_tag_is_carried_unchanged():
    codec = AdapterJSONCodec()

    payload = {"__type__": "not-registered", "a": 1}
    assert codec.loads(codec.dumps(payload)) == payload
