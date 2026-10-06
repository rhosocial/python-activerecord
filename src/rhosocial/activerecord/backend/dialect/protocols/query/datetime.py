# src/rhosocial/activerecord/backend/dialect/protocols/query/datetime.py
"""Date and time arithmetic and extraction.

The switches here are about precision rather than about whether date and time
functions exist at all: a fraction of a second is stored differently
depending on the engine, and only some of them keep it to microseconds.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class DateTimeSupport(Protocol):
    """Date and time expression support."""

    def supports_microsecond_timestamp(self) -> bool:
        """Whether a timestamp keeps microseconds.

        Engines differ: PostgreSQL does, MySQL only in some types, SQL Server
        rounds to 100ns increments. An engine that rounds needs the fraction
        formatted to match, so the value is declared rather than assumed.
        """
        ...  # pragma: no cover
