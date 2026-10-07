# src/rhosocial/activerecord/backend/dialect/protocols/ddl/sequence/drop_sequence.py
"""
DropSequenceSupport.

``DROP SEQUENCE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropSequenceExpression,
    )


@runtime_checkable
class DropSequenceSupport(Protocol):
    """``DROP SEQUENCE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_sequence(self) -> bool:
        """Whether the engine accepts the form ``drop_sequence``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_sequence_if_exists(self) -> bool:
        """Whether the engine accepts the form ``sequence_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_sequence_statement(self, expr: "DropSequenceExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropSequenceExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
