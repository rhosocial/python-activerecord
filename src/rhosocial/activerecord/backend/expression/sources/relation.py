# src/rhosocial/activerecord/backend/expression/sources/relation.py
"""
Reading a named relation.

:class:`NamedRelationRef` is the bridge between the two trees: it is a table
source that happens to point at a schema object. It *composes* rather than
inherits, because the source has an alias and lives in a query while the
object has a name and lives in a catalogue.

This is the class that replaces the old ``NamedRelationRef``. That one class
was doing both jobs at once -- carrying an alias and temporal options for a
``FROM`` clause while also standing in for index, sequence and type names in
DDL -- which is why an index could be built out of a "table expression".
"""

from typing import Any, Dict, Optional

from ..mixins import AliasableMixin
from ..objects.base import SchemaObject
from .base import TableSource

__all__ = ["NamedRelationRef"]


class NamedRelationRef(AliasableMixin, TableSource):
    """A ``FROM`` clause reading a named relation.

    The referenced object must be a relation. An index or a sequence cannot
    be read from, so accepting one here would be a category error rather
    than a convenience.
    """

    __slots__ = ("relation", "temporal_options")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this reference."""
        return "format_named_relation"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        relation: SchemaObject,
        temporal_options: Optional[Dict[str, Any]] = None,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Point this reference at a relation.

        Args:
            dialect: The dialect that will render this reference.
            relation: The relation being read. Pass the object, not a bare
                string: a string cannot say which kind of object it names,
                which is the ambiguity this class exists to remove.
            temporal_options: Engine-specific time-travel clauses
                (``Snowflake``'s ``AT`` / ``BEFORE``), or ``None``.
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.

        Note:
            That ``relation`` really is a relation is checked by the dialect
            formatter that renders it, which can also say what this dialect
            would otherwise have rendered in its place.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.relation = relation
        self.temporal_options = temporal_options or {}

    @property
    def name(self) -> str:
        """The relation's own name, unqualified."""
        return self.relation.name

    @property
    def schema_name(self) -> Optional[str]:
        """The relation's inner namespace, or ``None``."""
        return self.relation.schema_name

    @property
    def catalog_name(self) -> Optional[str]:
        """The relation's outer namespace, or ``None``."""
        return self.relation.catalog_name