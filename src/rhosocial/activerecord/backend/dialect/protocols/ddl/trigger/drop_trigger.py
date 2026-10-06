# src/rhosocial/activerecord/backend/dialect/protocols/ddl/trigger/drop_trigger.py
"""
DropTriggerSupport.

``DROP TRIGGER``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropTriggerExpression,
    )


@runtime_checkable
class DropTriggerSupport(Protocol):
    """``DROP TRIGGER``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_trigger(self) -> bool:
        """Whether the engine accepts the form ``drop_trigger``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_trigger_if_exists(self) -> bool:
        """Whether the engine accepts the form ``trigger_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_trigger_statement(self, expr: "DropTriggerExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropTriggerExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
