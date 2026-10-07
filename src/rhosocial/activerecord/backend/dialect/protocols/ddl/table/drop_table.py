# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/drop_table.py
"""
DropTableSupport.

``DROP TABLE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropTableExpression,
    )


@runtime_checkable
class DropTableSupport(Protocol):
    """``DROP TABLE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_table(self) -> bool:
        """Whether the engine accepts the form ``drop_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_if_exists_table(self) -> bool:
        """Whether the engine accepts the form ``if_exists_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_table_cascade(self) -> bool:
        """Whether the engine accepts the form ``drop_table_cascade``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_table_restrict(self) -> bool:
        """Whether the engine accepts the form ``drop_table_restrict``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_purge_on_drop_table(self) -> bool:
        """Whether the engine accepts the form ``purge_on_drop_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_table_statement(self, expr: "DropTableExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropTableExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
