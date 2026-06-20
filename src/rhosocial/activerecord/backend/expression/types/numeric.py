# src/rhosocial/activerecord/backend/expression/types/numeric.py
"""Floating-point and exact numeric SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class FloatType(DataType):
    """FLOAT[(p)] — approximate numeric, variable precision.

    Note:
        In many backends ``REAL`` is a synonym of ``FLOAT(24)`` and
        ``DOUBLE PRECISION`` a synonym of ``FLOAT(53)``.  The canonical
        class for those is ``RealType`` / ``DoubleType``; they are not
        synonyms of ``FloatType``.
    """

    precision: Optional[int] = None

    def __init__(self, precision: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))

    def _default_sql(self) -> str:
        return f"FLOAT({self.precision})" if self.precision is not None else "FLOAT"


class RealType(DataType):
    """REAL — single-precision (4 bytes / 24-bit mantissa)."""

    def _default_sql(self) -> str:
        return "REAL"


class DoubleType(DataType):
    """DOUBLE PRECISION — double-precision (8 bytes / 53-bit mantissa)."""

    def _default_sql(self) -> str:
        return "DOUBLE PRECISION"


class DecimalType(DataType):
    """DECIMAL[(p[,s])] / NUMERIC[(p[,s])] — exact fixed-point."""

    precision: Optional[int] = None
    scale: Optional[int] = None

    def __init__(self, precision: Optional[int] = None,
                 scale: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision
        self.scale = scale

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision and self.scale == other.scale

    def __hash__(self) -> int:
        return hash((type(self), self.precision, self.scale))

    def _default_sql(self) -> str:
        if self.precision is not None and self.scale is not None:
            return f"DECIMAL({self.precision},{self.scale})"
        if self.precision is not None:
            return f"DECIMAL({self.precision})"
        return "DECIMAL"
