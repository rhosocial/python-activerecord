# src/rhosocial/activerecord/backend/expression/types/_base.py
"""DataType base class — inherits from BaseExpression."""

from __future__ import annotations

import copy
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

    Lifecycle: **declare → bind → render**.

    1. *declare* — types may be constructed without a dialect (model field
       declarations, migrations, ``UseSqlType`` annotations).  Constructor
       convention: type-specific parameters come first; ``dialect`` is
       keyword-only and optional.
    2. *bind* — a dialect is attached via the constructor
       (``dialect=...``), via :meth:`bind`, or at production time by the
       dialect's ``parse_type()`` factory (introspection).
    3. *render* — ``to_sql()`` delegates to the bound dialect's
       ``format_data_type()``; a dialect may also be supplied per call.

    This differs from other expressions, which take a required positional
    ``dialect`` as their first parameter: expressions are query-time
    objects always built in a live dialect context, while types are
    schema-time objects that may be declared before a connection exists.

    Rendering is *strictly faithful*: a dialect renders only declarations
    it natively supports and raises otherwise — it never silently
    substitutes (e.g. generic auto-increment declared on Postgres raises
    and points to ``PostgresSerialType``).  ``synonyms()`` /
    ``is_equivalent()`` exist for intra-dialect normalization during
    schema comparison only; never register cross-dialect equivalences.

    Generic (core) types such as ``IntegerType`` serve as base classes
    for backend-specific subtypes.  They may be instantiated, but calling
    ``to_sql()`` without a bound dialect raises ``ValueError``.
    """

    def __init_subclass__(cls, **kwargs):
        if "backend" in kwargs:
            raise TypeError(
                f"{cls.__name__}: the 'backend' class keyword is no longer "
                f"supported. Bind a dialect at runtime instead — via the "
                f"constructor (dialect=...), bind(), or a dialect's "
                f"parse_type() factory."
            )
        super().__init_subclass__(**kwargs)

    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        if dialect is not None:
            from ...dialect.base import SQLDialectBase
            if not isinstance(dialect, SQLDialectBase):
                raise TypeError(
                    f"{type(self).__name__}: first positional argument is "
                    f"the dialect; pass type parameters as keyword "
                    f"arguments (got {type(dialect).__name__})."
                )
        super().__init__(dialect)

    def bind(self, dialect: "SQLDialectBase") -> "DataType":
        """Return a copy of this type bound to *dialect* for rendering.

        Types are value objects: binding never affects ``__eq__`` or
        ``__hash__``.  The original instance is left untouched; the
        returned copy carries *dialect* and is immediately renderable
        via ``to_sql()``.
        """
        bound = copy.copy(self)
        bound._dialect = dialect
        return bound

    def to_sql(self, dialect: Optional["SQLDialectBase"] = None) -> SQLQueryAndParams:
        effective = dialect or self.dialect
        if effective is None:
            raise ValueError(
                f"Cannot render {type(self).__name__} without a dialect. "
                f"Pass a dialect to to_sql(dialect=...), bind one via "
                f"bind(), or construct with dialect=...."
            )
        return effective.format_data_type(self)

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

        Intra-dialect normalization only: synonyms describe canonical
        forms *within one backend* (e.g. SQLite affinity collapse).
        Never register cross-dialect equivalences — rendering is strictly
        faithful and dialect differences must stay explicit.
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
        ``DDLTypeSupport``.  Falls back to ``CustomType(raw=raw)``.
        """
        from ...dialect.protocols import DDLTypeSupport
        if isinstance(dialect, DDLTypeSupport):
            return dialect.parse_type(raw)
        from .custom import CustomType
        return CustomType(raw=raw)

    def __repr__(self) -> str:
        params = self._type_params()
        if params:
            return f"{type(self).__name__}{params}"
        return f"{type(self).__name__}()"
