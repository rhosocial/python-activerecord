# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/create_table_as.py
"""
CreateTableAsSupport.

``CREATE TABLE ... AS <query>`` -- derive the shape from a query's result.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTableAsExpression,
    )


@runtime_checkable
class CreateTableAsSupport(Protocol):
    """``CREATE TABLE ... AS <query>`` -- derive the shape from a query's result.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_table_as(self) -> bool:
        """Whether the engine accepts the form ``create_table_as``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_table_as_statement(self, expr: "CreateTableAsExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTableAsExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
