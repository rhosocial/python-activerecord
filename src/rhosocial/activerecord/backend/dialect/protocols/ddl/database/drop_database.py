# src/rhosocial/activerecord/backend/dialect/protocols/ddl/database/drop_database.py
"""
DropDatabaseSupport.

``DROP DATABASE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements.ddl_database import DropDatabaseExpression


@runtime_checkable
class DropDatabaseSupport(Protocol):
    """``DROP DATABASE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_database(self) -> bool:
        """Whether the engine accepts the form ``drop_database``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_if_exists(self) -> bool:
        """Whether the engine accepts the form ``database_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_force_drop(self) -> bool:
        """Whether the engine accepts the form ``database_force_drop``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_undrop_database(self) -> bool:
        """Whether the engine accepts the form ``undrop_database``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_database_statement(self, expr: "DropDatabaseExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropDatabaseExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
