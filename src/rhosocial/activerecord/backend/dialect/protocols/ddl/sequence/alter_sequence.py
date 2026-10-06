# src/rhosocial/activerecord/backend/dialect/protocols/ddl/sequence/alter_sequence.py
"""
AlterSequenceSupport.

``ALTER SEQUENCE`` -- change a sequence that already exists.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        AlterSequenceExpression,
    )


@runtime_checkable
class AlterSequenceSupport(Protocol):
    """``ALTER SEQUENCE`` -- change a sequence that already exists.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_alter_sequence(self) -> bool:
        """Whether the engine accepts the form ``alter_sequence``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_alter_sequence_start(self) -> bool:
        """Whether the engine accepts ``ALTER SEQUENCE ... START``.

        This is a different clause from the ``CREATE SEQUENCE ... START WITH``
        one ``supports_sequence_start`` describes, so the two are not
        interchangeable. Defaults to ``False``; a dialect that accepts the
        ALTER-side clause returns ``True``.
        """
        ...  # pragma: no cover

    def format_alter_sequence_statement(self, expr: "AlterSequenceExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.AlterSequenceExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
