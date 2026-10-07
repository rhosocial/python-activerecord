# src/rhosocial/activerecord/backend/dialect/protocols/ddl/type_/drop_type.py
"""
DropTypeSupport.

``DROP TYPE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        DropTypeExpression,
    )


@runtime_checkable
class DropTypeSupport(Protocol):
    """``DROP TYPE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_drop_type(self) -> bool:
        """Whether the engine accepts the form ``drop_type``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_drop_type_if_exists(self) -> bool:
        """Whether the engine accepts the form ``drop_type_if_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_drop_type_statement(self, expr: "DropTypeExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropTypeExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
