# src/rhosocial/activerecord/backend/dialect/protocols/ddl/type_/create_type.py
"""
CreateTypeSupport.

``CREATE TYPE`` -- declare a user-defined type.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTypeExpression,
        TypeDefinition,
    )


@runtime_checkable
class CreateTypeSupport(Protocol):
    """``CREATE TYPE`` -- declare a user-defined type.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_type_objects(self) -> bool:
        """Whether the engine accepts the form ``type_objects``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_type(self) -> bool:
        """Whether the engine accepts the form ``create_type``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_type_if_not_exists(self) -> bool:
        """Whether the engine accepts the form ``create_type_if_not_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_type_or_replace(self) -> bool:
        """Whether the engine accepts the form ``create_type_or_replace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_type_definition(self) -> bool:
        """Whether the engine accepts the form ``type_definition``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_type_statement(self, expr: "CreateTypeExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTypeExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_type_definition(self, expr: "TypeDefinition") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.TypeDefinition`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
