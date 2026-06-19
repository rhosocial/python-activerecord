# src/rhosocial/activerecord/backend/expression/types/datetime_.py
"""Date/time SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class DateType(DataType):
    """DATE (year-month-day)."""

    def _default_sql(self) -> str:
        return "DATE"


class TimeType(DataType):
    """TIME[(p)] [WITHOUT TIME ZONE] — time of day (SQL standard)."""

    precision: Optional[int] = None

    def __init__(self, precision: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)

    def _default_sql(self) -> str:
        base = f"TIME({self.precision})" if self.precision is not None else "TIME"
        return base


class TimeTzType(DataType):
    """TIME[(p)] WITH TIME ZONE (SQL standard)."""

    precision: Optional[int] = None

    def __init__(self, precision: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)

    def _default_sql(self) -> str:
        base = f"TIME({self.precision})" if self.precision is not None else "TIME"
        return f"{base} WITH TIME ZONE"


class DateTimeType(DataType):
    """DATETIME — date + time (MySQL / SQLite)."""

    precision: Optional[int] = None

    def __init__(self, precision: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)

    def _default_sql(self) -> str:
        return f"DATETIME({self.precision})" if self.precision is not None else "DATETIME"


class TimestampType(DataType):
    """TIMESTAMP[(p)] [WITHOUT TIME ZONE] (SQL standard)."""

    precision: Optional[int] = None

    def __init__(self, precision: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)

    def _default_sql(self) -> str:
        base = f"TIMESTAMP({self.precision})" if self.precision is not None else "TIMESTAMP"
        return base


class TimestampTzType(DataType):
    """TIMESTAMP[(p)] WITH TIME ZONE (SQL standard, PostgreSQL)."""

    precision: Optional[int] = None

    def __init__(self, precision: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)

    def _default_sql(self) -> str:
        base = f"TIMESTAMP({self.precision})" if self.precision is not None else "TIMESTAMP"
        return f"{base} WITH TIME ZONE"


class IntervalType(DataType):
    """INTERVAL — time span (PostgreSQL / SQL standard)."""

    fields: Optional[str] = None  # e.g. 'YEAR', 'MONTH', 'DAY TO SECOND'

    def __init__(self, fields: Optional[str] = None, dialect=None):
        super().__init__(dialect)
        self.fields = fields

    def _type_params(self) -> tuple:
        return (self.fields,)

    def _default_sql(self) -> str:
        base = "INTERVAL"
        if self.fields:
            return f"{base} {self.fields}"
        return base
