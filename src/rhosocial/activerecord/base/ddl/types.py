# src/rhosocial/activerecord/base/ddl/types.py
"""Canonical Python-type mapping and dialect-aware column type resolution.

The core owns a small, backend-agnostic set of typical Python types and their
canonical *generic* SQL types. Backend dialects do not know Python types: they
declare which generic type names they support (``supports_data_types()``) and a
replacement for the ones they do not (``suggested_data_types()``). Resolution
therefore reuses the existing dialect type protocol.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, TYPE_CHECKING
from uuid import UUID

from ...backend.expression.types import (
    BlobType,
    BooleanType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    EnumType,
    IntegerType,
    IntervalType,
    JsonType,
    TextType,
    TimeType,
    UUIDType,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...backend.dialect import SQLDialectBase
    from ..fields import UseSqlType


class ColumnTypeResolutionError(ValueError):
    """Raised when a Python type cannot be resolved to a supported SQL type."""


class PythonTypeMapping:
    """Canonical mapping from typical Python types to generic SQL types."""

    CANONICAL_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        bool,
        int,
        float,
        Decimal,
        str,
        bytes,
        date,
        time,
        datetime,
        timedelta,
        dict,
        list,
        tuple,
        set,
        UUID,
    )

    DEFAULT_DATA_TYPES: ClassVar[Dict[Type[Any], Type[DataType]]] = {
        bool: BooleanType,
        int: IntegerType,
        float: DoubleType,
        Decimal: DecimalType,
        str: TextType,
        bytes: BlobType,
        date: DateType,
        time: TimeType,
        datetime: DateTimeType,
        timedelta: IntervalType,
        dict: JsonType,
        list: JsonType,
        tuple: JsonType,
        set: JsonType,
        UUID: UUIDType,
    }

    SUBCLASS_RULES: ClassVar[Tuple[Tuple[Type[Any], Type[DataType]], ...]] = (
        (bool, BooleanType),
        (int, IntegerType),
        (float, DoubleType),
        (datetime, DateTimeType),
        (date, DateType),
        (time, TimeType),
        (bytes, BlobType),
        (str, TextType),
    )

    @classmethod
    def data_type_for(cls, python_type: Any) -> Optional[DataType]:
        """Return the canonical generic ``DataType`` for a Python type.

        ``Enum`` subclasses map to ``EnumType`` carrying the member values;
        canonical types are looked up directly; everything else falls back to an
        ordered subclass check (``bool`` before ``int``, ``datetime`` before
        ``date``). ``None`` means "no canonical mapping".
        """
        if isinstance(python_type, type) and issubclass(python_type, Enum):
            return EnumType(values=[str(member.value) for member in python_type])
        factory = cls.DEFAULT_DATA_TYPES.get(python_type)
        if factory is not None:
            return factory()
        if not isinstance(python_type, type):
            return None
        for base, subclass_factory in cls.SUBCLASS_RULES:
            if issubclass(python_type, base):
                return subclass_factory()
        return None


class ColumnTypeResolver:
    """Resolves a column ``DataType`` against one dialect.

    Priority: explicit ``UseSqlType`` candidates (first candidate the dialect
    supports), then the canonical Python-type mapping, then the dialect's
    suggestion for that generic name. The resolved type is always a fresh
    instance bound to the dialect, so the model-declared markers are never
    mutated.
    """

    INTEGER_TYPE_NAMES: ClassVar[frozenset] = frozenset(
        {"tinyint", "smallint", "int", "integer", "bigint"}
    )

    def __init__(self, dialect: "SQLDialectBase"):
        self.dialect = dialect
        self.supported = dialect.supports_data_types()
        self.suggested = dialect.suggested_data_types()

    def resolve(self, python_type: Any, use_sql_type: Optional["UseSqlType"] = None) -> DataType:
        """Resolve the column type for a Python type, or raise on failure."""
        declared = list(use_sql_type.data_types) if use_sql_type is not None else []
        return self.resolve_candidates(python_type, declared)

    def resolve_candidates(self, python_type: Any, declared_types: List[DataType]) -> DataType:
        """Resolve from explicit candidates plus the canonical mapping."""
        candidates = list(declared_types)
        auto = PythonTypeMapping.data_type_for(python_type)
        if auto is not None:
            candidates.append(auto)
        return self.select(candidates, python_type)

    def select(self, candidates: List[DataType], python_type: Any) -> DataType:
        """Pick the first supported candidate; consult suggestions on fallback."""
        for candidate in candidates:
            if self.supports(candidate.name):
                return self.bind(candidate)
        for candidate in candidates:
            replacement = self.suggested.get(candidate.name)
            if replacement is None:
                continue
            instance = self.instantiate(replacement, candidate)
            if self.supports(instance.name):
                return self.bind(instance)
            raise ColumnTypeResolutionError(
                f"Dialect {type(self.dialect).__name__!r} suggests "
                f"{replacement.__name__} for generic type {candidate.name!r}, but "
                f"that resolves to unsupported name {instance.name!r}. A "
                f"suggestion must resolve to a supported type."
            )
        auto = PythonTypeMapping.data_type_for(python_type)
        readable = python_type if auto is None else auto.name
        raise ColumnTypeResolutionError(
            f"Cannot resolve Python type {python_type!r} (generic {readable!r}) to "
            f"a column type on {type(self.dialect).__name__}: no candidate is "
            f"supported and the dialect provides no suggestion. Declare "
            f"UseSqlType(...) with a type the backend supports."
        )

    def candidates(self, python_type: Any, use_sql_type: Optional["UseSqlType"]) -> List[DataType]:
        """Return the candidate data types in resolution order."""
        candidates: List[DataType] = []
        if use_sql_type is not None:
            candidates.extend(use_sql_type.data_types)
        auto = PythonTypeMapping.data_type_for(python_type)
        if auto is not None:
            candidates.append(auto)
        return candidates

    def supports(self, name: str) -> bool:
        """Whether the dialect renders the generic type ``name``."""
        return name in self.supported

    def instantiate(self, replacement: Type[DataType], original: DataType) -> DataType:
        """Instantiate a suggested type class carrying the original's params."""
        params = original.get_params()
        try:
            return replacement(**params)
        except Exception:  # noqa: BLE001 - fall back to the parameterless form
            pass
        try:
            return replacement()
        except Exception as exc:  # noqa: BLE001
            raise ColumnTypeResolutionError(
                f"Cannot instantiate suggested type {replacement.__name__} for "
                f"{type(original).__name__}: {exc}"
            ) from exc

    def bind(self, data_type: DataType) -> DataType:
        """Return a fresh copy of ``data_type`` bound to this dialect."""
        params = dict(data_type.get_params())
        params.pop("dialect", None)
        clone = type(data_type)(**params)
        clone.dialect = self.dialect
        return clone

    def is_integer(self, data_type: DataType) -> bool:
        """Whether a resolved type belongs to the integer family."""
        return data_type.name in self.INTEGER_TYPE_NAMES
