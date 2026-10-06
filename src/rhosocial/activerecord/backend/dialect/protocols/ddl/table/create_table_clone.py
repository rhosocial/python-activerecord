# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/create_table_clone.py
"""
CreateTableCloneSupport.

``CREATE TABLE ... CLONE|COPY`` -- copy an existing table without reading it.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTableCloneExpression,
    )


@runtime_checkable
class CreateTableCloneSupport(Protocol):
    """``CREATE TABLE ... CLONE|COPY`` -- copy an existing table without reading it.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_table_clone(self) -> bool:
        """Whether the engine accepts the form ``create_table_clone``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_table_clone_statement(self, expr: "CreateTableCloneExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTableCloneExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
