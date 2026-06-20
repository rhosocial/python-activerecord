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

    Subclass lifecycle
    ------------------
    * **Base (generic) types** leave ``_is_base_type = True`` (the default).
      Instantiating them raises ``TypeError`` — users must pick a backend-
      specific subtype.

    * **Backend-specific types** pass ``backend=`` in the class header, e.g.
      ``class MySQLIntType(IntegerType, backend="mysql")``.  This sets
      ``_is_base_type = False`` so they can be instantiated.

    * **synonyms** are only declared at the backend level and **only** between
      types belonging to the same backend.
    """

    #: ``True`` for generic types that must not be instantiated directly.
    _is_base_type: bool = True

    #: Backend identifier set by ``__init_subclass__(backend=…)``.
    _backend: str = ""

    #: Testing override — set to ``True`` globally in test fixtures to
    #: allow direct instantiation of base (generic) types.
    _testing_override: bool = False

    def __init_subclass__(cls, backend: str = "", **kwargs):
        super().__init_subclass__(**kwargs)
        if backend:
            cls._is_base_type = False
            cls._backend = backend

    @classmethod
    def synonyms(cls) -> Set[str]:
        """Return class names considered equivalent to this type.

        Override in subclasses to declare cross-class equivalence
        (e.g. ``IntType`` ↔ ``IntegerType``).  Used by ``is_equivalent``.

        .. note::
           Synonyms are **only** meaningful at the backend level and should
           **not** be declared on generic (base) types.
        """
        return set()

    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        if self._is_base_type and not type(self)._testing_override:
            raise TypeError(
                f"{type(self).__name__} is a base (generic) type and cannot "
                f"be instantiated directly. Use a backend-specific type "
                f"instead (e.g. MySQLIntegerType)."
            )
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

    def is_equivalent(self, other: DataType) -> bool:
        """Structural synonym check.

        Returns ``True`` when two types are logically the same for schema
        comparison purposes even when they are different Python classes
        (e.g. ``PostgresIntType`` vs ``PostgresIntegerType``).
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
