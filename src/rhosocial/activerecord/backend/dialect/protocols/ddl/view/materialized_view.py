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
        CreateMaterializedViewStatement,
        DropMaterializedViewStatement,
        RefreshMaterializedViewStatement,
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

    def supports_materialized_view_bind_parameters(self) -> bool:
        """Whether a materialized view body may carry bind parameters.

        Defaults to ``False``: a DDL statement carries no bind parameters
        unless the dialect says it can, so a dialect that does not answer
        refuses rather than emitting a statement the engine may reject. A
        dialect whose engine accepts them returns ``True``.
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

    def supports_with_data_clause(self) -> bool:
        """Whether the ``WITH [NO] DATA`` population clause is supported.

        The clause is shared by ``CREATE TABLE ... AS`` (whose renderer is
        declared by :class:`CreateTableAsSupport`), ``CREATE MATERIALIZED
        VIEW`` and ``REFRESH MATERIALIZED VIEW``.  The probe is declared once,
        here, and consulted by all three renderers; the parameters
        ``with_data`` / ``no_data`` select the spelling.

        Defaults to ``False``; a dialect that accepts the clause returns
        ``True``.
        """
        ...  # pragma: no cover

    def format_create_materialized_view_statement(self, expr: "CreateMaterializedViewStatement") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateMaterializedViewStatement`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_drop_materialized_view_statement(self, expr: "DropMaterializedViewStatement") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.DropMaterializedViewStatement`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover

    def format_refresh_materialized_view_statement(
        self, expr: "RefreshMaterializedViewStatement"
    ) -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.RefreshMaterializedViewStatement`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
