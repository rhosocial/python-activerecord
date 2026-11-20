# tests/rhosocial/activerecord_test/feature/backend/adapters/test_mac_address.py
"""DB-free tests for the neutral MacAddress type and its adapter base."""

from dataclasses import FrozenInstanceError

import pytest

from rhosocial.activerecord.backend.adapters.network import (
    MacAddress,
    MacAddressAdapterBase,
)
from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter

EUI48_BYTES = bytes.fromhex("0123456789ab")
EUI48_TEXT = "01:23:45:67:89:ab"
EUI64_BYTES = bytes.fromhex("0123456789abcdef")
EUI64_TEXT = "01:23:45:67:89:ab:cd:ef"


class TextMacAdapter(MacAddressAdapterBase):
    """A backend-style adapter that speaks canonical text."""

    def _encode(self, mac, target_type, options):
        if target_type is not str:
            raise TypeError(f"unsupported target type {target_type!r}")
        return str(mac)

    def _decode(self, value, options):
        return MacAddress.parse(value)


class IntegerMacAdapter(MacAddressAdapterBase):
    """A backend-style adapter that speaks integers."""

    def _encode(self, mac, target_type, options):
        if target_type is not int:
            raise TypeError(f"unsupported target type {target_type!r}")
        return int.from_bytes(mac.octets, "big")

    def _decode(self, value, options):
        if isinstance(value, bool):
            raise TypeError("bool is not a valid database value")
        if isinstance(value, str):
            raise TypeError("does not accept text")
        return MacAddress.parse(value)


class BrokenMacAdapter(MacAddressAdapterBase):
    """Returns a non-neutral value from its decode hook."""

    def _encode(self, mac, target_type, options):
        return str(mac)

    def _decode(self, value, options):
        return str(value)


@pytest.mark.parametrize(
    "value, expected",
    [
        (EUI48_TEXT, EUI48_BYTES),
        ("01-23-45-67-89-AB", EUI48_BYTES),
        ("0123456789AB", EUI48_BYTES),
        ("0123.4567.89ab", EUI48_BYTES),
        ("01.23.45.67.89.ab", EUI48_BYTES),
        (EUI64_TEXT, EUI64_BYTES),
        ("01-23-45-67-89-ab-cd-ef", EUI64_BYTES),
        ("0123456789abcdef", EUI64_BYTES),
        ("0123.4567.89ab.cdef", EUI64_BYTES),
        ("01.23.45.67.89.ab.cd.ef", EUI64_BYTES),
        (b"\x01\x23\x45\x67\x89\xab", EUI48_BYTES),
        (bytearray(b"\x01\x23\x45\x67\x89\xab"), EUI48_BYTES),
        (MacAddress(EUI48_BYTES), EUI48_BYTES),
    ],
)
def test_parse_accepted_forms(value, expected):
    assert MacAddress.parse(value).octets == expected


@pytest.mark.parametrize(
    "value, expected_octets",
    [
        (0, bytes(6)),
        (1, bytes.fromhex("000000000001")),
        ((1 << 48) - 1, b"\xff" * 6),
        (1 << 48, bytes.fromhex("0001000000000000")),
        ((1 << 64) - 1, b"\xff" * 8),
    ],
)
def test_parse_int_chooses_eui_size(value, expected_octets):
    mac = MacAddress.parse(value)
    assert mac.octets == expected_octets
    assert int.from_bytes(mac.octets, "big") == value


@pytest.mark.parametrize(
    "value, exc_type",
    [
        ("", ValueError),
        ("   ", ValueError),
        ("01:23:45:67:89", ValueError),  # 5 octets
        ("01:23:45:67:89:ab:cd", ValueError),  # 7 octets
        ("01:23:45:67:89:ab:cd:ef:00", ValueError),  # 9 octets
        ("0123456789", ValueError),  # 10 hex digits
        ("0123456789abc", ValueError),  # 13 hex digits
        ("0g:23:45:67:89:ab", ValueError),  # non-hex char
        ("01:23-45:67:89:ab", ValueError),  # mixed separators
        ("01:23:45:67:89:", ValueError),  # empty group
        ("1:23:45:67:89:ab", ValueError),  # group too short
        ("01:234:45:67:89:ab", ValueError),  # inconsistent group width
        ("01.2345.67.89.ab", ValueError),  # inconsistent dot groups
        ("01.23.45.67.89", ValueError),  # dot form, 5 octets
        (-1, ValueError),
        (1 << 64, ValueError),
        (None, TypeError),
        (1.5, TypeError),
        (True, TypeError),
        ([1, 2, 3], TypeError),
    ],
)
def test_parse_rejects_invalid_values(value, exc_type):
    with pytest.raises(exc_type):
        MacAddress.parse(value)


