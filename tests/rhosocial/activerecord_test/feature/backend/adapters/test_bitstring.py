# tests/rhosocial/activerecord_test/feature/backend/adapters/test_bitstring.py
"""DB-free tests for the neutral BitString type and its adapter base."""

import json
from dataclasses import FrozenInstanceError

import pytest

from rhosocial.activerecord.backend.adapters.bitstring import (
    BitString,
    BitStringAdapterBase,
)
from rhosocial.activerecord.backend.adapters.json_codec import AdapterJSONCodec
from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter


class BitsTextAdapter(BitStringAdapterBase):
    """A backend-style adapter that stores bit strings as 0/1 text."""

    def _encode(self, bits, target_type, options):
        if target_type is not str:
            raise TypeError(f"unsupported target type {target_type!r}")
        return bits.to_bits()

    def _decode(self, value, options):
        if not isinstance(value, str):
            raise TypeError(f"expected bit text, got {type(value).__name__}")
        return BitString.from_bits(value)


class RawBytesAdapter(BitStringAdapterBase):
    """Stores the raw bytes; lossless only for whole-byte bit lengths."""

    def _encode(self, bits, target_type, options):
        if target_type is not bytes:
            raise TypeError(f"unsupported target type {target_type!r}")
        return bits.data

    def _decode(self, value, options):
        if not isinstance(value, bytes):
            raise TypeError(f"expected bytes, got {type(value).__name__}")
        return BitString.from_bytes(value)


class BrokenBitStringAdapter(BitStringAdapterBase):
    """Returns a non-neutral value from its decode hook."""

    def _encode(self, bits, target_type, options):
        return bits.to_bits()

    def _decode(self, value, options):
        return str(value)


def test_direct_construction_accepts_valid_bit_sequences():
    bits = BitString(b"\xff", 8)
    assert bits.data == b"\xff"
    assert bits.bit_length == 8
    assert bits.to_bits() == "11111111"


@pytest.mark.parametrize(
    "data, bit_length, canonical_data",
    [
        (b"\x80", 1, b"\x80"),
        (bytearray(b"\xa0"), 3, b"\xa0"),
        (b"\x00", 1, b"\x00"),
        (b"\xf0", 4, b"\xf0"),
    ],
)
def test_direct_construction_normalizes_bytes(data, bit_length, canonical_data):
    bits = BitString(data, bit_length)
    assert bits.data == canonical_data
    assert isinstance(bits.data, bytes)


@pytest.mark.parametrize(
    "data, exc_type",
    [
        ("ff", TypeError),
        (None, TypeError),
        (5, TypeError),
    ],
)
def test_construction_rejects_non_bytes_data(data, exc_type):
    with pytest.raises(exc_type, match="data must be bytes"):
        BitString(data, 8)


@pytest.mark.parametrize(
    "bit_length, exc_type",
    [
        ("8", TypeError),
        (8.0, TypeError),
        (True, TypeError),
    ],
)
def test_construction_rejects_non_int_bit_length(bit_length, exc_type):
    with pytest.raises(exc_type, match="bit_length must be int"):
        BitString(b"\xff", bit_length)


@pytest.mark.parametrize(
    "data, bit_length",
    [
        (b"", 1),
        (b"\x00", 0),
        (b"\x00", -1),
        (b"\xff", 9),
        (b"\x01", 4),  # unused low bits are not zero
        (b"\xff", 4),  # unused low bits are not zero
        (b"\x81", 1),  # unused low bits are not zero
    ],
)
def test_construction_rejects_out_of_range_lengths(data, bit_length):
    with pytest.raises(ValueError):
        BitString(data, bit_length)


def test_leading_zero_bytes_are_trimmed():
    assert BitString(b"\x00\xff\x00", 16).data == b"\xff\x00"
    assert BitString(b"\x00\x00", 8).data == b"\x00"
    # A zero byte that carries significant leading zero bits must stay.
    assert BitString(b"\x00\x80", 16).data == b"\x00\x80"


@pytest.mark.parametrize(
    "text, expected_int, expected_data",
    [
        ("1", 1, b"\x80"),
        ("10101", 21, b"\xa8"),
        ("00000000", 0, b"\x00"),
        ("11111111", 255, b"\xff"),
        ("101010101", 341, b"\xaa\x80"),
        ("00001", 1, b"\x08"),
    ],
)
def test_from_bits(text, expected_int, expected_data):
    bits = BitString.from_bits(text)
    assert bits.bit_length == len(text)
    assert bits.to_int() == expected_int
    assert bits.data == expected_data


