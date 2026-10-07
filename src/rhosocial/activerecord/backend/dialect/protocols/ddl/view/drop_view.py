# src/rhosocial/activerecord/backend/dialect/protocols/ddl/view/drop_view.py
"""
DropViewSupport.

``DROP VIEW``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropViewExpression,
    )


@runtime_checkable
class DropViewSupport(Protocol):
    """``DROP VIEW``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_view(self) -> bool:
        """Whether the engine accepts the form ``drop_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_if_exists_view(self) -> bool:
        """Whether the engine accepts the form ``if_exists_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_cascade_view(self) -> bool:
        """Whether the engine accepts the form ``cascade_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_restrict_view(self) -> bool:
        """Whether the engine accepts the form ``restrict_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropViewExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
