# src/rhosocial/activerecord/backend/dialect/protocols/ddl/database/alter_database.py
"""
AlterDatabaseSupport.

``ALTER DATABASE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements.ddl_database import AlterDatabaseExpression


@runtime_checkable
class AlterDatabaseSupport(Protocol):
    """``ALTER DATABASE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_alter_database(self) -> bool:
        """Whether the engine accepts the form ``alter_database``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_alter_database_statement(self, expr: "AlterDatabaseExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.AlterDatabaseExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
