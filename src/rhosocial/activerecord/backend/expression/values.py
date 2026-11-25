# src/rhosocial/activerecord/backend/expression/values.py
"""The closed vocabulary of value kinds (catalog §3.3, wire §5).

A value that reaches SQL is carried by :class:`~.core.Literal`, which answers
one question -- whether that value binds or is written as text -- and nothing
else. What kind of value it is is a separate question, and this module is its
answer: a closed set, because the set of things a bind parameter can hold is
closed.

===========================  ==========================  =======================
stage                        form                       who converts
===========================  ==========================  =======================
:class:`Literal` ``value``   host value                 the caller
the artifact                 canonical spelling         :func:`LiteralKind.pack`
the parameter sequence       host value                 nobody -- it is what
                                                    the driver binds
===========================  ==========================  =======================

So an artifact carries the kind as ``{"kind": "date_value", "params":
{"value": "2026-10-17"}}`` and a Python ``date`` is its host form. Why the
spelling rather than the host value: spec 4.8 requires the artifact to be
language-neutral, so a Python ``date`` and a Go ``time.Time`` must serialize
identically. That constraint lands here, on the pack/unpack pair, which is
where it belongs.

There is no class per value type and there is no node per value type. One node
carries every value, so the twelve classes this used to have would each have
restated the same two things -- the host type, and the dialect method that
spells it -- on a node that had nothing else to do.

Why the spelling is not a free choice at the call site: the artifact must be
readable by a reader that has a different set of host types, so the conversion
is declared once per kind rather than left to each caller.
"""

import base64
import datetime
import decimal
import enum
import math
import uuid
from typing import Any, Callable, Dict, Optional

#: ISO 8601 duration, reduced to what ``timedelta`` can hold: days, hours,
#: minutes, seconds and an optional fraction. Years and months are refused --
#: their length is not a constant, so a timedelta cannot carry them honestly.
_TIME_COMPONENTS = (
    ("hours", "H"),
    ("minutes", "M"),
    ("seconds", "S"),
)


def _scan_decimal_digits(text: str, index: int) -> int:
    """Index past the run of decimal digits beginning at *index*."""
    while index < len(text) and text[index].isdecimal():
        index += 1
    return index


def _consume_time_component(text: str, index: int, stage: int):
    """Read the time component of *stage* at *index*, or ``None``.

    Stages run hours, minutes, seconds, so ``PT1M`` is a minute and ``PT1H1M``
    reads both. Only seconds take a fraction. The returned triple is the
    component's field name, its text, and the index after its suffix.
    """
    name, suffix = _TIME_COMPONENTS[stage]
    digits_start = index
    index = _scan_decimal_digits(text, index)
    if index == digits_start:
        return None
    value = text[digits_start:index]
    if name == "seconds" and index < len(text) and text[index] == ".":
        fraction_start = index + 1
        fraction_end = _scan_decimal_digits(text, fraction_start)
        if fraction_end == fraction_start:
            return None
        value = text[digits_start:fraction_end]
        index = fraction_end
    if index < len(text) and text[index] == suffix:
        return name, value, index + 1
    return None


def _duration_fields(text: str) -> Optional[Dict[str, Optional[str]]]:
    """The components *text* spells as an ISO 8601 duration, or ``None``.

    The grammar is ``-?P``, an optional ``[days]D``, then optionally ``T``
    followed by any of ``[hours]H``, ``[minutes]M`` and ``[seconds]S`` in that
    order. Each component may be absent, but a component that is present must
    sit in its own slot, which is why the scan retries a digit run against the
    later slots instead of refusing it outright.
    """
    index = 0
    if text.startswith("-"):
        index = 1
    if not text.startswith("P", index):
        return None
    index += 1
    fields: Dict[str, Optional[str]] = {
        "days": None,
        "hours": None,
        "minutes": None,
        "seconds": None,
    }

    days_start = index
    index = _scan_decimal_digits(text, index)
    if index > days_start:
        if index >= len(text) or text[index] != "D":
            return None
        fields["days"] = text[days_start:index]
        index += 1

    if index < len(text) and text[index] == "T":
        index += 1
        stage = 0
        while stage < len(_TIME_COMPONENTS):
            component = _consume_time_component(text, index, stage)
            if component is None:
                if index >= len(text) or not text[index].isdecimal():
                    break
                stage += 1
                continue
            name, value, index = component
            fields[name] = value
            stage += 1

    return fields if index == len(text) else None


