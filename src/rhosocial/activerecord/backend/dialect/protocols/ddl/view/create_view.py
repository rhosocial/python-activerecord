# src/rhosocial/activerecord/backend/dialect/protocols/ddl/view/create_view.py
"""
CreateViewSupport.

``CREATE VIEW``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateViewExpression,
    )


@runtime_checkable
class CreateViewSupport(Protocol):
    """``CREATE VIEW``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_view(self) -> bool:
        """Whether the engine accepts the form ``create_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_or_replace_view(self) -> bool:
        """Whether the engine accepts the form ``or_replace_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_or_replace_view(self) -> bool:
        """Whether the engine accepts the form ``create_or_replace_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_temporary_view(self) -> bool:
        """Whether the engine accepts the form ``temporary_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_if_not_exists_view(self) -> bool:
        """Whether the engine accepts the form ``if_not_exists_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_view_check_option(self) -> bool:
        """Whether the engine accepts the form ``view_check_option``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateViewExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
