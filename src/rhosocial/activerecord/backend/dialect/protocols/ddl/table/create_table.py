# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/create_table.py
"""
CreateTableSupport.

``CREATE TABLE`` with an explicit column list.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTableExpression,
        CreateTableOptions,
    )


@runtime_checkable
class CreateTableSupport(Protocol):
    """``CREATE TABLE`` with an explicit column list.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_table(self) -> bool:
        """Whether the engine accepts the form ``create_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_temporary_table(self) -> bool:
        """Whether the engine accepts the form ``temporary_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_if_not_exists_table(self) -> bool:
        """Whether the engine accepts the form ``if_not_exists_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_or_replace_table(self) -> bool:
        """Whether the engine accepts the form ``create_or_replace_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_unlogged_table(self) -> bool:
        """Whether the engine accepts the form ``unlogged_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_transient_table(self) -> bool:
        """Whether the engine accepts the form ``transient_table``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_table_tablespace(self) -> bool:
        """Whether the engine accepts the form ``table_tablespace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_table_comment(self) -> bool:
        """Whether the engine accepts the form ``table_comment``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_inline_index(self) -> bool:
        """Whether the engine accepts the form ``inline_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_table_inheritance(self) -> bool:
        """Whether the engine accepts the form ``table_inheritance``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTableExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_create_table_options(self, expr: "CreateTableOptions") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTableOptions`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
