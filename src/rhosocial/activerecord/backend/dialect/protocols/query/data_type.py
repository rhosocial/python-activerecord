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
        from the type's generic ``name``. The two families must correspond
        **1:1**: for every ``format_data_type_X`` a dialect implements it
        MUST also implement ``supports_data_type_X() -> bool``, and vice
        versa. The supported-type surface of a dialect is exactly the set
        of these method pairs — there is no registry.

    Honesty principle (D10)
    -----------------------

    A dialect that does not support a type simply does **not** implement
    its ``format_data_type_X`` / ``supports_data_type_X`` pair — it never
    fakes a formatter or hard-codes ``supports_data_type_X() -> False``
    for an unimplemented type. Dispatch on an unsupported type raises
    ``TypeError`` (there is no ``format_data_type_<name>`` to route to),
    which is the honest "unsupported here" signal.

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
        the user layer (ActiveRecord) decides whether to adopt them. Return
        an empty dict when there is nothing to suggest (honesty principle).
        """
        ...  # pragma: no cover


DDLTypeSupport = DataTypeSupport
