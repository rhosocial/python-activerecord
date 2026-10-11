# src/rhosocial/activerecord/backend/dialect/mixins/data_type.py
"""Data type formatting dispatch for SQL dialects."""

from __future__ import annotations

import re
import typing
from functools import lru_cache
from typing import Any, Callable, cast, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...expression.types._base import DataType


SQLQueryAndParams = Tuple[str, tuple]
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


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

    * substituted — ``suggested_data_types()[name]`` names what this backend
      stores instead, for concepts it genuinely cannot spell (XML on SQLite,
      arrays on Snowflake, …).

    Silence is the one answer that is not allowed: a caller who asks for an
    undeclared concept is told "unsupported" and nothing more, which is
    indistinguishable from the concept never having been considered. The
    ``suggested_data_types`` hook exists so that a backend *can* answer without
    faking a type it does not have, and the error text in
    :meth:`_suggested_type_advice` puts the answer in front of the caller.

    The two are disjoint by contract: a type the dialect renders needs no
    substitute. Both properties — completeness over core types, and the
    renderability of every suggested substitute — are enforced by
    ``tests/.../dummy2/test_type_protocol_contracts.py`` rather than by a
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
    family *is* the registry, and :meth:`_type_class_for` says where the class
    comes from — the formatter's own annotation first, then the backend's type
    module, then the live subclass tree. That last step is why
    ``tests/.../dummy2/test_type_dispatch_registry.py`` asks in a **fresh
    interpreter**: a test that imports the type classes in its own preamble has
    already loaded them, and a bug that only shows up before they are loaded is
    invisible to it.
    """

    def format_data_type(self, data_type: DataType) -> SQLQueryAndParams:
        """Render a :class:`DataType` through the dialect's type family.

        The **total dispatcher**: routes by ``data_type.name`` to the
        ``format_data_type_<name>`` member.  When no member exists the
        raise appends :meth:`substitute_advice`'s text, so a concept this
        dialect does not render still comes back as a ``TypeError`` that
        tells the caller what to declare instead — provided the dialect
        listed the concept in :meth:`suggested_data_types`.  A concept
        that is neither rendered nor suggested raises with **no advice**:
        that silent hole is exactly what the concept-coverage rule (D9,
        see the protocol) forbids, which is why the suggested map is a
        contract rather than politeness.
        """
        from ...expression.types._base import DataType

        if not isinstance(data_type, DataType):
            raise TypeError(
                f"{type(self).__name__}.format_data_type() expects a "
                f"DataType instance, got {type(data_type).__name__}."
            )
        name = getattr(data_type, "name", None)
        if not name or not _NAME_RE.match(name):
            raise TypeError(
                f"{type(data_type).__name__} does not declare a valid generic "
                f"type name (name={name!r}); cannot dispatch."
            )
        formatter = getattr(self, f"format_data_type_{name}", None)
        if formatter is None:
            raise TypeError(
                f"{type(self).__name__} does not support the generic type "
                f"{name!r} (no format_data_type_{name})."
                + self._suggested_type_advice(name)
            )
        return cast(SQLQueryAndParams, formatter(data_type))

    def substitute_advice(self, name: str) -> str:
        """Extra caveat for a substituted concept, empty by default.

        A substitute is not always the same meaning. Firebird's ``TIMETZ``
        concept has no generic rendering there, and its stand-in ``TimeType``
        stores a local time with the zone **dropped** — which is a different
        value, not a different spelling of one value. The default advice text
        cannot say that, because whether a substitution loses something is a
        fact about the backend, not about the mechanism.

        So a backend whose substitution is lossy returns the sentence here, and
        the caller sees it in the error it is already reading. Returning ``""``
        means "no caveat", which is the right answer whenever the substitute
        really does hold the same meaning — most of them do.
        """
        return ""

    def _suggested_type_advice(self, name: str) -> str:
        """Name this dialect's substitute for *name*, if it declares one.

        A backend that cannot render a generic type says what to use instead
        through ``suggested_data_types()``, and that is where the answer is
        written down. Without it in the message the caller is told the type is
        unsupported and nothing else, which is the same as not knowing.

        The wording deliberately does **not** claim the substitute holds the
        same meaning. That claim is true for most entries and false for a
        lossy one, and a message that is usually right is worse than one that
        never says it: the caller reads "stores the same meaning" and stops
        looking. A backend with something to add says it through
        :meth:`substitute_advice`, which lands in the same error.
        """
        substitute = self.suggested_data_types().get(name)
        if substitute is None:
            return " Use a type this backend supports."
        caveat = self.substitute_advice(name).strip()
        message = f" It suggests {substitute.__name__} instead, which is what this backend uses."
        return f"{message} {caveat}" if caveat else message

    def supports_data_types(self) -> Dict[str, type]:
        """Return the generic type names and concrete classes this dialect renders.

        Derived from the ``format_data_type_<name>`` family: **a formatter
        is the declaration of support**, so the mapping covers every name
        the dialect can render. A ``supports_data_type_<name>`` probe,
        where a dialect still owns one, is the only thing that can opt a
        rendered name out — that is how a backend gates a feature by
        version (a number of backends' ``<backend>_*`` probes do). Its
        absence is not an answer of "no": a dialect that declares no
        probe at all supports everything it renders.
        """
        result = {}
        for member_name in dir(type(self)):
            match = re.match(r"^format_data_type_([a-z][a-z0-9_]*)$", member_name)
            if not match:
                continue
            name = match.group(1)
            probe = getattr(self, f"supports_data_type_{name}", None)
            if probe is not None and not probe():
                continue
            data_type_class = self._type_class_for(name)
            if data_type_class is not None:
                result[name] = data_type_class
        return result

    def _type_class_for(self, name: str) -> Optional[type]:
        """Resolve the concrete ``DataType`` class for a generic name.

        Three answers are available and any two of them agree wherever more than
        one exists; the first one available is used.

        **The formatter's own annotation.**  ``format_data_type_<name>`` names
        the concept it renders twice — in the method name and in the declared type
        of its argument — so the class is named in the same place the dispatch key
        is.  That makes the annotation the authoritative statement, and reading it
        first means the answer no longer depends on which class a subclass walk
        happened to reach first if two ever share a ``name``.

        The annotation is trusted only when the class it names declares that
        *same* ``name`` — the 1:1 correspondence this whole mixin is built on.
        A formatter annotated with a different concept's class is describing what
        it accepts, not which dispatch key it serves (PostgreSQL's
        ``format_data_type_postgres_array`` takes the core ``ArrayType``), and the
        next step answers for it instead.

        **This backend's own type module.**  What is left over is a
        *backend-prefixed* name whose class nobody has imported — the one case
        where a lookup can silently come back empty-handed, because the answer
        depends on what else happens to be loaded.  The namespace rule that core
        already enforces is what makes the module derivable: a backend type is
        named ``<backend>_<...>`` and lives under ``...impl.<backend>...``, so
        the slug in the name and the slug in the dialect's own module path agree
        and ``impl/<backend>/expression/types.py`` follows.  Importing it is what
        the SQL Server dialect now does by hand in its registration hook; doing it
        here means a backend that forgets does not lose the name from its
        supported-types mapping, which is the whole of the bug.

        **The live subclass tree**, for a name that is neither of the above.

        A backend that keeps its types somewhere else, or that annotates a name
        only under ``TYPE_CHECKING`` so the annotation is a string with nothing
        behind it, still resolves here *if* something imported the class — and if
        nothing did, this returns ``None`` as it always did.  That residual is why
        ``tests/.../dummy2/test_type_dispatch_registry.py`` checks the mapping
        from a **fresh interpreter**, which is the only way a load-order bug can be
        seen: a test that imports the type classes in its own preamble has already
        made the bug invisible.
        """
        from ...expression.types._base import DataType

        formatter = getattr(type(self), f"format_data_type_{name}", None)
        declared = _annotated_data_type(formatter)
        if declared is not None and declared.name == name:
            return declared

        _load_backend_type_module(type(self), name)

        seen = set()
        stack = [DataType]
        while stack:
            klass = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            stack.extend(klass.__subclasses__())
            if isinstance(klass, type) and getattr(klass, "name", None) == name:
                return klass
        return None

    def suggested_data_types(self) -> Dict[str, type]:
        """Return cross-backend type suggestions, empty by default.

        One half of the **concept coverage** rule (D9 — see
        :class:`~...dialect.protocols.query.data_type.DataTypeSupport` for
        the full statement): every core concept must be either rendered by
        this dialect or listed here, and silence is not an answer — a
        concept that is neither reaches the caller as a bare ``TypeError``
        with no route forward.

        Keys are the **concept names** (the same dispatch keys as
        ``format_data_type_<name>``); values are the class this dialect
        really stores for the concept.  The map and ``supports_data_types()``
        are disjoint — a concept that renders needs no substitute — and an
        empty return means "this dialect renders every core concept it was
        asked about", not "not yet filled in".

        Coverage is deliberately **not audited from core**: backends differ
        too much for one shared shape.  Each backend's own tests walk the
        core concepts (discovered, not listed), assert the coverage, the
        disjointness, that every substitute renders, and that every key
        still names an existing concept — BigQuery's
        ``test_every_core_concept_is_declared`` is the pattern to copy.
        """
        return {}

    def type_parameter_defaults(self) -> Dict[str, Dict[str, Any]]:
        """The values this server supplies for parameters a type leaves undeclared.

        Keys are **concept names** — the same ``format_data_type_<name>`` dispatch
        keys, and the same ``name`` attribute the type class carries, so a backend
        type reached through its own entry point declares under its own name and
        a concept that uses ``None`` to mean *unbounded* rather than *undeclared*
        simply does not appear.  The inner mapping is keyed by parameter name
        (``length``, and ``precision`` for a concept that has one), because the
        question being asked is always "what does this server put here when the
        caller named nothing", and it is a different question for a length than
        for a precision.

        Empty by default, and empty is the **correct answer for most servers**,
        not an unfinished one.  A backend declares nothing here to say that the
        bare form of a concept carries no width on this server: PostgreSQL
        renders ``VARCHAR`` and parses it back with no length, because the
        catalog reports ``atttypmod = -1`` and a bare ``character varying`` there
        really does mean unbounded.  Deciding that centrally is not available —
        ``None`` means "no limit at all" on PostgreSQL and "the default, 4000"
        on Oracle, and there is no value that is honest for both — so the default
        has to be the empty statement and each server writes down its own.

        There is deliberately no list here of which concepts a backend may be
        silent about: silence is what every backend starts from, so a list could
        only ever be a list of permissions, and an empty one of those has already
        been deleted from this codebase once for inviting the next.

        A declaration here is a statement about **what this dialect writes and
        reads back**, so its justification belongs with the vendor's own words
        for the type, and it is worth being precise about which of the two it
        is: PostgreSQL's ``VARCHAR`` has no limit because the server has none,
        whereas SQL Server's ``VARCHAR`` has a documented default of 1 that this
        dialect deliberately does not use.  A backend that widens past its
        server's own default says so in that backend, in that backend's words.
        """
        return {}

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


@lru_cache(maxsize=None)
def _annotated_data_type(formatter: Optional[Callable]) -> Optional[type]:
    """The ``DataType`` class a formatter declares for its argument, if any.

    ``None`` when the formatter has no argument annotation, when the annotation
    is not a class, or when ``typing`` cannot resolve it — which is the ordinary
    outcome for a module that annotates under ``TYPE_CHECKING``, where the name
    is a string and the module namespace it would be resolved against does not
    carry it.  That is a lookup miss, not an error: the caller falls back to the
    subclass walk.

    Cached because ``supports_data_types()`` is called per dialect and resolves
    the same formatter every time, and because an annotation does not change
    after the function is defined.
    """
    if formatter is None:
        return None
    from ...expression.types._base import DataType

    try:
        hints = typing.get_type_hints(formatter)
    except Exception:
        # NameError when the annotation names something the defining module only
        # imported under TYPE_CHECKING; TypeError/AttributeError for a shape
        # get_type_hints cannot read. All of them mean "no usable annotation".
        return None
    # Every parameter is considered rather than only ``data_type``: dialects
    # name it whatever reads best at the call site (``data_type`` in core,
    # ``expr`` in Snowflake), and what is being asked is which ``DataType`` the
    # formatter serves, not what the argument is called.
    for parameter, declared in hints.items():
        if parameter == "return":
            continue
        if isinstance(declared, type) and issubclass(declared, DataType):
            return declared
    return None


#: Where a backend keeps the ``DataType`` subclasses its dispatch names refer to.
#: Every backend that defines backend-named types keeps them in exactly this
#: module; one that does not is simply left alone (see
#: :func:`_load_backend_type_module`).
_BACKEND_TYPE_MODULE = "rhosocial.activerecord.backend.impl.{backend}.expression.types"


@lru_cache(maxsize=None)
def _load_backend_type_module(dialect_class: type, name: str) -> None:
    """Import the module a backend keeps its own ``DataType`` classes in.

    A no-op unless the dispatch name is backend-prefixed and its prefix is the
    dialect's *own* backend slug.  That double condition is what keeps this
    narrow: core types have pure names and never reach here, a core dialect never
    imports a backend package, and one backend never imports another's.

    ``ImportError`` is swallowed on purpose and means only that this backend keeps
    its types somewhere else — the lookup then proceeds exactly as it did before.
    Anything else the module raises while importing is a real error and is left to
    propagate; a broken type module must not look like a missing one.
    """
    from ...expression.types._base import DataType

    backend, separator, _ = name.partition("_")
    if not separator:
        return
    match = DataType._BACKEND_MODULE_RE.search(dialect_class.__module__ or "")
    if match is None or match.group(1) != backend:
        return
    import importlib

    try:
        importlib.import_module(_BACKEND_TYPE_MODULE.format(backend=backend))
    except ImportError:
        return


__all__ = ["DataTypeMixin"]
