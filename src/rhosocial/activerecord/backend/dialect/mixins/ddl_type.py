# src/rhosocial/activerecord/backend/dialect/mixins/ddl_type.py
"""Default ``format_data_type()`` implementation for all core SQL types."""

from typing import ClassVar, List, Tuple, Type

from ...expression.types._base import DataType
from ...expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    CustomType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntType,
    IntegerType,
    IntervalType,
    JsonBType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
)


class DDLTypeMixin:
    """Mixin providing a default ``format_data_type()`` implementation.

    This mixin renders ``DataType`` value objects into their canonical SQL
    type strings.  The default implementation uses ``isinstance`` dispatch
    via a ``_SIMPLE_TYPES`` list for parameterless types (e.g.
    ``IntegerType`` → ``"INTEGER"``) and delegates parameterised types to
    dedicated ``_format_<ClassName>`` methods.

    Backend dialects should inherit from this mixin and may override either
    ``format_data_type()`` entirely or individual ``_format_*`` methods for
    backend-specific SQL output.
    """

    _SIMPLE_TYPES: ClassVar[List[Tuple[Type[DataType], str]]] = [
        (TinyIntType, "TINYINT"),
        (SmallIntType, "SMALLINT"),
        (IntType, "INT"),
        (IntegerType, "INTEGER"),
        (BigIntType, "BIGINT"),
        (RealType, "REAL"),
        (DoubleType, "DOUBLE PRECISION"),
        (TextType, "TEXT"),
        (BooleanType, "BOOLEAN"),
        (BlobType, "BLOB"),
        (DateType, "DATE"),
        (JsonType, "JSON"),
        (JsonBType, "JSONB"),
    ]

    def format_data_type(self, data_type: DataType) -> str:
        for type_class, sql in self._get_simple_types():
            if isinstance(data_type, type_class):
                return sql
        method = getattr(
            self, f"_format_{type(data_type).__name__}", None
        )
        if method is not None:
            return method(data_type)
        raise ValueError(
            f"Unsupported data type: {type(data_type).__name__}. "
            f"The dialect does not know how to render this type."
        )

    def _get_simple_types(self) -> List[Tuple[Type[DataType], str]]:
        """Return the list of simple (no-parameter) type mappings.

        Backends may override this method to add, reorder, or replace
        entries without touching ``format_data_type()`` itself.
        """
        return list(self._SIMPLE_TYPES)

    # ------------------------------------------------------------------
    # Parameterised type formatters
    #
    # Each handles a single DataType subclass that carries instance
    # parameters (length, precision, etc.).  Backends may override any
    # of these for dialect-specific output.
    # ------------------------------------------------------------------

    @staticmethod
    def _format_CharType(data_type: CharType) -> str:
        return f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"

    @staticmethod
    def _format_VarCharType(data_type: VarCharType) -> str:
        return f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"

    @staticmethod
    def _format_FloatType(data_type: FloatType) -> str:
        return f"FLOAT({data_type.precision})" if data_type.precision is not None else "FLOAT"

    @staticmethod
    def _format_DecimalType(data_type: DecimalType) -> str:
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision},{data_type.scale})"
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})"
        return "DECIMAL"

    @staticmethod
    def _format_TimeType(data_type: TimeType) -> str:
        return f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"

    @staticmethod
    def _format_TimeTzType(data_type: TimeTzType) -> str:
        base = f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"
        return f"{base} WITH TIME ZONE"

    @staticmethod
    def _format_DateTimeType(data_type: DateTimeType) -> str:
        return f"DATETIME({data_type.precision})" if data_type.precision is not None else "DATETIME"

    @staticmethod
    def _format_TimestampType(data_type: TimestampType) -> str:
        return f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"

    @staticmethod
    def _format_TimestampTzType(data_type: TimestampTzType) -> str:
        base = f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"
        return f"{base} WITH TIME ZONE"

    @staticmethod
    def _format_IntervalType(data_type: IntervalType) -> str:
        base = "INTERVAL"
        if data_type.fields:
            return f"{base} {data_type.fields}"
        return base

    @staticmethod
    def _format_CustomType(data_type: CustomType) -> str:
        return data_type.raw
