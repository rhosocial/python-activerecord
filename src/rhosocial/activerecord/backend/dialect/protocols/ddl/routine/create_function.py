# src/rhosocial/activerecord/backend/dialect/protocols/ddl/routine/create_function.py
"""
CreateRoutineSupport.

``CREATE FUNCTION`` / ``CREATE PROCEDURE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateFunctionExpression,
    )


@runtime_checkable
class CreateRoutineSupport(Protocol):
    """``CREATE FUNCTION`` / ``CREATE PROCEDURE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_function(self) -> bool:
        """Whether the engine accepts the form ``function``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_function(self) -> bool:
        """Whether the engine accepts the form ``create_function``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_function_or_replace(self) -> bool:
        """Whether the engine accepts the form ``function_or_replace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_function_parameters(self) -> bool:
        """Whether the engine accepts the form ``function_parameters``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_function_statement(self, expr: "CreateFunctionExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateFunctionExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
