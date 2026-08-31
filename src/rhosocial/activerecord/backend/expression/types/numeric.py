# src/rhosocial/activerecord/backend/expression/types/numeric.py
"""Floating-point and exact numeric SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class FloatType(DataType):
    """FLOAT[(p)] — approximate numeric, variable precision."""

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


class RealType(DataType):
    """REAL — single-precision (4 bytes / 24-bit mantissa)."""


class DoubleType(DataType):
    """DOUBLE PRECISION — double-precision (8 bytes / 53-bit mantissa)."""


class DecimalType(DataType):
    """DECIMAL[(p[,s])] / NUMERIC[(p[,s])] — exact fixed-point."""

    precision: Optional[int] = None
    scale: Optional[int] = None

    def __init__(self, dialect=None, *,
                 precision: Optional[int] = None, scale: Optional[int] = None):
        super().__init__(dialect)
        self.precision = precision
        self.scale = scale

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision and self.scale == other.scale

    def __hash__(self) -> int:
        return hash((type(self), self.precision, self.scale))
