# src/rhosocial/activerecord/backend/expression/types/datetime_.py
"""Date/time SQL types."""

from __future__ import annotations

import re
from typing import Optional

from ._base import DataType


class DateType(DataType):
    """DATE (year-month-day)."""

    name = "date"


class TimeType(DataType):
    """TIME[(p)] [WITHOUT TIME ZONE] — time of day (SQL standard)."""

    name = "time"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = ("precision",)

class TimeTzType(DataType):
    """TIME[(p)] WITH TIME ZONE (SQL standard)."""

    name = "timetz"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = ("precision",)

class DateTimeType(DataType):
    """DATETIME — date + time (MySQL / SQLite)."""

    name = "datetime"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = ("precision",)

class TimestampType(DataType):
    """TIMESTAMP[(p)] [WITHOUT TIME ZONE] (SQL standard)."""

    name = "timestamp"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = ("precision",)

class TimestampTzType(DataType):
    """TIMESTAMP[(p)] WITH TIME ZONE (SQL standard, PostgreSQL)."""

    name = "timestamptz"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = ("precision",)

#: The six fields an interval qualifier can name, in ascending resolution.
#: SQL:2016 gives an interval a *resolution*: either one field, or one field
#: ``TO`` a later one.  Enumerated rather than parsed because the set is
#: genuinely finite and small — six fields, thirteen combinations — which is the
#: whole argument for a closed list over a free string.
INTERVAL_FIELDS = ("YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND")

#: The thirteen qualifiers SQL:2016 defines: one field, or one field spanning to
#: a later one.  ``YEAR TO DAY`` is deliberately absent — the combinations are
#: contiguous ranges, not arbitrary pairs, and enumerating them is what makes an
#: impossible qualifier an error rather than a silently-rendered type.
INTERVAL_QUALIFIERS = frozenset({
    "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
    "YEAR TO MONTH",
    "DAY TO HOUR", "DAY TO MINUTE", "DAY TO SECOND",
    "HOUR TO MINUTE", "HOUR TO SECOND", "MINUTE TO SECOND",
})

#: A field with an optional leading precision, then an optional ``TO`` field
#: with its own.  Oracle writes ``DAY(2) TO SECOND(6)`` and PostgreSQL accepts
#: the same, so the precision belongs to the grammar; the *shape* it forms is
#: then checked against :data:`INTERVAL_QUALIFIERS`, so ``YEAR(3) TO DAY(9)``
#: is rejected on shape even though both fields parse.
_FIELD_ALTERNATION = "|".join(INTERVAL_FIELDS)
_INTERVAL_QUALIFIER_RE = re.compile(
    rf"^(?P<start>{_FIELD_ALTERNATION})"
    r"(?:\(\s*\d+\s*\))?"
    rf"(?:\s+TO\s+(?P<end>{_FIELD_ALTERNATION})"
    r"(?:\(\s*\d+\s*\))?)?$",
    re.IGNORECASE | re.ASCII,
)


class InvalidIntervalQualifierError(ValueError):
    """Raised when a string cannot be used as an SQL interval qualifier.

    A :class:`ValueError` for the same reason
    :class:`~...type_name.InvalidTypeNameError` is: the qualifier is rejected
    before any dialect is consulted, because the position it would occupy
    (``INTERVAL <qualifier>`` in DDL) cannot hold a bound parameter on any
    backend.
    """

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(
            f"{value!r} is not a SQL interval qualifier. A qualifier names the "
            f"resolution of the interval and is one field, or one field TO a "
            f"later one, each optionally with a leading precision: "
            f"{', '.join(sorted(INTERVAL_QUALIFIERS))} "
            f"(for example DAY(2) TO SECOND(6))."
        )


def is_valid_interval_qualifier(value: object) -> bool:
    """Whether *value* is an interval qualifier this package will render."""
    try:
        validate_interval_qualifier(value)
    except InvalidIntervalQualifierError:
        return False
    return True


def validate_interval_qualifier(value: object) -> str:
    """Return *value* when it is a usable interval qualifier, else raise.

    Returns the value unchanged (whitespace-stripped) so this can wrap a
    constructor argument, exactly as
    :func:`~...type_name.validate_type_name` does.

    Raises:
        InvalidIntervalQualifierError: If the qualifier is not one of the
            thirteen SQL:2016 qualifiers, with or without a leading precision.
    """
    if isinstance(value, str):
        candidate = value.strip()
        match = _INTERVAL_QUALIFIER_RE.match(candidate)
        if match is not None:
            shape = match.group("start").upper()
            if match.group("end") is not None:
                shape = f"{shape} TO {match.group('end').upper()}"
            if shape in INTERVAL_QUALIFIERS:
                return candidate
    raise InvalidIntervalQualifierError(value)


class IntervalQualifier(str):
    """A validated SQL interval qualifier.

    A ``str`` subclass, deliberately, and the reason is rendering. Three
    dialects interpolate ``fields`` straight into ``INTERVAL <fields>`` —
    Oracle (which also upper-cases it), PostgreSQL and the dummy dialect — so
    changing the *value type* from ``str`` to an ``enum.Enum`` would rewrite
    their output to ``INTERVAL IntervalField.YEAR`` and break every backend's
    DDL. Subclassing ``str`` keeps this additive: ``f"INTERVAL {q}"``,
    ``q.upper()``, ``q == "YEAR TO MONTH"``, ``json.dumps(q)`` and ``repr(q)``
    all behave exactly as they did, and equality, hashing and the ``PARAMETERS``
    identity tuple are untouched.

    What it buys is that the attribute can only ever *hold* a member of the
    closed vocabulary — an unchecked string in a DDL position is an injection,
    and a closed set is the same defence ``spelling`` uses for the same reason.
    """

    __slots__ = ()

    def __new__(cls, value: object) -> "IntervalQualifier":
        return super().__new__(cls, validate_interval_qualifier(value))


class IntervalType(DataType):
    """INTERVAL [qualifier] — a time span at a declared resolution.

    ``INTERVAL`` on its own is a span with no stated resolution; the qualifier
    is what says which fields it counts. It is a real part of the type rather
    than a decoration, because Oracle writes it: an unqualified ``IntervalType``
    renders ``INTERVAL DAY(2) TO SECOND(6)``, the qualifier Oracle means by a
    bare ``INTERVAL``, so that what is written is what the catalog reports back.

    The qualifier is drawn from :data:`INTERVAL_QUALIFIERS` — the thirteen SQL
    standard qualifiers — and validated by :class:`IntervalQualifier`, so an
    unknown qualifier raises :class:`InvalidIntervalQualifierError` naming it
    rather than becoming a string interpolated into DDL. Which qualifiers a
    backend *renders* is the backend's business; that the set is closed is
    core's.

    Renderers and ignorers, as of this change: Oracle, PostgreSQL and the dummy
    dialect interpolate ``fields``; SQLite renders interval as ``NUMERIC``
    because SQLite has no interval type at all and stores the value as a
    number, so its qualifier has nowhere to live; the remaining backends do not
    render interval at all and name a substitute through
    ``suggested_data_types()``.
    """

    name = "interval"

    fields: Optional[IntervalQualifier] = None

    def __init__(self, dialect=None, fields: Optional[str] = None,
                 ):
        super().__init__(dialect)
        # Validated here rather than in each rendering dialect: three formatters
        # interpolated this unchecked, and a per-formatter check is a
        # per-formatter bug waiting to happen.
        self.fields = None if fields is None else IntervalQualifier(fields)

    PARAMETERS = ("fields",)
