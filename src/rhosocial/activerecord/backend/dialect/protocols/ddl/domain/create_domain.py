# src/rhosocial/activerecord/backend/dialect/protocols/ddl/domain/create_domain.py
"""
CreateDomainSupport.

``CREATE DOMAIN`` -- declare a type built from another type plus constraints.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateDomainExpression,
        DomainCheckConstraint,
        DomainValueExpression,
    )


@runtime_checkable
class CreateDomainSupport(Protocol):
    """``CREATE DOMAIN`` -- declare a type built from another type plus constraints.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_domains(self) -> bool:
        """Whether the engine accepts the form ``domains``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_domain(self) -> bool:
        """Whether the engine accepts the form ``create_domain``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_domain_default(self) -> bool:
        """Whether the engine accepts the form ``domain_default``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_domain_nullability(self) -> bool:
        """Whether the engine accepts the form ``domain_nullability``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_domain_checks(self) -> bool:
        """Whether the engine accepts the form ``domain_checks``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_named_domain_checks(self) -> bool:
        """Whether the engine accepts the form ``named_domain_checks``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_multiple_domain_checks(self) -> bool:
        """Whether the engine accepts the form ``multiple_domain_checks``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_domain_collation(self) -> bool:
        """Whether the engine accepts the form ``domain_collation``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_domain_statement(self, expr: "CreateDomainExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateDomainExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_domain_value_expression(self, expr: "DomainValueExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DomainValueExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_domain_check_constraint(self, expr: "DomainCheckConstraint") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DomainCheckConstraint`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
