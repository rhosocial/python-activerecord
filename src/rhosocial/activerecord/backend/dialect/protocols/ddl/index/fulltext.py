# src/rhosocial/activerecord/backend/dialect/protocols/ddl/index/fulltext.py
"""
FulltextIndexSupport.

Full-text search: the index, the MATCH predicate and the parser options.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateFulltextIndexStatement,
        DropFulltextIndexStatement,
        FulltextMatchExpression,
    )


@runtime_checkable
class FulltextIndexSupport(Protocol):
    """Full-text search: the index, the MATCH predicate and the parser options.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_fulltext_index(self) -> bool:
        """Whether the engine accepts the form ``fulltext_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_fulltext_search(self) -> bool:
        """Whether the engine accepts the form ``fulltext_search``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_fulltext_parser(self) -> bool:
        """Whether the engine accepts the form ``fulltext_parser``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_fulltext_boolean_mode(self) -> bool:
        """Whether the engine accepts the form ``fulltext_boolean_mode``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether the engine accepts the form ``fulltext_query_expansion``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_fulltext_index_statement(self, expr: "CreateFulltextIndexStatement") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateFulltextIndexStatement`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_drop_fulltext_index_statement(self, expr: "DropFulltextIndexStatement") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropFulltextIndexStatement`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_fulltext_match(self, expr: "FulltextMatchExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.FulltextMatchExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
