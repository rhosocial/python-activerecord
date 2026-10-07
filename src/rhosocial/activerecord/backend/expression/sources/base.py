# src/rhosocial/activerecord/backend/expression/sources/base.py
"""
Row sources: the things a ``FROM`` clause can name.

A *table source* is whatever produces rows for a query. That is a different
question from "what does the engine persist", and the two are answered by two
separate trees:

* :mod:`..objects` -- catalog identity (a table, a view, an index).
* this module -- syntax position (``FROM x``, ``FROM json_table(...)``,
  ``FROM (SELECT ...)``, ``FROM VALUES ...``).

``FROM json_table(...)`` yields rows but has no catalog identity; ``FROM
my_index`` is neither legal nor meaningful. Keeping the trees apart lets each
one stay honest, and connects them by composition --
:class:`~.relation.NamedRelationRef` holds a schema object rather than
inheriting from one.

A source is an expression: it carries a dialect and renders. That is the
difference from a schema object, which carries neither.
"""

from typing import Optional

from ..bases import BaseExpression

__all__ = ["TableSource"]


class TableSource(BaseExpression):
    """Base of everything a ``FROM`` clause can be built from.

    A source collects parameters and nothing else. It does not know how a
    source is spelled -- not whether an alias is preceded by ``AS``, not which
    identifier quoting applies, not whether a temporal clause comes before the
    alias. Those are dialect decisions, reached through
    :attr:`format_method`, and a source that tried to answer one of them
    itself would be guessing on the engine's behalf.

    An alias is nonetheless a source's parameter rather than a schema object's:
    ``FROM users AS u`` renames a row for the duration of a query and renames
    nothing in the catalogue.
    """

    __slots__ = ()

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_table_source"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Bind the source to a dialect and record its alias.

        Args:
            dialect: The dialect that will render this source.
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect)
        self.alias = alias
        self.alias_need_quote = alias_need_quote