# src/rhosocial/activerecord/backend/expression/types/_base.py
"""DataType base class — inherits from BaseExpression."""

from __future__ import annotations

import inspect
import re
from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


class DataType(BaseExpression, ABC):
    """Base for all SQL data type expressions.

    ``DataType`` instances are *value objects* — two instances with the
    same logical parameters compare equal and have the same hash.

    Every concrete type declares its :attr:`name` — the **generic type
    name** used for protocol dispatch (``supports_data_type_<name>`` /
    ``format_data_type_<name>``) and as the key of the dialect's supported
    types mapping.

    Like every expression, a DataType carries an optional dialect
    (conventional first argument, may be deferred and set through the
    ``dialect`` property). Rendering goes through the unified
    ``BaseExpression.to_sql()``: each type renders via the dialect's
    ``format_data_type`` formatting function.

    Additionally, every type carries an optional ``dialect_options`` mapping
    (conventional keyword argument): backend-specific configuration that
    travels with the type instance (e.g. ``{'unsigned': True}``). Options
    participate in **equality** but **not** in ``__hash__`` — the hash covers
    type identity and type params only (options are configuration, rarely
    hashed; this asymmetry is deliberate so mutable option mappings do not
    break hashing).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_data_type"

    name: Optional[str] = None
    """Generic type name — the protocol dispatch key
    (``supports_data_type_<name>`` / ``format_data_type_<name>``).
    ``None`` on the abstract base; **mandatory and validated on every
    concrete subclass** (see ``__init_subclass__``)."""

    _NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

    # Module path of a backend-defined type: ``...impl.<backend>...``.
    # The captured group is the backend slug used as the name prefix.
    _BACKEND_MODULE_RE = re.compile(r"\.impl\.([a-z0-9_]+)(?:\.|$)")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # The dispatch key is a protocol contract, not decoration: a
        # concrete type without a valid `name` is undiscoverable by the
        # naming-convention dispatch (format_data_type_<name>) and cannot
        # appear in the dialect's supported-types mapping. Reject at class
        # definition time instead of failing at render time.
        if inspect.isabstract(cls):
            return
        # Names are namespaced: core-defined types own **pure** names
        # (``integer``, ``varchar``, ``timestamp``); backend-specific types
        # carry their backend name as a prefix (``sqlite_real``,
        # ``mysql_int``, ``postgres_uuid``). The prefix makes the origin of
        # a type visible at a glance and keeps the dispatch keys of
        # different backends isolated — which is exactly what ActiveRecord
        # field definitions need to stay portable across backends.
        name = cls.__dict__.get("name")
        if name is None:
            raise TypeError(
                f"{cls.__module__}.{cls.__name__} must declare a generic "
                f"type name: set `name = \"<identifier>\"` on the class. "
                f"The name is the dispatch key for format_data_type_<name>."
            )
        if not cls._NAME_RE.match(name):
            raise TypeError(
                f"{cls.__module__}.{cls.__name__} declares an invalid "
                f"generic type name {name!r}: it must match "
                f"\"[a-z][a-z0-9_]*\" (a valid identifier suffix)."
            )
        # Enforce the namespace prefix rule: core-defined types (module
        # under ``rhosocial.activerecord.backend.expression.types``) own
        # **pure** names; every other (backend-defined) type must prefix
        # its name with its backend slug derived from the module path.
        # The prefix keeps the dispatch keys of different backends isolated
        # (``format_data_type_<name>`` families never collide) and makes
        # support-list merges unambiguous when a backend dialect folds its
        # own types into the inherited supported-types mapping.
        if not cls.__module__.startswith(
                "rhosocial.activerecord.backend.expression.types"):
            match = cls._BACKEND_MODULE_RE.search(cls.__module__)
            if match is None:
                raise TypeError(
                    f"{cls.__module__}.{cls.__name__} is defined outside "
                    f"the core types package but its module path does not "
                    f"contain \".impl.<backend>\"; backend-defined types "
                    f"must live under \"...impl.<backend>...\" so their "
                    f"namespace prefix can be derived."
                )
            backend = match.group(1)
            prefix = backend + "_"
            if not name.startswith(prefix):
                raise TypeError(
                    f"{cls.__module__}.{cls.__name__} is a backend-defined "
                    f"type: its generic type name {name!r} must be "
                    f"namespaced with the backend slug and start with "
                    f"{prefix!r} (e.g. \"{prefix}<name>\"). The prefix "
                    f"keeps dispatch keys "
                    f"(format_data_type_<name>) isolated per backend and "
                    f"makes support-list merges unambiguous."
                )

    def __init__(self, dialect: Optional["SQLDialectBase"] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.dialect_options: Dict[str, Any] = dict(dialect_options) if dialect_options else {}

    # ----- value-object semantics (ignore dialect for equality) -----

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self._type_params() == other._type_params()
                and self.dialect_options == other.dialect_options)

    def __hash__(self) -> int:
        return hash((type(self), self._type_params()))

    def _type_params(self) -> tuple:
        """Return a tuple of the fields that define the logical type.

        Subclasses with extra parameters override this so the unified
        base ``__eq__``/``__hash__`` compare their logical content;
        they should **not** hand-write ``__eq__``/``__hash__``.
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
        return CustomType(dialect, raw)

    def __repr__(self) -> str:
        params = self._type_params()
        if params:
            return f"{type(self).__name__}{params}"
        return f"{type(self).__name__}()"
