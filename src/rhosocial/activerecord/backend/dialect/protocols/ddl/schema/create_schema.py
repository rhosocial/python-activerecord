# src/rhosocial/activerecord/backend/dialect/protocols/ddl/schema/create_schema.py
"""
CreateSchemaSupport.

``CREATE SCHEMA``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateSchemaExpression,
    )


@runtime_checkable
class CreateSchemaSupport(Protocol):
    """``CREATE SCHEMA``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_schema(self) -> bool:
        """Whether the engine accepts the form ``schema``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_schema(self) -> bool:
        """Whether the engine accepts the form ``create_schema``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_schema_if_not_exists(self) -> bool:
        """Whether the engine accepts the form ``schema_if_not_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_schema_authorization(self) -> bool:
        """Whether the engine accepts the form ``schema_authorization``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_schema_statement(self, expr: "CreateSchemaExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateSchemaExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
