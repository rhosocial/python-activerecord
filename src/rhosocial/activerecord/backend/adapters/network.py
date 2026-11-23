# src/rhosocial/activerecord/backend/adapters/network.py
"""Neutral network address types and their adapter bases.

This module provides driver-independent representations of a MAC address
(48-bit EUI-48 or 64-bit EUI-64) and of an IP address (IPv4 or IPv6), plus base
adapters that backend adapters derive from. It depends only on the standard
library: :class:`IPAddress` carries a standard-library ``ipaddress`` object so
parsing, validation and compression are the stdlib's, not a second
implementation.
"""

import ipaddress
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, Union

from ..errors import TypeConversionError
from ..type_adapter import BaseSQLTypeAdapter

_HEX_CHARS = frozenset("0123456789abcdefABCDEF")
_SEPARATORS = (":", "-", ".")
_EUI48_OCTETS = 6
_EUI64_OCTETS = 8
_MAX_EUI48 = (1 << (8 * _EUI48_OCTETS)) - 1
_MAX_EUI64 = (1 << (8 * _EUI64_OCTETS)) - 1


def _parse_text(text: str) -> bytes:
    """Parse text representations of a MAC address into octets."""
    text = text.strip()
    if not text:
        raise ValueError("MAC address text is empty")

    separators = [sep for sep in _SEPARATORS if sep in text]
    if len(separators) > 1:
        raise ValueError(f"MAC address must use a single separator, got {separators!r}")

    if not separators:
        if len(text) not in (12, 16):
            raise ValueError(
                "Compact MAC address must contain 12 or 16 hex digits, " f"got {len(text)}"
            )
        if not all(char in _HEX_CHARS for char in text):
            raise ValueError("MAC address contains non-hexadecimal characters")
        return bytes.fromhex(text)

    separator = separators[0]
    groups = text.split(separator)
    if any(not group for group in groups):
        raise ValueError("MAC address contains an empty group")

    if separator == ".":
        widths = {len(group) for group in groups}
        if widths not in ({2}, {4}):
            raise ValueError("Dot-separated MAC address must use uniformly 2- or 4-digit groups")
    else:
        if any(len(group) != 2 for group in groups):
            raise ValueError(
                f"{separator!r}-separated MAC address groups must have exactly 2 digits"
            )

    if not all(char in _HEX_CHARS for group in groups for char in group):
        raise ValueError("MAC address contains non-hexadecimal characters")

    octets = b"".join(bytes.fromhex(group) for group in groups)
    if len(octets) not in (_EUI48_OCTETS, _EUI64_OCTETS):
        raise ValueError("MAC address must have 6 or 8 octets, " f"got {len(octets)}")
    return octets


