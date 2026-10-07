# src/rhosocial/activerecord/backend/dialect/protocols/ddl/schema/drop_schema.py
"""
DropSchemaSupport.

``DROP SCHEMA``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropSchemaExpression,
    )


@runtime_checkable
class DropSchemaSupport(Protocol):
    """``DROP SCHEMA``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_schema(self) -> bool:
        """Whether the engine accepts the form ``drop_schema``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_schema_if_exists(self) -> bool:
        """Whether the engine accepts the form ``schema_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_schema_cascade(self) -> bool:
        """Whether the engine accepts the form ``schema_cascade``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_schema_restrict(self) -> bool:
        """Whether the engine accepts the form ``schema_restrict``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_schema_statement(self, expr: "DropSchemaExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropSchemaExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