@pytest.mark.parametrize(
    "value, exc_type",
    [
        ("0123456789ab", TypeError),
        (bytearray(b"\x01" * 7), ValueError),
        (b"\x01" * 5, ValueError),
        ("01:23:45:67:89:ab", TypeError),
        (None, TypeError),
    ],
)
def test_direct_construction_validates_octets(value, exc_type):
    with pytest.raises(exc_type):
        MacAddress(value)


def test_canonical_string_is_lowercase_colon_separated():
    assert str(MacAddress.parse("01-23-45-67-89-AB")) == EUI48_TEXT
    assert str(MacAddress.parse(EUI64_BYTES)) == EUI64_TEXT
    assert MacAddress.parse(EUI64_BYTES).to_json_value() == EUI64_TEXT


def test_is_immutable():
    mac = MacAddress(EUI48_BYTES)
    with pytest.raises(FrozenInstanceError):
        mac.octets = b"\x00" * 6


def test_equality_and_hash_use_normalized_octets():
    colon = MacAddress.parse(EUI48_TEXT)
    hyphen = MacAddress.parse("01-23-45-67-89-AB")
    compact = MacAddress.parse("0123456789ab")
    integer = MacAddress.parse(int.from_bytes(EUI48_BYTES, "big"))

    for other in (hyphen, compact, integer):
        assert colon == other
        assert hash(colon) == hash(other)
        assert len({colon, other}) == 1

    assert colon != MacAddress.parse(EUI64_BYTES)
    assert colon != EUI48_TEXT


def test_json_round_trip():
    for original in (MacAddress.parse(EUI48_TEXT), MacAddress.parse(EUI64_TEXT)):
        payload = original.to_json_value()
        assert isinstance(payload, str)
        assert payload == str(original)
        assert MacAddress.from_json_value(payload) == original


@pytest.mark.parametrize("value", [b"\x01", 1, None, ["01:23:45:67:89:ab"]])
def test_from_json_value_rejects_non_text(value):
    with pytest.raises(TypeError):
        MacAddress.from_json_value(value)


def test_from_json_value_rejects_malformed_text():
    with pytest.raises(ValueError):
        MacAddress.from_json_value("01:23:45:67:89")


def test_adapter_uses_neutral_type_and_base_class():
    adapter = TextMacAdapter()
    assert isinstance(adapter, BaseSQLTypeAdapter)
    assert adapter.neutral_type is MacAddress


def test_text_adapter_round_trip():
    adapter = TextMacAdapter()
    for mac in (MacAddress.parse(EUI48_TEXT), MacAddress.parse(EUI64_TEXT)):
        stored = adapter.to_database(mac, str)
        assert stored == str(mac)
        assert adapter.from_database(stored, MacAddress) == mac

    # Accepted input coercions: text, bytes, and int.
    assert adapter.to_database(EUI48_TEXT.upper(), str) == EUI48_TEXT
    assert adapter.to_database(EUI48_BYTES, str) == EUI48_TEXT
    assert adapter.to_database(int.from_bytes(EUI64_BYTES, "big"), str) == EUI64_TEXT


def test_integer_adapter_round_trip():
    adapter = IntegerMacAdapter()
    for mac in (MacAddress.parse(EUI48_TEXT), MacAddress.parse(EUI64_TEXT)):
        stored = adapter.to_database(mac, int)
        assert isinstance(stored, int)
        assert adapter.from_database(stored, MacAddress) == mac


def test_adapter_passes_none_through():
    adapter = TextMacAdapter()
    assert adapter.to_database(None, str) is None
    assert adapter.from_database(None, MacAddress) is None


def test_adapter_wraps_encode_failures():
    adapter = TextMacAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(MacAddress(EUI48_BYTES), int)
    message = str(excinfo.value)
    assert "Cannot convert MacAddress to int" in message
    assert "unsupported target type" in message


@pytest.mark.parametrize("value", ["not-a-mac", "01:23:45:67:89", b"\x01"])
def test_adapter_wraps_invalid_python_values(value):
    adapter = TextMacAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(value, str)
    assert "to MacAddress" in str(excinfo.value)


def test_adapter_wraps_unsupported_python_types():
    adapter = TextMacAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(object(), str)
    assert "Cannot convert object to MacAddress" in str(excinfo.value)
    assert "expected MacAddress, str, bytes, or int" in str(excinfo.value)


@pytest.mark.parametrize("value", ["not-a-mac", "01:23:45:67:89", 1.5, ["text"]])
def test_adapter_wraps_decode_failures(value):
    adapter = TextMacAdapter()
    with pytest.raises(TypeConversionError):
        adapter.from_database(value, MacAddress)


def test_adapter_rejects_non_neutral_decode_result():
    adapter = BrokenMacAdapter()
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database("01:23:45:67:89:ab", MacAddress)
    assert "decoder must return MacAddress" in str(excinfo.value)
