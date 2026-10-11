# src/rhosocial/activerecord/backend/dialect/protocols/query/data_type.py
"""DataTypeSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Dict, Protocol, TYPE_CHECKING, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.types._base import DataType


@runtime_checkable
class DataTypeSupport(Protocol):
    """Dialect support for structured ``DataType`` — formatting and parsing.

    Dialects that implement this protocol (usually via ``DataTypeMixin``) can:

    * Render ``DataType`` expressions into backend-specific SQL strings
      via ``format_data_type()`` — called by ``DataType.to_sql()``.
    * Parse raw SQL type strings from introspection back into ``DataType``
      instances via ``parse_type()`` — called by
      ``DataType.parse_data_type_str()``.

    Contract members
    ----------------

    ``format_data_type(data_type)``
        The **total dispatcher**. It validates that ``data_type`` is a
        ``DataType`` instance and routes by ``data_type.name`` to the
        corresponding ``format_data_type_<name>`` method of the naming
        family. A dialect never renders a type directly inside
        ``format_data_type()``; it only dispatches.

    ``format_data_type_<name>(data_type)`` / ``supports_data_type_<name>()``
        **Naming-family contracts.** These per-type members cannot be
        enumerated in the Protocol — they are discovered by convention
        from the type's generic ``name``. The formatter is the declaration
        of support: ``supports_data_types()`` derives the mapping from the
        formatter family, and a ``supports_data_type_X() -> bool`` probe,
        where a dialect owns one, is the only thing that may opt a rendered
        name **out** (a version-gated feature — a number of backends'
        ``<backend>_*`` probes do exactly that). Backends that keep the
        pair keep the **1:1** discipline: for every ``format_data_type_X``
        a ``supports_data_type_X()``, and no probe without a formatter to
        promise delivery. The supported-type surface of a dialect has no
        registry beyond these members.

    Honesty principle (D10)
    -----------------------

    A dialect that does not support a type simply does **not** implement
    its ``format_data_type_X`` — it never fakes a formatter, and never
    hard-codes a ``supports_data_type_X() -> False`` probe for a type it
    cannot render at all. Dispatch on an unsupported type raises
    ``TypeError`` (there is no ``format_data_type_<name>`` to route to),
    which is the honest "unsupported here" signal. Rendering a declaration
    the formatter cannot express raises at render time, which is also a
    legitimate state.

    Backend-specific protocol layering (D8)
    ---------------------------------------

    Backend-defined types (namespaced generic names such as
    ``mysql_int``, ``sqlite_real``) are governed by the backend's **own**
    protocols, defined in each backend repository — not in core. Within
    this layering a backend dialect:

    * MAY override ``format_data_type()`` — typically calling
      ``super().format_data_type()`` for the general family first, then
      handling its own namespaced family;
    * MUST merge its namespaced entries into ``supports_data_types()`` —
      call ``super().supports_data_types()`` and fold in its own
      namespaced entries, so the returned mapping covers both layers.

    Core never enumerates backend families; it only fixes the shape of
    the dispatch and the merge.

    Concept coverage (D9)
    ---------------------

    The honesty principle above governs *how* a dialect says
    "unsupported"; this rule governs *whether it has said anything at
    all*.  Every concrete concept in
    :mod:`rhosocial.activerecord.backend.expression.types` must receive
    one of two explicit answers from every dialect that implements this
    protocol:

    * the concept is **rendered** — its ``format_data_type_<name>``
      exists.  (The formatter may still refuse *particular declarations*
      with ``UnsupportedFeatureError`` plus a ``suggestion`` — a concept
      the dialect models but cannot express every declaration of; that is
      a refusal answer, not an absence.)
    * the concept is **substituted** — an entry in
      :meth:`suggested_data_types` names the class this dialect really
      stores for it, so the caller reads the substitution instead of a
      bare ``TypeError``.

    The two sets are disjoint: a rendered concept needs no substitute.
    **Silence is not an answer.**  A concept that is neither rendered nor
    substituted reaches the caller as a ``TypeError`` with no route
    forward, and the hole is invisible until someone happens to declare
    that concept.

    This completeness is **per dialect and deliberately not audited by
    core**: backends differ too much for one shared shape (a closed
    short type list, a wide list with substitutes, semantic refusals).
    Each backend's own test file should walk the core concepts —
    **discovered, not listed**, so a concept added to core later cannot
    slip past a stale list — and assert: the coverage above; that
    rendered and substituted keys are disjoint; that every substitute
    actually renders on the dialect; and that every suggested key still
    names an existing concept, so a core rename cannot leave dead
    entries.  BigQuery's ``test_every_core_concept_is_declared`` is the
    pattern to copy.
    """






























    def format_data_type(self, data_type: "DataType") -> "Tuple[str, tuple]":
        """Render a ``DataType`` expression into a SQL type string and params.

        Total dispatcher: routes by ``data_type.name`` to the
        ``format_data_type_<name>`` naming-family member. Raises
        ``TypeError`` when the dialect does not support the type (no
        family member exists) — the honest unsupported-type signal.
        """
        ...  # pragma: no cover

    def parse_type(self, raw: str) -> "DataType":
        """Parse a raw SQL type string into a ``DataType``."""
        ...  # pragma: no cover

    def supports_data_types(self) -> Dict[str, type]:
        """Mapping ``{<generic name>: concrete DataType class}`` of every
        type supported by this dialect.

        Keys are the generic type names (the dispatch keys of the
        ``format_data_type_<name>`` naming family); values are the concrete
        ``DataType`` subclasses whose :attr:`~DataType.name` equals the
        key. Backend dialects that define namespaced types must merge
        their own entries into the inherited mapping (``super()`` + own).
        """
        ...  # pragma: no cover

    def suggested_data_types(self) -> "Dict[str, type]":
        """Cross-backend type-consistency suggestion map.

        Keys: generic type name — same namespace as ``format_data_type_*`` /
        ``supports_data_type_*`` (e.g. ``"uuid"``).
        Values: the suggested replacement ``DataType`` **class** (same value
        type as :meth:`supports_data_types` — consumers get usable class
        objects directly, no import resolution needed).

        Contract: suggested keys and supported keys are **disjoint** — a
        type this dialect renders needs no suggestion. Suggestions only —
        the user layer (ActiveRecord) decides whether to adopt them.

        This map is one half of the **concept coverage** rule (D9, see the
        class docstring): every core concept must be rendered or listed
        here, and silence is not an answer.  It is therefore **not**
        optional politeness — an entry here is how a caller who declares a
        concept this dialect stores some other way learns what to declare
        instead.  Return an empty dict when there is nothing to suggest —
        which, under D9, says "this dialect renders every core concept it
        was asked about", not "not yet filled in".
        """
        ...  # pragma: no cover


DDLTypeSupport = DataTypeSupport