@pytest.mark.parametrize("text", ["", "102", "10 1", "-1", "0b1"])
def test_from_bits_rejects_invalid_text(text):
    with pytest.raises(ValueError):
        BitString.from_bits(text)


def test_from_bits_rejects_non_text():
    with pytest.raises(TypeError, match="must be str"):
        BitString.from_bits(10101)


@pytest.mark.parametrize(
    "value, length, expected_bits",
    [
        (0, 1, "0"),
        (1, 1, "1"),
        (21, 5, "10101"),
        (255, 8, "11111111"),
        (1, 16, "0000000000000001"),
    ],
)
def test_from_int(value, length, expected_bits):
    bits = BitString.from_int(value, length)
    assert bits.bit_length == length
    assert bits.to_bits() == expected_bits
    assert bits.to_int() == value


@pytest.mark.parametrize(
    "value, length, exc_type",
    [
        (256, 8, ValueError),
        (-1, 8, ValueError),
        (1, 0, ValueError),
        (1, -1, ValueError),
        (1.5, 8, TypeError),
        (True, 8, TypeError),
        (1, "8", TypeError),
        (False, 8, TypeError),
    ],
)
def test_from_int_rejects_invalid_input(value, length, exc_type):
    with pytest.raises(exc_type):
        BitString.from_int(value, length)


def test_from_bytes_defaults_to_whole_bytes():
    bits = BitString.from_bytes(b"\xff")
    assert bits.bit_length == 8
    assert bits.to_bits() == "11111111"


def test_from_bytes_accepts_shorter_bit_length():
    bits = BitString.from_bytes(b"\xaa\x80", 9)
    assert bits.to_bits() == "101010101"
    assert bits.to_int() == 341


@pytest.mark.parametrize(
    "value, bit_length, exc_type",
    [
        (b"", None, ValueError),
        (b"\x01", 4, ValueError),
        ("ff", None, TypeError),
        (None, None, TypeError),
    ],
)
def test_from_bytes_rejects_invalid_input(value, bit_length, exc_type):
    with pytest.raises(exc_type):
        BitString.from_bytes(value, bit_length)


def test_to_bits_preserves_leading_zeros():
    bits = BitString.from_int(1, 8)
    assert bits.to_bits() == "00000001"
    assert bits.to_int() == 1


def test_to_int_of_zero_and_whole_bytes():
    assert BitString.from_bits("000").to_int() == 0
    assert BitString.from_bytes(b"\xff").to_int() == 255


@pytest.mark.parametrize(
    "bits, payload",
    [
        (BitString.from_bits("10101"), {"hex": "15", "bit_length": 5}),
        (BitString.from_bits("0000"), {"hex": "0", "bit_length": 4}),
        (BitString.from_bits("11111111"), {"hex": "ff", "bit_length": 8}),
        (BitString.from_bits("0000000011111111"), {"hex": "ff", "bit_length": 16}),
        (BitString.from_bits("101010101"), {"hex": "155", "bit_length": 9}),
    ],
)
def test_to_json_value_is_minimal_lowercase_hex(bits, payload):
    assert bits.to_json_value() == payload


def test_json_round_trip():
    for original in (
        BitString.from_bits("10101"),
        BitString.from_bits("0"),
        BitString.from_bytes(b"\xff"),
        BitString.from_int(1, 16),
    ):
        payload = original.to_json_value()
        assert isinstance(payload, dict)
        assert BitString.from_json_value(payload) == original


@pytest.mark.parametrize(
    "text, expected_bits",
    [
        ("a", "1010"),
        ("0", "0000"),
        ("abc", "101010111100"),
        ("ABC", "101010111100"),
        ("0f", "00001111"),
    ],
)
def test_from_json_value_accepts_plain_hex(text, expected_bits):
    bits = BitString.from_json_value(text)
    assert bits.bit_length == 4 * len(text)
    assert bits.to_bits() == expected_bits


