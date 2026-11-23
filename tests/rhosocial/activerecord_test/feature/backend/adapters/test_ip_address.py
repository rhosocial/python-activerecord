# tests/rhosocial/activerecord_test/feature/backend/adapters/test_ip_address.py
"""DB-free tests for the neutral IPAddress type and its adapter base."""

import ipaddress
from dataclasses import FrozenInstanceError

import pytest

from rhosocial.activerecord.backend.adapters.network import (
    IPAddress,
    IPAddressAdapterBase,
)
from rhosocial.activerecord.backend.errors import TypeConversionError


class TextIPAdapter(IPAddressAdapterBase):
    """A backend-style adapter that speaks canonical text."""

    def _encode(self, ip_addr, target_type, options):
        if target_type is not str:
            raise TypeError(f"unsupported target type {target_type!r}")
        return str(ip_addr)

    def _decode(self, value, options):
        return IPAddress.parse(value)


class BrokenIPAdapter(IPAddressAdapterBase):
    """Returns a non-neutral value from its decode hook."""

    def _encode(self, ip_addr, target_type, options):
        return str(ip_addr)

    def _decode(self, value, options):
        return str(value)


@pytest.mark.parametrize(
    "text, version",
    [
        ("192.0.2.1", 4),
        ("2001:db8::1", 6),
        ("::1", 6),
        ("0.0.0.0", 4),
    ],
)
def test_parse_text(text, version):
    ip = IPAddress.parse(text)
    assert ip.value == ipaddress.ip_address(text)
    assert ip.version == version
    assert str(ip) == text


def test_parse_packed_bytes():
    assert IPAddress.parse(bytes([192, 0, 2, 1])) == IPAddress.parse("192.0.2.1")


def test_parse_integer():
    assert IPAddress.parse(0xC0000201) == IPAddress.parse("192.0.2.1")


def test_parse_stdlib_object_and_passthrough():
    std = ipaddress.ip_address("2001:db8::1")
    assert IPAddress.parse(std).value == std
    ip = IPAddress.parse(std)
    assert IPAddress.parse(ip) is ip


def test_frozen():
    ip = IPAddress.parse("192.0.2.1")
    with pytest.raises(FrozenInstanceError):
        ip.value = ipaddress.ip_address("192.0.2.2")


@pytest.mark.parametrize("bad", ["", "999.1.1.1", "not-an-ip", 3.14, True])
def test_parse_rejects_invalid(bad):
    with pytest.raises((TypeError, ValueError)):
        IPAddress.parse(bad)


def test_json_roundtrip():
    ip = IPAddress.parse("2001:db8::1")
    assert IPAddress.from_json_value(ip.to_json_value()) == ip


def test_adapter_roundtrip():
    adapter = TextIPAdapter()
    for text in ("192.0.2.1", "2001:db8::1"):
        encoded = adapter.to_database(IPAddress.parse(text), str)
        decoded = adapter.from_database(encoded, IPAddress)
        assert decoded == IPAddress.parse(text)


def test_broken_decoder_is_rejected():
    adapter = BrokenIPAdapter()
    with pytest.raises(TypeConversionError):
        adapter.from_database("192.0.2.1", IPAddress)
