# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/create_table_like.py
"""
CreateTableLikeSupport.

``CREATE TABLE ... LIKE`` -- copy the shape of an existing table.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTableLikeExpression,
    )


@runtime_checkable
class CreateTableLikeSupport(Protocol):
    """``CREATE TABLE ... LIKE`` -- copy the shape of an existing table.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_table_like(self) -> bool:
        """Whether the engine accepts the form ``create_table_like``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_table_like_statement(self, expr: "CreateTableLikeExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTableLikeExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
