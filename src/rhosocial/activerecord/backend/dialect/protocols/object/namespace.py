# src/rhosocial/activerecord/backend/dialect/protocols/object/namespace.py
"""The namespace levels every named object may carry."""

from typing import Protocol, runtime_checkable
from ....expression.objects import SchemaObject

__all__ = ["NamespaceSupport"]


@runtime_checkable
class NamespaceSupport(Protocol):
    """Which namespace levels a name can be qualified with.

    Shared by every object protocol because every object has the same three
    slots -- catalog, schema, name -- and the same question about each: does
    this engine have that level, and is it rendered?

    Support is asymmetric across engines, which is why there are two switches
    rather than one:

    * Snowflake has a database above a schema, BigQuery a project above a
      dataset, SQL Server a catalog above a schema, MySQL / MariaDB /
      ClickHouse a database and **no** inner schema.
    * PostgreSQL has a database but leaves it implicit, so it answers ``True``
      for :meth:`supports_catalog` and ``False`` for
      :meth:`supports_catalog_qualification`.
    * Oracle has no catalog at all.

    Every switch here asks whether a name may be *qualified*, never whether the
    engine has the object at all. "Does this database have schemas" is a different
    question with a different owner -- see
    :class:`~rhosocial.activerecord.backend.dialect.protocols.ddl.schema.create_schema.CreateSchemaSupport`
    -- and an engine can answer the two differently. That is why these are named
    ``*_qualification`` and the DDL switches are not.

    Read these from the dialect rather than inferring them from which protocols
    a class happens to inherit: ``runtime_checkable`` protocols match
    structurally, so a dialect can satisfy a protocol while declaring it has no
    such namespace, and treating that as support renders a name for an engine
    that cannot resolve it.
    """

    def validate_namespace(self, expr: "SchemaObject") -> None:
        """Accept or refuse the namespace levels *expr* carries.

        The single check every named object goes through, and the one place a
        dialect that cannot express a level says so.

        Raises rather than returning ``False``, so a caller cannot ignore the
        verdict. Called while rendering rather than while constructing: at
        construction the dialect may not be settled and the slots may not be
        complete.
        """
        ...  # pragma: no cover

    def format_qualified_name(self, expr: "SchemaObject") -> tuple:
        """Build the qualified name of *expr*, levels joined by the separator.

        The spelling half. It assumes the levels have been accepted, so call
        :meth:`validate_namespace` first.
        """
        ...  # pragma: no cover

    def supports_catalog(self) -> bool:
        """Whether the engine models a namespace above the schema."""
        ...  # pragma: no cover

    def supports_catalog_qualification(self) -> bool:
        """Whether the outer namespace is rendered onto a name carrying one."""
        ...  # pragma: no cover

    def supports_schema_qualification(self) -> bool:
        """Whether the inner namespace is rendered onto a name carrying one.

        Named apart from ``supports_schema`` deliberately. That switch is a DDL
        question -- does the engine have schemas, can it ``CREATE SCHEMA`` -- and
        lives on :class:`~...ddl.schema.create_schema.CreateSchemaSupport`. This one is a naming
        question: may a name be qualified with a schema, which an engine can
        answer differently. PostgreSQL qualifies; MySQL and ClickHouse have a
        database and no inner schema, so they answer ``False`` here.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def validate_catalog_name(self, expr: "SchemaObject") -> None:
        """Accept or reject the outer namespace *expr* carries.

        Raises rather than returning ``False``, so a caller cannot ignore the
        verdict. Called while rendering rather than while constructing: at
        construction the dialect may not be settled and the slots may not be
        complete.
        """
        ...  # pragma: no cover

    def validate_schema_name(self, expr: "SchemaObject") -> None:
        """Accept or reject the inner namespace *expr* carries.

        Raises rather than returning ``False``, for the reason given on
        :meth:`validate_catalog_name`.
        """
        ...  # pragma: no cover