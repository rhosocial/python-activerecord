# src/rhosocial/activerecord/backend/dialect/protocols/ddl/database/create_database.py
"""
CreateDatabaseSupport.

``CREATE DATABASE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements.ddl_database import CreateDatabaseExpression


@runtime_checkable
class CreateDatabaseSupport(Protocol):
    """``CREATE DATABASE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_database(self) -> bool:
        """Whether the engine accepts the form ``database``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_database(self) -> bool:
        """Whether the engine accepts the form ``create_database``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_if_not_exists(self) -> bool:
        """Whether the engine accepts the form ``database_if_not_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_owner(self) -> bool:
        """Whether the engine accepts the form ``database_owner``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_encoding(self) -> bool:
        """Whether the engine accepts the form ``database_encoding``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_collation(self) -> bool:
        """Whether the engine accepts the form ``database_collation``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_comment(self) -> bool:
        """Whether the engine accepts the form ``database_comment``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_tablespace(self) -> bool:
        """Whether the engine accepts the form ``database_tablespace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_template(self) -> bool:
        """Whether the engine accepts the form ``database_template``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_connection_limit(self) -> bool:
        """Whether the engine accepts the form ``database_connection_limit``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_database_or_replace(self) -> bool:
        """Whether the engine accepts the form ``database_or_replace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_database_statement(self, expr: "CreateDatabaseExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateDatabaseExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
