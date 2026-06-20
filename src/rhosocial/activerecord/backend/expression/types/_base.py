# src/rhosocial/activerecord/backend/expression/types/_base.py
"""DataType base class — inherits from BaseExpression."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Optional, Set, Tuple

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


class DataType(BaseExpression, ABC):
    """Base for all SQL data type expressions.

    ``DataType`` instances are *value objects* — two instances with the
    same logical parameters compare equal and have the same hash,
    regardless of whether they carry a dialect reference or not.

    Generic (core) types such as ``IntegerType`` serve as base classes
    for backend-specific subtypes.  They may be instantiated, but calling
    ``to_sql()`` without a bound dialect raises ``ValueError``.
    """

    def __init_subclass__(cls, **kwargs):
        kwargs.pop("backend", None)  # silently consume legacy keyword
        super().__init_subclass__(**kwargs)

    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        super().__init__(dialect)

    def to_sql(self, dialect: Optional["SQLDialectBase"] = None) -> SQLQueryAndParams:
        effective = dialect or self.dialect
        if effective is None:
            raise ValueError(
                f"Cannot render {type(self).__name__} without a dialect. "
                f"Pass a dialect to to_sql() or bind one via bind()."
            )
        return (effective.format_data_type(self), ())

    # ----- value-object semantics (ignore dialect for equality) -----

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return True

    def __hash__(self) -> int:
        return hash(type(self))

    def _type_params(self) -> tuple:
        """Return a tuple of the fields that define the logical type.

        Subclasses with extra parameters may override this, but **must**
        also override ``__eq__`` and ``__hash__`` directly to avoid
        fragility from positional tuple semantics.
        """
        return ()

    # ----- equivalence -----

    @classmethod
    def synonyms(cls) -> Set[str]:
        """Return class names considered equivalent to this type.

        Override in subclasses to declare cross-class equivalence
        (e.g. ``IntType`` ↔ ``IntegerType``).  Used by ``is_equivalent``.
        """
        return set()

    def is_equivalent(self, other: DataType) -> bool:
        """Structural synonym check.

        Returns ``True`` when two types are logically the same for schema
        comparison purposes even when they are different Python classes
        (e.g. ``SQLiteIntegerType`` vs ``SQLiteNumericType``).
        """
        if type(self) is type(other):
            return self == other
        return type(self).__name__ in type(other).synonyms() or \
               type(other).__name__ in type(self).synonyms()

    # ----- factory (delegated by dialect) -----

    @staticmethod
    def parse_data_type_str(dialect: "SQLDialectBase", raw: str) -> "DataType":
        """Backend-specific factory.

        Delegates to ``dialect.parse_type(raw)`` when the dialect implements
        ``DDLTypeSupport``.  Falls back to ``CustomType(raw)``.
        """
        from ...dialect.protocols import DDLTypeSupport
        if isinstance(dialect, DDLTypeSupport):
            return dialect.parse_type(raw)
        from .custom import CustomType
        return CustomType(raw)

    def __repr__(self) -> str:
        params = self._type_params()
        if params:
            return f"{type(self).__name__}{params}"
        return f"{type(self).__name__}()"
