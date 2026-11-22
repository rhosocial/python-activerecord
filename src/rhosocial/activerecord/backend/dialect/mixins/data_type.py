# src/rhosocial/activerecord/backend/dialect/mixins/data_type.py
"""Data type formatting dispatch for SQL dialects."""

from __future__ import annotations

import re
import typing
from typing import Any, Callable, cast, Dict, Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedDataTypeError

if TYPE_CHECKING:
    from ...expression.types._base import DataType


SQLQueryAndParams = Tuple[str, tuple]
# Name validation lives in expression.types._base.DataType, which enforces it at
# class-definition time; a second copy here would only be a rule that could drift
# from the one that actually runs.


class DataTypeMixin:
    """Mixin providing naming-convention ``format_data_type`` dispatch.

    A ``DataType`` declares its concept in a class attribute ``name``; the
    dialect renders it with ``format_data_type_<name>``. The correspondence
    is by naming convention, not by inheritance: the dialect does not know
    in advance which types exist, and a backend that introduces one needs
    no change here.

    Expression ⇔ dialect correspondence
    ----------------------------------
    Every concept the framework models must be **declared** by every dialect,
    in one of two ways:

    * rendered — ``format_data_type_<name>`` exists, which is the support
      declaration itself. A dialect that owns a ``supports_data_type_<name>``
      probe may answer ``False`` there to opt a rendered name out (a
      version-gated feature); without such a probe, rendering *is* support.

    * substituted — ``substitute_data_types()[name]`` names what this backend
      stores instead, for concepts it genuinely cannot spell (XML on SQLite,
      arrays on Snowflake, …).

    Silence is the one answer that is not allowed: a caller who asks for an
    undeclared concept is told "unsupported" and nothing more, which is
    indistinguishable from the concept never having been considered. The
    ``substitute_data_types`` hook exists so that a backend *can* answer without
    faking a type it does not have, and the error text in
    :meth:`_suggested_type_advice` puts the answer in front of the caller.

    The two are disjoint by contract: a type the dialect renders needs no
    substitute. Both properties — completeness over core types, and the
    renderability of every suggested substitute — are enforced by
    ``tests/.../dummy/capability/test_type_protocol_contracts.py`` rather than by a
    ``Protocol``, because the set of concepts is open: a backend may add one
    (that is how ``Enum8``/``Enum16`` in ClickHouse, ``GEOMETRY`` in
    PostgreSQL, or the three SQL Server GUID spellings exist), and requiring
    the dialect protocol to enumerate every core type would turn each addition
    into an edit to an unrelated file. A backend that owns a whole family of
    its own types additionally declares a ``XxxTypeSupport(Protocol)`` for
    them, so the family has one stated shape rather than being merely implied
    by a naming pattern.

    No registry
    -----------
    There is deliberately no table mapping a generic name to a class. The naming
    family *is* the registry, and :meth:`type_class_for` says where the class
    comes from — the formatter's own annotation first, then the backend's type
    module, then the live subclass tree. That last step is why
    ``tests/.../dummy/types/test_type_dispatch_registry.py`` asks in a **fresh
    interpreter**: a test that imports the type classes in its own preamble has
    already loaded them, and a bug that only shows up before they are loaded is
    invisible to it.
    """

    def format_data_type(self, expr: DataType) -> Tuple[str, tuple]:
        """Render a :class:`DataType` through the dialect's type family.

        The **total dispatcher**: routes by ``expr.name`` to the
        ``format_data_type_<name>`` member.  When no member exists the
        raise appends :meth:`substitute_advice`'s text, so a concept this
        dialect does not render still comes back as a ``TypeError`` that
        tells the caller what to declare instead — provided the dialect
        listed the concept in :meth:`substitute_data_types`.  A concept
        that is neither rendered nor suggested raises with **no advice**:
        that silent hole is exactly what the concept-coverage rule (D9,
        see the protocol) forbids, which is why the suggested map is a
        contract rather than politeness.
        """
        from ...expression.types._base import DataType

        if not isinstance(expr, DataType):
            raise TypeError(
                f"{type(self).__name__}.format_data_type() expects a "
                f"DataType instance, got {type(expr).__name__}."
            )
        # `name` is declared on DataType and every concrete subclass has it
        # validated at class-definition time (see DataType.__init_subclass__),
        # so it is read directly: probing for a field the contract already
        # guarantees is the reflection §11.2 forbids, and the None check it
        # invites would only ever catch a class that never could have existed.
        name = expr.name
        formatter = getattr(self, f"format_data_type_{name}", None)
        if formatter is None:
            raise UnsupportedDataTypeError(
                f"{type(self).__name__} does not support the generic type "
                f"{name!r} (no format_data_type_{name})."
                + self._suggested_type_advice(name)
            )
        return cast(SQLQueryAndParams, formatter(expr))

    def _check_spelling(self, data_type, accepted) -> None:
        """Raise unless *data_type* carries a spelling this dialect renders.

        A ``DataType`` with several spellings (one class, several ways to write
        it — ``INTEGER``/``INT``, ``DECIMAL``/``NUMERIC``/``DEC``) carries the
        chosen one in ``spelling``. Which of them a *backend* accepts is a fact
        about the backend, not about the concept, so the check belongs here in
        the formatter rather than in the expression: SQL Server has ``INT`` but
        no ``INT4``, PostgreSQL has no ``TINYINT`` at all, and a silent fallback
        to the default spelling would turn a caller's explicit request into a
        different type without saying so.

        ``accepted`` is either the class that declares ``SPELLINGS`` — normally
        the formatter's own parameter type — or an explicit tuple, for the
        common case where a backend supports only some of a concept's spellings
        and naming the rest would be false advertising (``format_data_type_text``
        below accepts ``"text"`` and not ``"clob"``, because PostgreSQL has no
        CLOB).

        The closed list is what makes this injection-safe: an unknown spelling
        is a ``TypeError`` naming the accepted set, never a value interpolated
        into SQL. The same argument as
        :meth:`~...types.custom.CustomType.validate_type_name` and
        ``type_name.validate_type_name``.
        """
        spellings = accepted if isinstance(accepted, tuple) else accepted.SPELLINGS
        spelling = data_type.spelling
        if spelling not in spellings:
            raise TypeError(
                f"{type(self).__name__} does not spell this type "
                f"{spelling!r}; it renders "
                f"{', '.join(repr(s) for s in spellings)}."
            )

    def _suggested_type_advice(self, name: str) -> str:
        """Name this dialect's substitute for *name*, if it declares one.

        A backend that cannot render a generic type says what to use instead
        through ``substitute_data_types()``, and that is where the answer is
        written down. Without it in the message the caller is told the type is
        unsupported and nothing else, which is the same as not knowing.

        The wording deliberately does **not** claim the substitute holds the
        same meaning. That claim is true for most entries and false for a
        lossy one, and a message that is usually right is worse than one that
        never says it: the caller reads "stores the same meaning" and stops
        looking. A backend with something to add says it through
        :meth:`substitute_advice`, which lands in the same error.
        """
        _sub = getattr(self, 'suggest_substitute_types', None)
        substitute = (_sub().mapping if _sub else {}).get(name)
        if substitute is None:
            return " Use a type this backend supports."
        _adv = getattr(self, 'suggest_substitute_advice', None)
        caveat = (_adv(name).advice if _adv else '').strip()
        message = f" It suggests {substitute.__name__} instead, which is what this backend uses."
        return f"{message} {caveat}" if caveat else message




__all__ = ["DataTypeMixin"]
