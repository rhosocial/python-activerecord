# src/rhosocial/activerecord/backend/dialect/protocols/ddl/routine/drop_function.py
"""
DropRoutineSupport.

``DROP FUNCTION`` / ``DROP PROCEDURE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropFunctionExpression,
    )


@runtime_checkable
class DropRoutineSupport(Protocol):
    """``DROP FUNCTION`` / ``DROP PROCEDURE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_function(self) -> bool:
        """Whether the engine accepts the form ``drop_function``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_function_if_exists(self) -> bool:
        """Whether the engine accepts the form ``drop_function_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_function_cascade(self) -> bool:
        """Whether the engine accepts the form ``drop_function_cascade``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_function_statement(self, expr: "DropFunctionExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropFunctionExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
