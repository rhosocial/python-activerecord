# src/rhosocial/activerecord/backend/dialect/protocols/ddl/index/drop_index.py
"""
DropIndexSupport.

``DROP INDEX``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropIndexExpression,
    )


@runtime_checkable
class DropIndexSupport(Protocol):
    """``DROP INDEX``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_index(self) -> bool:
        """Whether the engine accepts the form ``drop_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_index_if_exists(self) -> bool:
        """Whether the engine accepts the form ``index_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_index_on_table(self) -> bool:
        """Whether the engine accepts the form ``drop_index_on_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_index_statement(self, expr: "DropIndexExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropIndexExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
