# src/rhosocial/activerecord/backend/dialect/protocols/query/timestamp.py
"""Timestamp precision, and nothing else.

The switch here is about precision rather than about whether date and time
functions exist at all: a fraction of a second is stored differently depending
on the engine, and only some of them keep it to microseconds.

The date/time *operations* -- arithmetic, extraction, truncation -- live
elsewhere, in ``DateTimeMixin`` on the column side and in each dialect's own
formatters, so nothing about them belongs in this protocol.

It is named for what it declares. It used to be ``DateTimeSupport``, which read
as "this dialect supports date-time operations" and so invited exactly the
wrong additions; ``TimestampSupport`` names the precision question it asks.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class TimestampSupport(Protocol):
    """Whether an engine's timestamp keeps microseconds."""

    def supports_microsecond_timestamp(self) -> bool:
        """Whether a timestamp keeps microseconds.

        Engines differ: PostgreSQL does, MySQL only in some types, SQL Server
        rounds to 100ns increments. An engine that rounds needs the fraction
        formatted to match, so the value is declared rather than assumed.
        """
        ...  # pragma: no cover
