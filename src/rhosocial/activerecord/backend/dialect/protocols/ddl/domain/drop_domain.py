# src/rhosocial/activerecord/backend/dialect/protocols/ddl/domain/drop_domain.py
"""
DropDomainSupport.

``DROP DOMAIN``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropDomainExpression,
    )


@runtime_checkable
class DropDomainSupport(Protocol):
    """``DROP DOMAIN``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_domain(self) -> bool:
        """Whether the engine accepts the form ``drop_domain``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_domain_if_exists(self) -> bool:
        """Whether the engine accepts the form ``drop_domain_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_domain_cascade(self) -> bool:
        """Whether the engine accepts the form ``drop_domain_cascade``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_domain_restrict(self) -> bool:
        """Whether the engine accepts the form ``drop_domain_restrict``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_domain_statement(self, expr: "DropDomainExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropDomainExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
