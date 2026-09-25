# src/rhosocial/activerecord/ddl/types.py
"""Canonical Python-type mapping and dialect-aware column type resolution.

DDL type resolution turns a source field's Python type and optional
``UseSqlType`` candidates into a concrete :class:`DataType` expression.  The
resolver asks the active dialect which generic type names it renders, preserves
explicit candidate order, and can use a dialect-provided suggestion when no
candidate is directly supported.

The types produced here are expression values only.  They are bound to the
active dialect for later rendering; this module neither emits SQL nor executes
DDL.  Generic core types are portable declarations, while backend-specific
types are selected only when their owning backend advertises support.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, cast, TYPE_CHECKING
from uuid import UUID

from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    BooleanType,
    DataType,
    DateTimeType,
    DateType,
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
from rhosocial.activerecord.base.fields import UseSqlType

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class ColumnTypeResolutionError(ValueError):
    """Indicate that no supported SQL data type can represent a Python type.

    The resolver raises this error after checking explicit candidates, the
    canonical Python mapping, and dialect-provided type suggestions.  The
    message identifies the dialect and the unresolved generic type so a source
    declaration can be corrected with a supported ``UseSqlType`` candidate.
    """


class PythonTypeMapping:
    """Map common Python types to portable generic ``DataType`` values.

    The mapping is deliberately backend-independent.  It is used as a fallback
    after explicitly declared ``UseSqlType`` candidates, and the active dialect
    decides whether the resulting generic name is supported.  Enum classes are
    mapped to an :class:`EnumType` whose values are the stringified member
    values.

    Attributes:
        CANONICAL_TYPES: The Python types represented by the default mapping.
        DEFAULT_DATA_TYPES: Exact-type lookup from Python types to generic
            ``DataType`` factories.
        SUBCLASS_RULES: Ordered fallback rules for subclasses of canonical
            scalar and temporal types.
    """

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
        """Return the generic type expression inferred for a Python type.

        Args:
            python_type: A Python type object, normally a field annotation's
                unwrapped runtime type.

        Returns:
            A fresh generic ``DataType`` expression when the type is an Enum
            or matches the canonical/subclass mapping; otherwise ``None``.

        Notes:
            Exact mappings take precedence over subclass rules.  The subclass
            order is significant: ``bool`` is checked before ``int`` and
            ``datetime`` before ``date``.  The returned expression is not
            dialect-bound.
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
    """Resolve declared and inferred ``DataType`` candidates for one dialect.

    A resolver snapshots the dialect's supported generic type names and its
    optional cross-backend suggestions at construction time.  Candidate order is
    significant: explicit ``UseSqlType`` values are considered first, followed
    by the canonical Python mapping; a suggestion is consulted only after no
    direct candidate is supported.

    Notes:
        The resolver binds the selected value to the dialect but does not call
        its SQL formatter.  Capability errors that arise while rendering a
        later DDL expression remain errors of that rendering phase.
    """

    INTEGER_TYPE_NAMES: ClassVar[frozenset] = frozenset(
        {"tinyint", "smallint", "int", "integer", "bigint"}
    )

    def __init__(self, dialect: "SQLDialectBase"):
        """Create a resolver using the dialect's type capability maps.

        Args:
            dialect: The active SQL dialect.  It must provide
                ``supports_data_types()`` and ``suggested_data_types()``.

        Raises:
            AttributeError: If the dialect does not provide one of the two
                type-capability methods.
        """
        self.dialect = dialect
        dialect_view = cast(Any, dialect)
        self.supported = dialect_view.supports_data_types()
        self.suggested = dialect_view.suggested_data_types()

    def resolve(
        self,
        python_type: Any,
        use_sql_type: Optional["UseSqlType"] = None,
    ) -> DataType:
        """Resolve a column type from a Python type and optional declaration.

        Args:
            python_type: The field's Python type used for automatic mapping.
            use_sql_type: Optional marker containing one or more explicit
                ``DataType`` candidates in priority order.

        Returns:
            A fresh ``DataType`` expression bound to the active dialect.

        Raises:
            ColumnTypeResolutionError: If no explicit, inferred, or suggested
                candidate has a supported generic type name.
        """
        declared = list(use_sql_type.data_types) if use_sql_type is not None else []
        return self.resolve_candidates(python_type, declared)

    def resolve_candidates(
        self,
        python_type: Any,
        declared_types: List[DataType],
    ) -> DataType:
        """Resolve from explicit candidates followed by the inferred type.

        Args:
            python_type: Python type used to append a canonical fallback when
                one is available.
            declared_types: Explicit ``DataType`` candidates in declaration
                priority order.

        Returns:
            The first supported candidate bound to the active dialect, or a
            dialect-suggested equivalent when no direct candidate is
            supported.

        Raises:
            ColumnTypeResolutionError: If candidate resolution or a suggested
                replacement cannot produce a supported type.
        """
        candidates = list(declared_types)
        auto = PythonTypeMapping.data_type_for(python_type)
        if auto is not None:
            candidates.append(auto)
        return self.select(candidates, python_type)

    def select(self, candidates: List[DataType], python_type: Any) -> DataType:
        """Select the first supported candidate or a dialect suggestion.

        Args:
            candidates: Ordered ``DataType`` values to try directly.
            python_type: Original Python type used only to make a readable
                failure message when no candidate resolves.

        Returns:
            A dialect-bound copy of the first directly supported candidate, or
            a supported replacement suggested for an unsupported candidate.

        Raises:
            ColumnTypeResolutionError: If a suggested replacement itself has
                an unsupported name, or if no candidate or suggestion is
                supported.
        """
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

    def candidates(
        self,
        python_type: Any,
        use_sql_type: Optional["UseSqlType"],
    ) -> List[DataType]:
        """Return the candidate data types in resolution order.

        Args:
            python_type: Python type used to derive the automatic fallback.
            use_sql_type: Optional marker whose explicit candidates are
                returned first.

        Returns:
            A new list containing the marker's ``data_types`` in order,
            followed by the canonical inferred ``DataType`` when one exists.
            The candidate objects themselves are not copied or bound.
        """
        candidates: List[DataType] = []
        if use_sql_type is not None:
            candidates.extend(use_sql_type.data_types)
        auto = PythonTypeMapping.data_type_for(python_type)
        if auto is not None:
            candidates.append(auto)
        return candidates

    def supports(self, name: Optional[str]) -> bool:
        """Return whether the dialect advertises a generic type name.

        Args:
            name: Generic ``DataType.name`` to check, or ``None``.

        Returns:
            ``True`` when ``name`` is a key in the dialect's supported type
            mapping; otherwise ``False``.
        """
        return name in self.supported

    def instantiate(self, replacement: Type[DataType], original: DataType) -> DataType:
        """Instantiate a suggested type while retaining useful parameters.

        Args:
            replacement: ``DataType`` subclass suggested by the dialect.
            original: Candidate whose constructor parameters should be copied.

        Returns:
            A replacement instance constructed with the original's parameters
            when that succeeds, or a parameterless replacement when the first
            construction attempt fails.

        Raises:
            ColumnTypeResolutionError: If both parameterized and
                parameterless construction fail.
        """
        params = original.get_params()
        try:
            return replacement(**params)
        except Exception:
            pass
        try:
            return replacement()
        except Exception as exc:
            raise ColumnTypeResolutionError(
                f"Cannot instantiate suggested type {replacement.__name__} for "
                f"{type(original).__name__}: {exc}"
            ) from exc

    def bind(self, data_type: DataType) -> DataType:
        """Return a fresh dialect-bound copy of a data type.

        Args:
            data_type: The generic or backend-specific type value to copy.

        Returns:
            A new instance of ``type(data_type)`` constructed from its logical
            parameters, with the active dialect assigned.

        Notes:
            The ``dialect`` entry is removed from ``get_params()`` before
            reconstruction because every ``DataType`` constructor accepts the
            conventional dialect argument separately.
        """
        params = dict(data_type.get_params())
        params.pop("dialect", None)
        clone = type(data_type)(**params)
        clone.dialect = self.dialect
        return clone

    def is_integer(self, data_type: DataType) -> bool:
        """Return whether a resolved type is in the integer family.

        Args:
            data_type: A resolved ``DataType`` value.

        Returns:
            ``True`` for generic names ``tinyint``, ``smallint``, ``int``,
            ``integer``, or ``bigint``; otherwise ``False``.
        """
        return data_type.name in self.INTEGER_TYPE_NAMES


__all__ = [
    "ColumnTypeResolutionError",
    "ColumnTypeResolver",
    "PythonTypeMapping",
]