@dataclass(frozen=True)
class MacAddress:
    """A driver-independent MAC address (EUI-48 or EUI-64).

    ``octets`` holds 6 or 8 bytes in network (big-endian) order.
    """

    octets: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.octets, (bytes, bytearray)):
            raise TypeError(f"octets must be bytes, got {type(self.octets).__name__}")
        octets = bytes(self.octets)
        if len(octets) not in (_EUI48_OCTETS, _EUI64_OCTETS):
            raise ValueError("MAC address must have 6 or 8 octets, " f"got {len(octets)}")
        object.__setattr__(self, "octets", octets)

    @classmethod
    def parse(cls, value: Union[str, bytes, int, "MacAddress"]) -> "MacAddress":
        """Parse text, bytes, or an integer into a :class:`MacAddress`.

        Accepted text forms are colon- or hyphen-separated byte groups
        (``01:23:45:67:89:ab``), dot-separated groups (``0123.4567.89ab``
        or ``01.23.45.67.89.ab``), and compact hexadecimal
        (``0123456789ab``). ``bytes`` must already be 6 or 8 octets; an
        integer is interpreted with its bit length deciding between
        EUI-48 and EUI-64 (values above 2**48-1 become 8 octets).
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            raise TypeError("MAC address cannot be parsed from bool")
        if isinstance(value, int):
            if value < 0:
                raise ValueError("MAC address integer must be non-negative")
            if value > _MAX_EUI64:
                raise ValueError("MAC address integer must fit in 48 or 64 bits, " f"got {value}")
            octet_count = _EUI64_OCTETS if value > _MAX_EUI48 else _EUI48_OCTETS
            return cls(value.to_bytes(octet_count, "big"))
        if isinstance(value, (bytes, bytearray)):
            return cls(value)
        if isinstance(value, str):
            return cls(_parse_text(value))
        raise TypeError(
            "MAC address must be parsed from str, bytes, or int, " f"got {type(value).__name__}"
        )

    def __str__(self) -> str:
        """Return the canonical lowercase colon-separated form."""
        return ":".join(f"{octet:02x}" for octet in self.octets)

    def to_json_value(self) -> str:
        """Return the canonical string used for JSON serialization."""
        return str(self)

    @classmethod
    def from_json_value(cls, value: str) -> "MacAddress":
        """Rebuild a :class:`MacAddress` from its canonical JSON string."""
        if not isinstance(value, str):
            raise TypeError("MAC address JSON value must be str, " f"got {type(value).__name__}")
        return cls.parse(value)


class MacAddressAdapterBase(BaseSQLTypeAdapter):
    """Base adapter for backends exposing MAC addresses.

    Backends derive from this class and implement :meth:`_encode` and
    :meth:`_decode`. Conversion failures raised by those hooks are wrapped
    in :class:`TypeConversionError` by the base class.
    """

    neutral_type = MacAddress

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        mac = self._coerce_mac(value)
        try:
            return self._encode(mac, target_type, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc), target=target_type)

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        try:
            mac = self._decode(value, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc))

        if not isinstance(mac, MacAddress):
            self._conversion_error(
                value,
                "decoder must return MacAddress, " f"got {type(mac).__name__}",
            )
        return mac

    def _coerce_mac(self, value: Any) -> MacAddress:
        """Convert a supported Python value into a :class:`MacAddress`."""
        if isinstance(value, MacAddress):
            return value
        if isinstance(value, bool):
            self._conversion_error(value, "bool is not a valid MAC address input")
        if isinstance(value, (str, bytes, bytearray, int)):
            try:
                return MacAddress.parse(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, str(exc))
        self._conversion_error(
            value,
            "expected MacAddress, str, bytes, or int",
        )

    @abstractmethod
    def _encode(
        self,
        mac: MacAddress,
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        """Encode a neutral MAC address into the backend/driver value."""
        raise NotImplementedError

    @abstractmethod
    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> MacAddress:
        """Decode a backend/driver value into a neutral MAC address."""
        raise NotImplementedError


_IP_ADDRESS_TYPES = (ipaddress.IPv4Address, ipaddress.IPv6Address)


@dataclass(frozen=True)
class IPAddress:
    """A driver-independent IPv4 or IPv6 address.

    ``value`` holds a standard-library ``ipaddress.IPv4Address`` or
    ``IPv6Address``. The wrapper is a distinct framework type so it can be a
    key in the suggestion tables (the stdlib classes are *backend-neutral*
    value classes, not framework-committed types).
    """

    value: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]

    def __post_init__(self) -> None:
        if not isinstance(self.value, _IP_ADDRESS_TYPES):
            raise TypeError(
                "value must be ipaddress.IPv4Address or IPv6Address, "
                f"got {type(self.value).__name__}"
            )

    @property
    def version(self) -> int:
        """4 for IPv4, 6 for IPv6."""
        return self.value.version

    @classmethod
    def parse(cls, value: Union[str, bytes, int, "IPAddress", Any]) -> "IPAddress":
        """Parse text, packed bytes, an integer, or a stdlib address object.

        ``str`` is parsed by ``ipaddress.ip_address``; ``bytes`` of length 4 or
        16 is unpacked; an ``int`` is interpreted by ``ipaddress.ip_address``;
        a stdlib address (or an existing :class:`IPAddress`) is passed through.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, _IP_ADDRESS_TYPES):
            return cls(value)
        if isinstance(value, bool):
            raise TypeError("IP address cannot be parsed from bool")
        if isinstance(value, bytes):
            value = ipaddress.ip_address(value)
        elif isinstance(value, str):
            value = ipaddress.ip_address(value.strip())
        elif isinstance(value, int):
            value = ipaddress.ip_address(value)
        if isinstance(value, _IP_ADDRESS_TYPES):
            return cls(value)
        raise TypeError(
            "IP address must be parsed from str, bytes, int, or an ipaddress "
            f"object, got {type(value).__name__}"
        )

    def __str__(self) -> str:
        """Return the canonical compressed text form."""
        return str(self.value)

    def to_json_value(self) -> str:
        """Return the canonical string used for JSON serialization."""
        return str(self)

    @classmethod
    def from_json_value(cls, value: str) -> "IPAddress":
        """Rebuild an :class:`IPAddress` from its canonical JSON string."""
        if not isinstance(value, str):
            raise TypeError("IP address JSON value must be str, " f"got {type(value).__name__}")
        return cls.parse(value)


class IPAddressAdapterBase(BaseSQLTypeAdapter):
    """Base adapter for backends exposing IP addresses.

    Backends derive from this class and implement :meth:`_encode` and
    :meth:`_decode`. Conversion failures from those hooks are wrapped in
    :class:`TypeConversionError` by the base class.
    """

    neutral_type = IPAddress

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        ip_addr = self._coerce_ip(value)
        try:
            return self._encode(ip_addr, target_type, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc), target=target_type)

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        try:
            ip_addr = self._decode(value, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc))

        if not isinstance(ip_addr, IPAddress):
            self._conversion_error(
                value,
                "decoder must return IPAddress, " f"got {type(ip_addr).__name__}",
            )
        return ip_addr

    def _coerce_ip(self, value: Any) -> IPAddress:
        """Convert a supported Python value into an :class:`IPAddress`."""
        if isinstance(value, IPAddress):
            return value
        if isinstance(value, bool):
            self._conversion_error(value, "bool is not a valid IP address input")
        if isinstance(value, (str, bytes, bytearray, int)) or isinstance(
            value, _IP_ADDRESS_TYPES
        ):
            try:
                return IPAddress.parse(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, str(exc))
        self._conversion_error(
            value,
            "expected IPAddress, str, bytes, int, or an ipaddress object",
        )

    @abstractmethod
    def _encode(
        self,
        ip_addr: IPAddress,
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        """Encode a neutral IP address into the backend/driver value."""
        raise NotImplementedError

    @abstractmethod
    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> IPAddress:
        """Decode a backend/driver value into a neutral IP address."""
        raise NotImplementedError
