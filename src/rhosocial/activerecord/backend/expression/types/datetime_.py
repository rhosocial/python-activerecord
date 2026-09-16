# src/rhosocial/activerecord/backend/expression/types/datetime_.py
"""Date/time SQL types."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._base import DataType


class DateType(DataType):
    """DATE (year-month-day)."""

    name = "date"


class TimeType(DataType):
    """TIME[(p)] [WITHOUT TIME ZONE] — time of day (SQL standard)."""

    name = "time"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)


class TimeTzType(DataType):
    """TIME[(p)] WITH TIME ZONE (SQL standard)."""

    name = "timetz"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)


class DateTimeType(DataType):
    """DATETIME — date + time (MySQL / SQLite)."""

    name = "datetime"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)


class TimestampType(DataType):
    """TIMESTAMP[(p)] [WITHOUT TIME ZONE] (SQL standard)."""

    name = "timestamp"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)


class TimestampTzType(DataType):
    """TIMESTAMP[(p)] WITH TIME ZONE (SQL standard, PostgreSQL)."""

    name = "timestamptz"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)


class IntervalType(DataType):
    """INTERVAL — time span (PostgreSQL / SQL standard)."""

    name = "interval"

    fields: Optional[str] = None  # e.g. 'YEAR', 'MONTH', 'DAY TO SECOND'

    def __init__(self, dialect=None, fields: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.fields = fields

    def _type_params(self) -> tuple:
        return (self.fields,)
