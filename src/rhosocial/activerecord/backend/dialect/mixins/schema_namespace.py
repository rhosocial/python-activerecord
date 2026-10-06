# src/rhosocial/activerecord/backend/dialect/mixins/schema_namespace.py
"""
The namespace levels of a named object, and how a dialect spells them.

Two things live here, and they are deliberately separate:

* :meth:`NamespaceMixin.validate_namespace` -- a check. It answers whether the
  namespace levels *expr* carries are ones this dialect can express, and raises
  when they are not.

* :meth:`NamespaceMixin.format_qualified_name` -- the spelling. It builds the
  qualified name, and its ``separator`` says what goes between the levels.

They were one method called ``render_namespace`` until this branch. The name was
wrong in a way that mattered: the method's body is five checks and three spelling
steps, and the whole tree is otherwise consistent -- 751 ``format_*`` methods that
build SQL and 15 ``validate_*`` that do not -- with this as the only ``render_*``
in the package. A validation wearing a builder's name is hard to reason about, and
it is hard to notice that the two responsibilities are already separable.

Keeping the spelling here rather than repeating it in every ``format_*_object``
is deliberate. Those fifteen methods all do the same three things: read the
object's slots, quote each level, join them. Duplicating that fifteen times would
make every dialect responsible for keeping fifteen copies in step, and the failure
mode would be a name rendered one level short.

What this module does *not* do is decide the shape. Engines differ, and they
differ in the way that matters:

* Snowflake has a database above a schema, BigQuery a project above a dataset,
  SQL Server a catalog above a schema, PostgreSQL a database and an inner schema.
* MySQL, MariaDB and ClickHouse have a database and **no** inner schema.
* Oracle has no catalog and **an** inner schema -- the opposite arrangement.
* Firebird has a single unnamed namespace, and no engine qualifies names with it.

A level the caller supplied has to appear in the SQL or be reported as unusable.
Rendering a name against a dialect that cannot express one of its levels produces
a statement naming a different object than the caller asked for, so
:meth:`validate_namespace` raises rather than dropping it.
"""

from typing import List, Tuple
from ...expression.objects import SchemaObject

__all__ = ["NamespaceMixin"]


class NamespaceMixin:
    """Checks the namespace levels a name carries, and spells the name out.

    Mixed into dialects that name objects. It builds no statement of its own:
    :meth:`validate_namespace` accepts or refuses, and the per-kind
    ``format_*_object`` asks :meth:`format_qualified_name` for the text.
    """

    separator: str = "."

    def validate_namespace(self, expr: "SchemaObject") -> None:
        """Accept or refuse the namespace levels *expr* carries.

        The check this class performs for every named object. Called while
        rendering rather than while constructing, because at construction the
        dialect may not be settled and the slots may not be complete.

        Args:
            expr: The object whose ``catalog_name`` and ``schema_name`` slots are
                being checked.

        Raises:
            UnsupportedFeatureError: The object carries a namespace level this
                dialect declares it cannot express.
        """
        from ..exceptions import UnsupportedFeatureError

        if expr.catalog_name and not self.supports_catalog():
            raise UnsupportedFeatureError(
                self.name,
                "catalog-qualified names",
                suggestion=(
                    f"{type(expr).__name__} carries catalog_name="
                    f"{expr.catalog_name!r}, but {self.name} declares no catalog "
                    f"namespace; implement supports_catalog() if that is wrong"
                ),
            )
        if expr.catalog_name and not self.supports_catalog_qualification():
            raise UnsupportedFeatureError(
                self.name,
                "rendering a catalog qualifier",
                suggestion=(
                    f"{self.name} has a catalog but does not qualify names with it; "
                    f"override supports_catalog_qualification() to render it"
                ),
            )
        if expr.schema_name and not self.supports_schema_qualification():
            raise UnsupportedFeatureError(
                self.name,
                "schema-qualified names",
                suggestion=(
                    f"{type(expr).__name__} carries schema_name="
                    f"{expr.schema_name!r}, but {self.name} declares no schema "
                    f"namespace; implement supports_schema_qualification() if "
                    f"that is wrong"
                ),
            )

        if expr.catalog_name:
            self.validate_catalog_name(expr)
        if expr.schema_name:
            self.validate_schema_name(expr)
        return None

    def format_qualified_name(self, expr: "SchemaObject") -> Tuple[str, tuple]:
        """Build the qualified name of *expr*, levels joined by the separator.

        The spelling half of what ``render_namespace`` used to do. The levels and
        their order come from the object's slots; the separator comes from
        :attr:`separator`, which a dialect overrides when its spelling differs.

        Call :meth:`validate_namespace` first. This method assumes the levels are
        ones the dialect can express, and a caller who skips the check gets a
        name built from levels the engine cannot resolve.

        Args:
            expr: The object being named.

        Returns:
            A ``(sql, params)`` tuple. ``params`` is empty because an identifier
            is never a bind parameter.
        """
        parts: List[str] = []
        if expr.catalog_name:
            parts.append(
                self.format_identifier(expr.catalog_name, expr.catalog_need_quote)
            )
        if expr.schema_name:
            parts.append(
                self.format_identifier(expr.schema_name, expr.schema_need_quote)
            )
        parts.append(self.format_identifier(expr.name, expr.name_need_quote))
        return self.separator.join(parts), ()

    def supports_catalog(self) -> bool:
        """Whether the engine models a namespace above the schema.

        Defaults to ``False``: a dialect that has one says so. MySQL, MariaDB,
        ClickHouse, SQL Server, Snowflake and BigQuery return ``True``; Oracle
        has no catalog and keeps this ``False``.

        Read from this method rather than inferred from which protocols the class
        inherits, because ``runtime_checkable`` protocols match structurally -- a
        dialect can satisfy a catalog protocol while declaring no catalog, and
        treating that as support renders a name for an engine that cannot resolve
        it.
        """
        return False

    def supports_catalog_qualification(self) -> bool:
        """Whether the outer namespace is rendered onto a name that carries one.

        Distinct from :meth:`supports_catalog`: PostgreSQL has a database and
        normally leaves it implicit, so it answers ``True`` here and ``False``
        above. Defaults to ``False``.
        """
        return False

    def supports_schema_qualification(self) -> bool:
        """Whether a name may be qualified with an inner namespace.

        Named apart from ``supports_schema``, which is a DDL switch owned by
        :class:`~...mixins.ddl_schema.SchemaMixin` and answers whether the engine
        has schemas at all. This one answers the naming question, and an engine can
        answer the two differently. Defaults to ``False``.
        """
        return False

    def validate_catalog_name(self, expr: "SchemaObject") -> None:
        """Accept or reject the outer namespace *expr* carries.

        The default accepts what the object already validated: a non-empty
        string, or ``None``. An engine with stricter rules -- a length limit, a
        folded case, a reserved word -- overrides this.

        Called from :meth:`validate_namespace` for the reason given there.
        """
        return None

    def validate_schema_name(self, expr: "SchemaObject") -> None:
        """Accept or reject the inner namespace *expr* carries.

        The default accepts what the object already validated. This is the place
        for an engine to be stricter, and it is called from
        :meth:`validate_namespace` for the reason given there.
        """
        return None
