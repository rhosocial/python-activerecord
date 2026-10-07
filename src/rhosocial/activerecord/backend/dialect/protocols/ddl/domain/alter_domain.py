# src/rhosocial/activerecord/backend/dialect/protocols/ddl/domain/alter_domain.py
"""
AlterDomainSupport.

``ALTER DOMAIN`` -- change a domain that already exists.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        AlterDomainExpression,
        DomainAlterAction,
    )


@runtime_checkable
class AlterDomainSupport(Protocol):
    """``ALTER DOMAIN`` -- change a domain that already exists.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_alter_domain(self) -> bool:
        """Whether the engine accepts the form ``alter_domain``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_alter_domain_action(self) -> bool:
        """Whether the engine accepts the form ``alter_domain_action``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_multiple_domain_alter_actions(self) -> bool:
        """Whether the engine accepts the form ``multiple_domain_alter_actions``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_unnamed_domain_check_drop(self) -> bool:
        """Whether the engine accepts the form ``unnamed_domain_check_drop``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_alter_domain_statement(self, expr: "AlterDomainExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.AlterDomainExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_domain_alter_action(self, expr: "DomainAlterAction") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DomainAlterAction`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
