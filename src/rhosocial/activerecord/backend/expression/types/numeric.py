# src/rhosocial/activerecord/backend/expression/types/numeric.py
"""Floating-point and exact numeric SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType
from ._validation import (
    FLOAT_PRECISION_MAX,
    FLOAT_PRECISION_MIN,
    require_optional_range,
)


class FloatType(DataType):
    """FLOAT[(p)] — approximate numeric, variable precision."""

    # SQL standard: FLOAT precision is the binary mantissa bit count.
    PRECISION_MIN = FLOAT_PRECISION_MIN
    PRECISION_MAX = FLOAT_PRECISION_MAX

    precision: Optional[int] = None

    def __init__(self, dialect=None, *, precision: Optional[int] = None):
        super().__init__(dialect)
        self.precision = require_optional_range(
            precision, type(self).__name__, "precision", self.PRECISION_MIN, self.PRECISION_MAX
        )

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

    # SQL standard: precision >= 1; 0 <= scale <= precision. No standard
    # upper bound on precision (backends may set one via PRECISION_MAX).
    PRECISION_MIN = 1
    PRECISION_MAX: Optional[int] = None

    precision: Optional[int] = None
    scale: Optional[int] = None

    def __init__(self, dialect=None, *,
                 precision: Optional[int] = None, scale: Optional[int] = None):
        super().__init__(dialect)
        self.precision = require_optional_range(
            precision, type(self).__name__, "precision", self.PRECISION_MIN, self.PRECISION_MAX
        )
        self.scale = require_optional_range(
            scale, type(self).__name__, "scale", 0, self.precision if self.precision is not None else None
        )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision and self.scale == other.scale

    def __hash__(self) -> int:
        return hash((type(self), self.precision, self.scale))