@pytest.mark.parametrize(
    "payload, exc_type",
    [
        ("", ValueError),
        ("gg", ValueError),
        ("0x10", ValueError),
        ({"hex": "f"}, ValueError),
        ({"bit_length": 4}, ValueError),
        ({"hex": 15, "bit_length": 4}, ValueError),
        ({"hex": "f", "bit_length": "4"}, ValueError),
        ({"hex": "f", "bit_length": 0}, ValueError),
        ({"hex": "", "bit_length": 4}, ValueError),
        ({"hex": "ff", "bit_length": 4}, ValueError),
        (5, TypeError),
        ([1, 0], TypeError),
        (None, TypeError),
    ],
)
def test_from_json_value_rejects_invalid_payloads(payload, exc_type):
    with pytest.raises(exc_type):
        BitString.from_json_value(payload)


def test_equality_and_hash_use_canonical_bits():
    from_text = BitString.from_bits("10101")
    from_value = BitString.from_int(21, 5)
    from_json = BitString.from_json_value({"hex": "15", "bit_length": 5})

    for other in (from_value, from_json):
        assert from_text == other
        assert hash(from_text) == hash(other)

    assert len({from_text, from_value, from_json}) == 1
    assert from_text != BitString.from_bits("101010")
    assert BitString.from_int(1, 5) != BitString.from_int(1, 8)
    assert BitString(b"\x00\xff\x00", 16) == BitString(b"\xff\x00", 16)


def test_is_immutable():
    bits = BitString.from_bits("10101")
    with pytest.raises(FrozenInstanceError):
        bits.bit_length = 8
    with pytest.raises(FrozenInstanceError):
        bits.data = b"\xff"


def test_str_returns_the_bit_string():
    assert str(BitString.from_bits("10101")) == "10101"


def test_adapter_uses_neutral_type_and_base_class():
    adapter = BitsTextAdapter()
    assert isinstance(adapter, BaseSQLTypeAdapter)
    assert adapter.neutral_type is BitString


def test_text_adapter_round_trip():
    adapter = BitsTextAdapter()
    for bits in (
        BitString.from_bits("10101"),
        BitString.from_bits("0"),
        BitString.from_int(3, 8),
    ):
        stored = adapter.to_database(bits, str)
        assert isinstance(stored, str)
        assert stored == bits.to_bits()
        assert adapter.from_database(stored, BitString) == bits

    # Accepted input coercions: bit text and raw bytes.
    assert adapter.to_database("10101", str) == "10101"
    assert adapter.to_database(b"\xa8", str) == "10101000"


def test_bytes_adapter_round_trip_of_whole_bytes():
    adapter = RawBytesAdapter()
    for bits in (BitString.from_bytes(b"\x00"), BitString.from_bytes(b"\xff")):
        stored = adapter.to_database(bits, bytes)
        assert isinstance(stored, bytes)
        assert adapter.from_database(stored, BitString) == bits


def test_adapter_passes_none_through():
    adapter = BitsTextAdapter()
    assert adapter.to_database(None, str) is None
    assert adapter.from_database(None, BitString) is None


def test_adapter_wraps_encode_failures():
    adapter = BitsTextAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(BitString.from_bits("1"), int)
    message = str(excinfo.value)
    assert "Cannot convert BitString to BitString" in message
    assert "unsupported target type" in message


@pytest.mark.parametrize("value", ["102", "", "abc", "10 1"])
def test_adapter_wraps_invalid_python_values(value):
    adapter = BitsTextAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(value, str)
    assert "to BitString" in str(excinfo.value)


def test_adapter_wraps_unsupported_python_types():
    adapter = BitsTextAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(object(), str)
    assert "Cannot convert object to BitString" in str(excinfo.value)
    assert "expected BitString, a bit-string text, or bytes" in str(excinfo.value)


@pytest.mark.parametrize("value", ["102", "10 1", 1.5, {}, [1, 0]])
def test_adapter_wraps_decode_failures(value):
    adapter = BitsTextAdapter()
    with pytest.raises(TypeConversionError):
        adapter.from_database(value, BitString)


def test_adapter_rejects_non_neutral_decode_result():
    adapter = BrokenBitStringAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database("10101", BitString)
    assert "decoder must return BitString" in str(excinfo.value)


def test_tagged_json_codec_round_trip():
    assert BitString.json_type_tag == "bitstring"
    codec = AdapterJSONCodec(tagged=True)
    original = BitString.from_bits("101010101")

    encoded = json.loads(codec.dumps(original))
    assert encoded == {"__type__": "bitstring", "hex": "155", "bit_length": 9}

    restored = codec.loads(codec.dumps(original))
    assert isinstance(restored, BitString)
    assert restored == original
