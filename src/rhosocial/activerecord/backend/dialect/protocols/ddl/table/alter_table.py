# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/alter_table.py
"""
AlterTableSupport.

``ALTER TABLE`` -- change a table that already exists.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        AlterTableExpression,
    )


@runtime_checkable
class AlterTableSupport(Protocol):
    """``ALTER TABLE`` -- change a table that already exists.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_alter_table(self) -> bool:
        """Whether the engine accepts the form ``alter_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_rename_table(self) -> bool:
        """Whether the engine accepts the form ``rename_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_rename_column(self) -> bool:
        """Whether the engine accepts the form ``rename_column``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_alter_column_type(self) -> bool:
        """Whether the engine accepts the form ``alter_column_type``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_alter_column_properties(self) -> bool:
        """Whether the engine accepts the form ``alter_column_properties``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_alter_table_index_actions(self) -> bool:
        """Whether the engine accepts the form ``alter_table_index_actions``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_multi_action_alter_table(self) -> bool:
        """Whether the engine accepts the form ``multi_action_alter_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.AlterTableExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
