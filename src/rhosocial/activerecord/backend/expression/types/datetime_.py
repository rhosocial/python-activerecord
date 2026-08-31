# src/rhosocial/activerecord/backend/expression/types/datetime_.py
"""Date/time SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class DateType(DataType):
    """DATE (year-month-day)."""


class TimeType(DataType):
    """TIME[(p)] [WITHOUT TIME ZONE] — time of day (SQL standard)."""

    precision: Optional[int] = None

    def __init__(self, dialect=None, *, precision: Optional[int] = None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))


class TimeTzType(DataType):
    """TIME[(p)] WITH TIME ZONE (SQL standard)."""

    precision: Optional[int] = None

    def __init__(self, dialect=None, *, precision: Optional[int] = None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))


class DateTimeType(DataType):
    """DATETIME — date + time (MySQL / SQLite)."""

    precision: Optional[int] = None

    def __init__(self, dialect=None, *, precision: Optional[int] = None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))


class TimestampType(DataType):
    """TIMESTAMP[(p)] [WITHOUT TIME ZONE] (SQL standard)."""

    precision: Optional[int] = None

    def __init__(self, dialect=None, *, precision: Optional[int] = None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))


class TimestampTzType(DataType):
    """TIMESTAMP[(p)] WITH TIME ZONE (SQL standard, PostgreSQL)."""

    precision: Optional[int] = None

    def __init__(self, dialect=None, *, precision: Optional[int] = None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))


class IntervalType(DataType):
    """INTERVAL — time span (PostgreSQL / SQL standard)."""

    fields: Optional[str] = None  # e.g. 'YEAR', 'MONTH', 'DAY TO SECOND'

    def __init__(self, dialect=None, *, fields: Optional[str] = None):
        super().__init__(dialect)
        self.fields = fields

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.fields == other.fields

    def __hash__(self) -> int:
        return hash((type(self), self.fields))
