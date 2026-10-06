# src/rhosocial/activerecord/backend/dialect/protocols/ddl/sequence/create_sequence.py
"""
CreateSequenceSupport.

``CREATE SEQUENCE``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateSequenceExpression,
    )


@runtime_checkable
class CreateSequenceSupport(Protocol):
    """``CREATE SEQUENCE``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_sequence(self) -> bool:
        """Whether the engine accepts the form ``sequence``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_create_sequence(self) -> bool:
        """Whether the engine accepts the form ``create_sequence``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_sequence_if_not_exists(self) -> bool:
        """Whether the engine accepts the form ``sequence_if_not_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_sequence_cycle(self) -> bool:
        """Whether the engine accepts the form ``sequence_cycle``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_sequence_cache(self) -> bool:
        """Whether the engine accepts the form ``sequence_cache``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_sequence_order(self) -> bool:
        """Whether the engine accepts the form ``sequence_order``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_sequence_owned_by(self) -> bool:
        """Whether the engine accepts the form ``sequence_owned_by``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_sequence_statement(self, expr: "CreateSequenceExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateSequenceExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
