# src/rhosocial/activerecord/backend/adapters/bitstring.py
"""Neutral bit-string type and its adapter base.

This module provides a driver-independent representation of a bit sequence
(for example PostgreSQL ``BIT``/``VARBIT``, MySQL ``BIT``, or ``BINARY``
columns) plus a base adapter that backend adapters derive from. It depends
only on the standard library.

Bits are stored most-significant-bit first: the first ``bit_length`` bits of
``data`` are significant, and the bits after them are unused padding. Unused
bits are required to be zero, so a value has one canonical byte form (leading
zero bytes are trimmed). ``bit_length`` carries the leading-zero information
that the trimmed bytes alone cannot express.
"""

from abc import abstractmethod
from collections.abc import Mapping as ABCMapping
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Optional, Type

from ..errors import TypeConversionError
from ..type_adapter import BaseSQLTypeAdapter

_HEX_CHARS = frozenset("0123456789abcdefABCDEF")


def _bytes_for_bits(bit_length: int) -> int:
    """Number of bytes needed to hold ``bit_length`` bits."""
    return (bit_length + 7) // 8


@dataclass(frozen=True)
class BitString:
    """An immutable bit sequence.

    ``data`` holds the bits most-significant-bit first, and ``bit_length``
    (``1..len(data) * 8``) says how many leading bits are significant. The
    remaining low bits of ``data`` must be zero. Leading zero bytes are
    trimmed during construction, so equal bit sequences always produce equal
    (and equally hashable) instances.

    The string and integer helpers treat the significant bits as one binary
    number written most-significant-bit first: ``BitString.from_bits("10101")
    .to_int() == 21``.
    """

    #: Stable tag used by ``AdapterJSONCodec`` for tagged envelopes.
    json_type_tag: ClassVar[str] = "bitstring"

    data: bytes
    bit_length: int

    def __post_init__(self) -> None:
        if not isinstance(self.data, (bytes, bytearray)):
            raise TypeError(f"data must be bytes, got {type(self.data).__name__}")
        data = bytes(self.data)
        if isinstance(self.bit_length, bool) or not isinstance(self.bit_length, int):
            raise TypeError("bit_length must be int, " f"got {type(self.bit_length).__name__}")
        if not data:
            raise ValueError("data must contain at least one byte")
        if self.bit_length < 1:
            raise ValueError(f"bit_length must be at least 1, got {self.bit_length}")
        if self.bit_length > len(data) * 8:
            raise ValueError(
                f"bit_length {self.bit_length} exceeds the " f"{len(data) * 8} bits in data"
            )
        unused = len(data) * 8 - self.bit_length
        if unused and int.from_bytes(data, "big") & ((1 << unused) - 1):
            raise ValueError(f"the {unused} unused low bits of data must be zero")

        while len(data) > 1 and data[0] == 0 and self.bit_length <= (len(data) - 1) * 8:
            data = data[1:]
        object.__setattr__(self, "data", data)

    @classmethod
    def from_bits(cls, text: str) -> "BitString":
        """Build a bit string from text such as ``"10101"``."""
        if not isinstance(text, str):
            raise TypeError(f"bit string text must be str, got {type(text).__name__}")
        if not text:
            raise ValueError("bit string text must not be empty")
        if any(char not in "01" for char in text):
            raise ValueError("bit string text may only contain '0' and '1'")
        return cls.from_int(int(text, 2), len(text))

    @classmethod
    def from_int(cls, value: int, length: int) -> "BitString":
        """Build a ``length``-bit string from a non-negative integer.

        ``value`` is interpreted as a binary number written most-significant-
        bit first, so leading zeros are preserved by ``length``.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"value must be int, got {type(value).__name__}")
        if isinstance(length, bool) or not isinstance(length, int):
            raise TypeError(f"length must be int, got {type(length).__name__}")
        if value < 0:
            raise ValueError("value must be non-negative")
        if length < 1:
            raise ValueError(f"length must be at least 1, got {length}")
        if value >= 1 << length:
            raise ValueError(f"value {value} does not fit in {length} bits")

        size = _bytes_for_bits(length)
        unused = size * 8 - length
        return cls((value << unused).to_bytes(size, "big"), length)

    @classmethod
    def from_bytes(cls, value: bytes, bit_length: Optional[int] = None) -> "BitString":
        """Build a bit string from raw bits.

        ``bit_length`` defaults to ``len(value) * 8``. When a shorter length
        is given, the trailing bits of the last byte must be zero.
        """
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError(f"value must be bytes, got {type(value).__name__}")
        data = bytes(value)
        if not data:
            raise ValueError("bytes must not be empty")
        length = len(data) * 8 if bit_length is None else bit_length
        return cls(data, length)

    def to_bits(self) -> str:
        """Return the significant bits as a ``"0"``/``"1"`` string."""
        unused = len(self.data) * 8 - self.bit_length
        value = int.from_bytes(self.data, "big") >> unused
        return format(value, "b").zfill(self.bit_length)

    def to_int(self) -> int:
        """Return the significant bits as a non-negative integer."""
        unused = len(self.data) * 8 - self.bit_length
        return int.from_bytes(self.data, "big") >> unused

    def to_json_value(self) -> Dict[str, Any]:
        """Return the canonical JSON form.

        ``hex`` is lowercase, has no ``0x`` prefix, and drops leading zero
        nibbles; ``bit_length`` restores the leading zeros it drops.
        """
        return {"hex": format(self.to_int(), "x"), "bit_length": self.bit_length}

    @classmethod
    def from_json_value(cls, value: Any) -> "BitString":
        """Rebuild a :class:`BitString` from its JSON form.

        Accepts either the canonical mapping ``{"hex": ..., "bit_length": n}``
        or a plain hexadecimal string (whose ``bit_length`` is
        ``4 * len(hex)``).
        """
        if isinstance(value, str):
            return cls._from_hex(value, None)
        if isinstance(value, ABCMapping):
            try:
                hex_text = value["hex"]
                bit_length = value["bit_length"]
            except KeyError as exc:
                raise ValueError(f"BitString JSON value is missing field {exc}") from exc
            if not isinstance(hex_text, str):
                raise ValueError(
                    "BitString JSON field 'hex' must be str, " f"got {type(hex_text).__name__}"
                )
            if isinstance(bit_length, bool) or not isinstance(bit_length, int):
                raise ValueError(
                    "BitString JSON field 'bit_length' must be int, "
                    f"got {type(bit_length).__name__}"
                )
            return cls._from_hex(hex_text, bit_length)
        raise TypeError(
            "BitString JSON value must be a hex string or a mapping, " f"got {type(value).__name__}"
        )

    @classmethod
    def _from_hex(cls, text: str, bit_length: Optional[int]) -> "BitString":
        if not text:
            raise ValueError("hex must not be empty")
        if any(char not in _HEX_CHARS for char in text):
            raise ValueError("hex contains non-hexadecimal characters")

        value = int(text, 16)
        length = 4 * len(text) if bit_length is None else bit_length
        if length < 1:
            raise ValueError(f"bit_length must be at least 1, got {length}")
        if value >= 1 << length:
            raise ValueError(f"hex value {text!r} does not fit in {length} bits")
        return cls.from_int(value, length)

    def __str__(self) -> str:
        return self.to_bits()


class BitStringAdapterBase(BaseSQLTypeAdapter):
    """Base adapter for backends exposing bit strings.

    Backends derive from this class and implement :meth:`_encode` and
    :meth:`_decode`. Conversion failures raised by those hooks are wrapped in
    :class:`TypeConversionError` by the base class.

    A raw ``bytes`` target carries only whole bytes, so it is lossless only
    when ``bit_length`` is a multiple of 8; bit-varying columns must keep the
    bit length in their own metadata or a backend-specific text form.
    """

    neutral_type = BitString

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        bits = self._coerce_bitstring(value)
        try:
            return self._encode(bits, target_type, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc))

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        try:
            bits = self._decode(value, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc))

        if not isinstance(bits, BitString):
            self._conversion_error(
                value,
                "decoder must return BitString, " f"got {type(bits).__name__}",
            )
        return bits

    def _coerce_bitstring(self, value: Any) -> BitString:
        """Convert a supported Python value into a :class:`BitString`.

        Text other than ``"0"``/``"1"`` digits is rejected; hexadecimal text
        is accepted only by :meth:`BitString.from_json_value`.
        """
        if isinstance(value, BitString):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                return BitString.from_bytes(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, str(exc))
        if isinstance(value, str):
            try:
                return BitString.from_bits(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, str(exc))
        self._conversion_error(
            value,
            "expected BitString, a bit-string text, or bytes",
        )

    @abstractmethod
    def _encode(
        self,
        bits: BitString,
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        """Encode a neutral bit string into the backend/driver value."""
        raise NotImplementedError

    @abstractmethod
    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> BitString:
        """Decode a backend/driver value into a neutral bit string."""
        raise NotImplementedError
