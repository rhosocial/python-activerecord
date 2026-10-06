# src/rhosocial/activerecord/backend/expression/objects/base.py
"""
The identity of a named database object.

A schema object answers exactly one question: *which object, in which
namespace*. It holds three fixed slots and nothing else:

``catalog_name``
    The outermost namespace, when the engine has one (Snowflake database,
    BigQuery project, SQL Server catalog, MySQL database).
``schema_name``
    The inner namespace (Snowflake schema, BigQuery dataset, SQL Server
    schema, Oracle owner).
``name``
    The object's own name inside those namespaces.

The slots are **named and fixed**, never an ordered list: an ordered
representation cannot say which part is the schema and which part is the
name, so every consumer would have to re-infer it. Fixed slots make the
meaning of each part a property of the class rather than of the caller.

Two properties are deliberate and load-bearing:

*Schema objects know nothing about quoting style or case folding.* Identifier
rendering differs per engine -- backticks, brackets, double quotes, upper-casing
-- and that knowledge belongs to the dialect alone. The ``*_need_quote`` flags
below are not quoting *rules*; they are a per-reference request that the dialect
may decline, and the dialect remains the only thing that knows how to honour one.

*Schema objects are expressions.* They derive from
:class:`~rhosocial.activerecord.backend.expression.bases.BaseExpression` like
every other node in the tree, which is what lets a statement hold one as an
ordinary child and render it without knowing what it is.

:class:`SchemaObject` itself declares no ``format_method``, so it cannot be
rendered on its own: reading :attr:`~...bases.BaseExpression.format_method`
raises, and the class exists only to give the concrete kinds below a shared
identity. Each concrete kind declares the single dialect formatter that turns
it into SQL -- ``Table`` renders through ``format_table_object``, ``Index``
through ``format_index_object``, and so on. Only those formatters build SQL;
nothing else in the tree touches a keyword, a separator or a quote.
"""

from typing import Optional, TYPE_CHECKING

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase

__all__ = ["SchemaObject"]


class SchemaObject(BaseExpression):
    """Identity of a named database object: catalog, schema and name.

    This is the shared base of every object the engine persists. Subclasses
    name the *kind* -- table, view, index, sequence, type -- so that the type
    system refuses nonsense such as passing an index where a table belongs.
    The kind never changes how the name is rendered; it only changes which
    statements accept the object and which formatter renders it.
    """

    __slots__ = (
        "catalog_name",
        "schema_name",
        "name",
        "catalog_need_quote",
        "schema_need_quote",
        "name_need_quote",
    )

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        *,
        catalog_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        catalog_need_quote: bool = True,
        schema_need_quote: bool = True,
        name_need_quote: bool = True,
    ) -> None:
        """Record the object's identity.

        Args:
            dialect: The dialect that will render this object. First and
                required, as on every other expression: a schema object names an
                object, and naming it is only meaningful to one engine.
            name: The object's own name, unqualified.
            catalog_name: Outermost namespace, or ``None`` when the engine has
                none or the caller wants the default.
            schema_name: Inner namespace, or ``None`` for the default.
            catalog_need_quote: Whether the catalog is quoted when rendered.
            schema_need_quote: Whether the schema is quoted when rendered.
            name_need_quote: Whether the name is quoted when rendered.

        Raises:
            ValueError: ``name`` is empty, or a namespace slot was given as
                something other than a non-empty string. An empty slot is
                rejected rather than silently treated as absent, because
                ``""`` and ``None`` render differently and only the caller
                knows which was meant.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if catalog_name is not None and (not isinstance(catalog_name, str) or not catalog_name.strip()):
            raise ValueError("catalog_name must be a non-empty string or None")
        if schema_name is not None and (not isinstance(schema_name, str) or not schema_name.strip()):
            raise ValueError("schema_name must be a non-empty string or None")
        super().__init__(dialect)
        self.name = name
        self.catalog_name = catalog_name
        self.schema_name = schema_name
        self.catalog_need_quote = catalog_need_quote
        self.schema_need_quote = schema_need_quote
        self.name_need_quote = name_need_quote

    def __repr__(self) -> str:
        parts = [p for p in (self.catalog_name, self.schema_name, self.name) if p]
        return f"{type(self).__name__}({'.'.join(parts)})"

    def identity(self) -> tuple:
        """What makes this object the object it is.

        Two objects of the same kind, in the same namespaces, under the same
        name, spelled with the same quoting *are* the same catalogue entry. So
        that is the whole of equality: the dialect that renders the name is not
        part of it, since the same table named through two dialects is still
        that one table, and the formatter differs per query, not per object.
        """
        return (
            type(self).__name__,
            self.catalog_name,
            self.schema_name,
            self.name,
            self.catalog_need_quote,
            self.schema_need_quote,
            self.name_need_quote,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SchemaObject):
            return NotImplemented
        return self.identity() == other.identity()

    def __hash__(self) -> int:
        return hash(self.identity())