def _parse_duration(text: str) -> datetime.timedelta:
    """``"P1DT2H3M4.5S"`` -> timedelta, or a refusal naming what it cannot hold."""
    parts = _duration_fields(text)
    if parts is None:
        raise ValueError(
            f"{text!r} is not an ISO 8601 duration this implementation can "
            f"carry. Years and months have no fixed length, so they cannot "
            f"become a timedelta; use a day/hour/minute/second form."
        )
    delta = datetime.timedelta(
        days=int(parts["days"] or 0),
        hours=int(parts["hours"] or 0),
        minutes=int(parts["minutes"] or 0),
        seconds=float(parts["seconds"] or 0),
    )
    return -delta if text.startswith("-") else delta


def _pack_duration(value: datetime.timedelta) -> str:
    """``timedelta`` -> ISO 8601, empty parts omitted."""
    total = value.total_seconds()
    sign = "-" if total < 0 else ""
    days, rest = divmod(abs(total), 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    out = [sign, "P"]
    if days:
        out.append(f"{int(days)}D")
    if hours or minutes or seconds or len(out) == 2:
        out.append("T")
        if hours:
            out.append(f"{int(hours)}H")
        if minutes:
            out.append(f"{int(minutes)}M")
        if seconds or (not hours and not minutes):
            text = f"{seconds:.6f}".rstrip("0").rstrip(".")
            out.append(f"{text or '0'}S")
    return "".join(out)


def _identity(value: Any) -> Any:
    """A host type JSON already carries: ``int``, ``bool``, ``str``, ``None``."""
    return value


def _unpack_float(payload: Any) -> Any:
    """A JSON number read back as a float.

    Non-finite is refused, and not because the value is somehow invalid -- it is
    an ordinary member of the float type. It is refused because ``float_value``
    is the kind for a number *JSON* can carry, and these three are exactly what
    JSON's number grammar leaves out (RFC 8259). They have kinds of their own
    (:attr:`LiteralKind.NAN`, :attr:`LiteralKind.INFINITY`), so one arriving here
    is a payload that contradicts its own kind.

    A non-number is refused for that reason plus one: it would bind as a string
    and surface as a database error somewhere else entirely, naming neither the
    artifact nor the position.
    """
    if isinstance(payload, bool) or not isinstance(payload, (int, float)):
        raise ValueError(f"float_value must carry a JSON number, got {payload!r}")
    if math.isnan(payload) or math.isinf(payload):
        raise ValueError(
            f"float_value cannot carry {payload!r}: JSON has no literal for a "
            "non-finite number (RFC 8259). It has a kind of its own -- "
            "nan_value or infinity_value -- which travels as text."
        )
    return float(payload)


def _pack_infinity(value: Any) -> Any:
    """An infinity, as the text naming which way it points.

    The sign is the whole content of the value, so it is spelled rather than
    left to be inferred: ``"+inf"`` is not a JSON number either, and writing a
    bare ``Infinity`` would put the same problem back one level up.
    """
    return "+inf" if value > 0 else "-inf"


def _unpack_infinity(payload: Any) -> Any:
    """``"+inf"`` / ``"-inf"`` back to the float they name."""
    if payload == "+inf":
        return float("inf")
    if payload == "-inf":
        return float("-inf")
    raise ValueError(f"infinity_value must be '+inf' or '-inf', got {payload!r}")


class LiteralKind(enum.Enum):
    """One value type: its wire kind, its host type, and the two conversions.

    A member states four things and no more, and each of them is forced by the
    others. ``wire`` is the kind string that goes into an artifact (spec 4.11.1
    -- part of the wire contract, so it cannot drift). ``host`` is the type a
    bind parameter of this kind carries, and it is what :meth:`of` matches
    against. ``pack`` turns the host value into what JSON can carry, and
    ``unpack`` turns it back; the default pair is the identity, because a
    value whose host type *is* a JSON scalar needs no conversion.

    The order of the members is the order :meth:`of` tries them, and it is not
    cosmetic -- two host types are subclasses of another, so the narrower one
    has to be tried first or the broader one claims it. ``bool`` is an ``int``
    subclass, so ``BOOLEAN`` precedes ``INTEGER`` and every ``True`` reads back
    as itself rather than as ``1``. ``datetime`` is a ``date`` subclass, so
    ``TIMESTAMP`` precedes ``DATE``. With one class per kind, as this module
    used to have, no such order existed to get wrong; an enum makes the
    matching positional and so has to say which way round it goes.

    ``LIST`` and ``TUPLE`` are here because a literal really does carry them:
    ``IN`` takes a value list and renders one placeholder per member, so the
    list is the value at that position rather than a container around one. The
    two are separate kinds because JSON draws no distinction between an array
    and a tuple and the artifact must (§4.8) -- they are told apart on the way
    back by the kind, which is the whole reason a kind is worth having.
    """

    NULL = ("null_value", type(None), None, None, _identity, _identity)
    BOOLEAN = ("boolean_value", bool, None, None, _identity, _identity)
    INTEGER = ("integer_value", int, None, None, _identity, _identity)
    FLOAT = ("float_value", float, None, None, _identity, _unpack_float)
    # The two members of the float type JSON's number grammar leaves out. They
    # are not errors and not edge cases -- IEEE 754 defines them and a Decimal
    # has them -- so they are carried, each in its own kind, as text. Putting
    # them in float_value would mean a payload that is not the number its kind
    # promises; dropping them would mean losing part of the type.
    NAN = ("nan_value", float, None, None, lambda _value: "nan",
           lambda _text: float("nan"))
    INFINITY = ("infinity_value", float, None, None, _pack_infinity, _unpack_infinity)
    DECIMAL = (
        "decimal_value",
        decimal.Decimal,
        None,
        None,
        # A Decimal travels as a string: binary floating point cannot carry its
        # precision, and an artifact must not round a money value.
        str,
        lambda text: decimal.Decimal(text),
    )
    STRING = ("string_value", str, None, None, _identity, _identity)
    BINARY = (
        "binary_value",
        (bytes, bytearray),
        None,
        None,
        # Base64 is text, so the wire form is a JSON string. It used to be
        # ``{"__b64__": "..."}`` -- a wrapper around that same string, carrying
        # nothing the kind was not already saying, and something every language
        # would have had to reimplement in order to read it back.
        lambda value: base64.b64encode(bytes(value)).decode("ascii"),
        lambda text: base64.b64decode(text),
    )
    TIMESTAMP = (
        "timestamp_value",
        datetime.datetime,
        None,
        None,
        lambda value: value.isoformat(sep=" "),
        # Naive and aware are both ``datetime``; the distinction lives in
        # ``tzinfo`` and the spelling keeps the offset. This never adds ``Z``
        # and never reinterprets a naive value in some other zone.
        lambda text: datetime.datetime.fromisoformat(text),
    )
    DATE = (
        "date_value",
        datetime.date,
        None,
        None,
        lambda value: value.isoformat(),
        lambda text: datetime.date.fromisoformat(text),
    )
    TIME = (
        "time_value",
        datetime.time,
        None,
        None,
        lambda value: value.isoformat(),
        lambda text: datetime.time.fromisoformat(text),
    )
    INTERVAL = (
        "interval_value",
        datetime.timedelta,
        None,
        None,
        # ISO 8601 is text, so the wire form is a JSON string. The entry stays
        # wide and a bare number still reads as seconds -- the only unit a plain
        # scalar can name -- while what gets *written* is always the string, so
        # the artifact holds one normalised type (§10: wide in, normalised out).
        _pack_duration,
        lambda payload: _parse_duration(payload)
        if isinstance(payload, str)
        else datetime.timedelta(seconds=float(payload)),
    )
    LIST = ("list_value", list, None, None, list, list)
    TUPLE = ("tuple_value", tuple, None, None, list, tuple)
    UUID = (
        "uuid_value",
        uuid.UUID,
        None,
        None,
        str,
        # Every spelling names one value: hyphenated, plain hex, any case, the
        # ``0x`` form. Widening here is a compatibility question -- external
        # sources write all four -- not a semantic one.
        lambda text: uuid.UUID(text),
    )

    def __init__(
        self,
        wire: str,
        host: Any,
        _formatter: Optional[str],
        _unused: Optional[str],
        pack: Callable[[Any], Any],
        unpack: Callable[[Any], Any],
    ):
        self._value_ = wire
        self.host = host
        self._pack = pack
        self._unpack = unpack

    @property
    def wire(self) -> str:
        """The kind string this value type writes into an artifact."""
        return self._value_

    @classmethod
    def of(cls, value: Any) -> "LiteralKind":
        """The kind *value* belongs to, by its host type.

        This is the one place a bare host value names its own kind, and it is
        total over the closed set above. A value outside the set is refused by
        name rather than guessed at: a bind parameter carrying something this
        package does not know how to write has no artifact, and inventing one
        would put an unreadable value on the wire.
        """
        return cls._refine(cls._by_host(value), value)

    @classmethod
    def _by_host(cls, value: Any) -> "LiteralKind":
        for member in cls:
            if isinstance(value, member.host):
                return member
        raise TypeError(
            f"{type(value).__name__} is not one of the value kinds this "
            f"package can write: "
            + ", ".join(m.wire for m in cls)
            + ". Implement SQLLiteral on the type for inline rendering, and "
            "give it its own artifact shape if it must travel."
        )

    @classmethod
    def match(cls, value: Any) -> Optional["LiteralKind"]:
        """The kind *value* belongs to, or ``None`` if it belongs to none.

        The difference from :meth:`of` is who gets to be told "no". A literal
        that carries a type the dialect constructs itself -- a ``Point``, an
        ``inet``, anything implementing :class:`~...bases.SQLLiteral` -- still
        renders, and refusing to build it would refuse SQL the backend can
        write. So building asks :meth:`match`, and refusing is left to
        serialization, which is the layer that actually cannot proceed.
        """
        for member in cls:
            if isinstance(value, member.host):
                return cls._refine(member, value)
        return None

    @classmethod
    def _refine(cls, member: "LiteralKind", value: Any) -> "LiteralKind":
        """Separate the non-finite floats from the rest, which share one type.

        ``isinstance`` cannot do this and no amount of reordering will: NaN and
        both infinities *are* floats, so all four arrive as the same host type.
        The kind table matches on type everywhere else, so this is the one place
        that also looks at the value -- and it is worth the exception, because
        the alternative is a kind whose payload contradicts its own name.

        The membership is decided once, here, and read back through the same
        function on the way in, so a value written as ``nan_value`` comes back
        as a NaN and not as some other float.
        """
        if member is cls.FLOAT:
            if math.isnan(value):
                return cls.NAN
            if math.isinf(value):
                return cls.INFINITY
        return member

    @classmethod
    def by_wire(cls, wire: str) -> "LiteralKind":
        """The kind an artifact's ``kind`` names."""
        for member in cls:
            if member.wire == wire:
                return member
        raise ValueError(f"{wire!r} is not a known value kind")

    def pack(self, value: Any) -> Any:
        """*value* as JSON carries it, given it is this kind."""
        return self._pack(value)

    def unpack(self, payload: Any) -> Any:
        """A packed payload as the host value this kind carries."""
        return self._unpack(payload)

    def __str__(self) -> str:
        return self.wire


__all__ = ["LiteralKind", "_parse_duration", "_pack_duration"]