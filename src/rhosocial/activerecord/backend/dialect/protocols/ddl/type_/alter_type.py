# src/rhosocial/activerecord/backend/dialect/protocols/ddl/type_/alter_type.py
"""
AlterTypeSupport.

``ALTER TYPE`` -- change a user-defined type that already exists.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        AlterTypeExpression,
        TypeAlterAction,
    )


@runtime_checkable
class AlterTypeSupport(Protocol):
    """``ALTER TYPE`` -- change a user-defined type that already exists.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_alter_type(self) -> bool:
        """Whether the engine accepts the form ``alter_type``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_alter_type_if_exists(self) -> bool:
        """Whether the engine accepts the form ``alter_type_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_type_alter_action(self) -> bool:
        """Whether the engine accepts the form ``type_alter_action``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_multiple_type_alter_actions(self) -> bool:
        """Whether the engine accepts the form ``multiple_type_alter_actions``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_alter_type_statement(self, expr: "AlterTypeExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.AlterTypeExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_type_alter_action(self, expr: "TypeAlterAction") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.TypeAlterAction`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
