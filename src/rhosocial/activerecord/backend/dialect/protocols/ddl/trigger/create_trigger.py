# src/rhosocial/activerecord/backend/dialect/protocols/ddl/trigger/create_trigger.py
"""
CreateTriggerSupport.

``CREATE TRIGGER``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTriggerExpression,
    )


@runtime_checkable
class CreateTriggerSupport(Protocol):
    """``CREATE TRIGGER``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_trigger(self) -> bool:
        """Whether the engine accepts the form ``trigger``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_trigger(self) -> bool:
        """Whether the engine accepts the form ``create_trigger``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether the engine accepts the form ``trigger_if_not_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_instead_of_trigger(self) -> bool:
        """Whether the engine accepts the form ``instead_of_trigger``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_statement_trigger(self) -> bool:
        """Whether the engine accepts the form ``statement_trigger``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_trigger_referencing(self) -> bool:
        """Whether the engine accepts the form ``trigger_referencing``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_trigger_when(self) -> bool:
        """Whether the engine accepts the form ``trigger_when``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_trigger_statement(self, expr: "CreateTriggerExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTriggerExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
