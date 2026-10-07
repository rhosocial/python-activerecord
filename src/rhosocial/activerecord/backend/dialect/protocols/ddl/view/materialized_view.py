# src/rhosocial/activerecord/backend/dialect/protocols/ddl/view/materialized_view.py
"""
MaterializedViewSupport.

Materialized views: creating, dropping and refreshing a stored query result.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateMaterializedViewExpression,
        DropMaterializedViewExpression,
        RefreshMaterializedViewExpression,
    )


@runtime_checkable
class MaterializedViewSupport(Protocol):
    """Materialized views: creating, dropping and refreshing a stored query result.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_materialized_view(self) -> bool:
        """Whether the engine accepts the form ``materialized_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_refresh_materialized_view(self) -> bool:
        """Whether the engine accepts the form ``refresh_materialized_view``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_materialized_view_tablespace(self) -> bool:
        """Whether the engine accepts the form ``materialized_view_tablespace``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_materialized_view_storage_options(self) -> bool:
        """Whether the engine accepts the form ``materialized_view_storage_options``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def supports_materialized_view_restrict(self) -> bool:
        """Whether the engine accepts the form ``materialized_view_restrict``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_materialized_view_statement(self, expr: "CreateMaterializedViewExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateMaterializedViewExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_drop_materialized_view_statement(self, expr: "DropMaterializedViewExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropMaterializedViewExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_refresh_materialized_view_statement(
        self, expr: "RefreshMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.RefreshMaterializedViewExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
