# src/rhosocial/activerecord/backend/expression/types/_base.py
"""DataType base class — inherits from BaseExpression."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Set, Tuple

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase
    from ...dialect.protocols import TypeFormattingSupport, TypeParsingSupport


class DataType(BaseExpression, ABC):
    """Base for all SQL data type expressions.

    Inherits from ``BaseExpression`` so every DataType *is* an expression:
    ``to_sql()`` delegates to ``self.dialect.render_type(self)`` when the
    dialect implements ``TypeFormattingSupport``.

    However, DataType instances are primarily *value objects* —
    two instances with the same logical parameters compare equal and have the
    same hash, regardless of whether they carry a dialect reference or not.
    """

    @classmethod
    def synonyms(cls) -> Set[str]:
        """Return class names considered equivalent to this type.

        Override in subclasses to declare cross-class equivalence
        (e.g. ``IntType`` ↔ ``IntegerType``).  Used by ``is_equivalent``.
        """
        return set()

    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        super().__init__(dialect)

    def to_sql(self, dialect: Optional["SQLDialectBase"] = None) -> SQLQueryAndParams:
        effective_dialect = dialect or self.dialect
        if effective_dialect is None:
            return (self._default_sql(), ())
        from ...dialect.protocols import TypeFormattingSupport
        if isinstance(effective_dialect, TypeFormattingSupport):
            return (effective_dialect.render_type(self), ())
        return (self._default_sql(), ())

    @abstractmethod
    def _default_sql(self) -> str:
        """Backend-agnostic SQL string for this type.

        Each concrete DataType subclass must implement this to return the
        canonical SQL representation for its type.
        """
        ...

    # ----- value-object semantics (ignore dialect for equality) -----

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self._type_params() == other._type_params()

    def __hash__(self) -> int:
        return hash((type(self), self._type_params()))

    def _type_params(self) -> tuple:
        """Return a tuple of the fields that define the logical type.
        Override in subclasses with extra parameters."""
        return ()

    # ----- equivalence -----

    def is_equivalent(self, other: DataType) -> bool:
        """Structural synonym check.

        Returns ``True`` when two types are logically the same for schema
        comparison purposes even when they are different Python classes
        (e.g. ``IntType`` vs ``IntegerType``, ``VarCharType`` vs
        ``CharacterVaryingType``).
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
        ``TypeParsingSupport``.  Falls back to ``CustomType(raw)``.
        """
        from ...dialect.protocols import TypeParsingSupport
        if isinstance(dialect, TypeParsingSupport):
            return dialect.parse_type(raw)
        from .custom import CustomType
        return CustomType(raw)

    def __repr__(self) -> str:
        params = self._type_params()
        if params:
            return f"{type(self).__name__}{params}"
        return f"{type(self).__name__}()"
