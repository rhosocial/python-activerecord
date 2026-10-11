# src/rhosocial/activerecord/backend/expression/types/_base.py
"""DataType base class — inherits from BaseExpression."""

from __future__ import annotations

import inspect
import re
from abc import ABC
from typing import TYPE_CHECKING, Optional, Tuple

from ..bases import BaseExpression

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

    Backend-specific type configuration is carried by typed constructor
    fields on the backend's own type subclass, never by an untyped bag.

    Spellings
    ---------
    SQL and the supported backends spell one type several ways: ``INT`` is
    SQL's own shorthand for ``INTEGER``, ``CHARACTER VARYING`` for ``VARCHAR``,
    ``BYTEA`` is PostgreSQL's name for a ``BLOB``. Those are **spellings of one
    type**, not separate types — a second class for ``INT`` would make
    ``parse_type("INT")`` and ``parse_type("INTEGER")`` return different classes
    for the same storage, and the schema differ would then need a table of
    strings to tell them apart. So a type that has synonyms declares them as a
    constant :attr:`SPELLINGS` list and takes a ``spelling`` argument naming
    which one to render as.

    Two things follow from that division of labour:

    * **A type with no synonyms declares no list and takes no argument.** There
      is nothing to choose between, so a single-spelling ``SPELLINGS`` and a
      ``spelling`` parameter that can only hold one value are noise.
    * **The expression only collects the parameter.** Which spelling a backend
      actually renders is the formatter's business — ``format_data_type_<name>``
      reads ``data_type.spelling`` and either honours it or reports that this
      dialect does not support it. Keeping the vocabulary in a constant on the
      class is what lets a formatter validate against it in one line.
    """

    #: The known spellings of this concept, for types that have more than one.
    #: Empty on the abstract base and on every type with a single spelling.
    SPELLINGS: Tuple[str, ...] = ()

    #: Which member of :attr:`SPELLINGS` this instance renders as, or ``None``
    #: on the abstract base and on types that take no ``spelling`` argument.
    #:
    #: Deliberately **not** in :attr:`PARAMETERS`.  A spelling is how this
    #: instance is written, not what it is: the same column introspects as
    #: ``character varying(30)`` whichever word created it, so counting it would
    #: make every introspected type unequal to its own declaration and the
    #: schema differ would invent a change.  It does reach the rendered SQL,
    #: which is where the difference is real and visible.
    spelling: Optional[str] = None

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

    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        super().__init__(dialect)

    # ----- value-object semantics (ignore dialect for equality) -----

    #: The instance attributes that constitute this type's **identity**, in
    #: comparison order.  Equality, hashing and ``repr`` read it and nothing
    #: else does.
    #:
    #: What belongs here is what makes two declarations of this type *different
    #: columns* — ``length``, ``precision``, ``scale``, ``unsigned``,
    #: ``values``, ``raw``, ``fields``, ``element_type``, ``dimensions``.
    #:
    #: What does **not** belong here is :attr:`spelling`.  A spelling is a
    #: rendering choice, not a property of the value: ``CREATE TABLE t (a
    #: VARCHAR(30))`` and a catalog that reports ``character varying(30)`` are
    #: the same column, and PostgreSQL reports the long form for every such
    #: column regardless of how it was written.  Counting the spelling would
    #: make every introspected column compare unequal to the declaration that
    #: produced it, and the schema differ would report a change that does not
    #: exist.  Two declarations that differ only in spelling are ``==``; the
    #: difference is still visible in the rendered SQL, and ``spelling`` still
    #: round-trips through :meth:`~...expression.bases.BaseExpression.get_params`
    #: because serialization needs everything the constructor took.
    #:
    #: Declare parameters here rather than overriding anything.  A subclass
    #: inherits the base ``__eq__``/``__hash__`` and is done.
    #:
    #: This is deliberately **not** the serialization surface.  ``get_params``
    #: is the single serialization path for all expressions and reads the
    #: constructor signature; there is exactly one answer to "what does it take
    #: to rebuild this", and it is not this one.
    #:
    #: **A dialect must honour or refuse every field named here — never drop
    #: one.**  A field in this tuple is part of the type's identity, so two
    #: declarations differing only in it are *different columns*, and the
    #: schema differ reports them as such.  That makes exactly three honest
    #: answers for a formatter, and only three:
    #:
    #:   * **honour** it — flipping the field changes the rendered SQL, because
    #:     the field changes what the server will store;
    #:   * **refuse** it — flipping the field raises an error that names the
    #:     field and says why *this* backend cannot do it.  Use this when the
    #:     backend has no such concept (``unsigned`` where the server has no
    #:     unsigned integers).  The backend's own documentation belongs in the
    #:     refusal's message;
    #:   * **not belong here at all** — remove the field from this tuple, and
    #:     say in the class docstring why the concept does not have it (a
    #:     ``SERIAL`` column has no signedness: the auto-increment is a column
    #:     default, not a property of the storage).
    #:
    #: Silently dropping a declared field is the one thing that cannot be
    #: allowed: the caller gets a column that is not the one they declared, and
    #: the call reports success.  Two columns differing only in that field also
    #: render byte-identical SQL, so nothing downstream can notice.
    PARAMETERS: Tuple[str, ...] = ()

    def identity(self) -> tuple:
        """The values of :attr:`PARAMETERS`, in declaration order.

        Derived, never overridden: an override here would be a second,
        divergent answer to "what makes two of these different columns".
        """
        return tuple(getattr(self, field) for field in self.PARAMETERS)

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.identity() == other.identity()

    def __hash__(self) -> int:
        return hash((type(self), self.identity()))

    # ----- factory (delegated by dialect) -----

    @staticmethod
    def parse_data_type_str(dialect: "SQLDialectBase", raw: str) -> "DataType":
        """Backend-specific factory.

        Delegates to ``dialect.parse_type(raw)`` when the dialect implements
        ``DataTypeSupport``.  Falls back to ``CustomType(raw)``.
        """
        from ...dialect.protocols import DataTypeSupport
        if isinstance(dialect, DataTypeSupport):
            return dialect.parse_type(raw)
        from .custom import CustomType
        return CustomType(dialect, raw)

    def __repr__(self) -> str:
        params = self.identity()
        if params:
            return f"{type(self).__name__}{params}"
        return f"{type(self).__name__}()"
