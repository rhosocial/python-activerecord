# src/rhosocial/activerecord/backend/expression/types/numeric.py
"""Floating-point and exact numeric SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class FloatType(DataType):
    """FLOAT[(p)] — approximate numeric, variable precision."""

    name = "float"

    precision: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)


class RealType(DataType):
    """REAL — single-precision (4 bytes / 24-bit mantissa)."""

    name = "real"


class DoubleType(DataType):
    """DOUBLE PRECISION — double-precision (8 bytes / 53-bit mantissa)."""

    name = "double"


class DecimalType(DataType):
    """DECIMAL[(p[,s])] / NUMERIC[(p[,s])] — exact fixed-point."""

    name = "decimal"

    precision: Optional[int] = None
    scale: Optional[int] = None

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 scale: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.precision = precision
        self.scale = scale

    def _type_params(self) -> tuple:
        return (self.precision, self.scale)
