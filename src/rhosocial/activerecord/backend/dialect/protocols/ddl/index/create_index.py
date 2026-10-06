# src/rhosocial/activerecord/backend/dialect/protocols/ddl/index/create_index.py
"""
CreateIndexSupport.

``CREATE INDEX``.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateIndexExpression,
    )


@runtime_checkable
class CreateIndexSupport(Protocol):
    """``CREATE INDEX``.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_index(self) -> bool:
        """Whether the engine accepts the form ``create_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_unique_index(self) -> bool:
        """Whether the engine accepts the form ``unique_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_index_if_not_exists(self) -> bool:
        """Whether the engine accepts the form ``index_if_not_exists``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_index_type(self) -> bool:
        """Whether the engine accepts the form ``index_type``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_partial_index(self) -> bool:
        """Whether the engine accepts the form ``partial_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_functional_index(self) -> bool:
        """Whether the engine accepts the form ``functional_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_index_include(self) -> bool:
        """Whether the engine accepts the form ``index_include``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_index_tablespace(self) -> bool:
        """Whether the engine accepts the form ``index_tablespace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_concurrent_index(self) -> bool:
        """Whether the engine accepts the form ``concurrent_index``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_index_statement(self, expr: "CreateIndexExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateIndexExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
