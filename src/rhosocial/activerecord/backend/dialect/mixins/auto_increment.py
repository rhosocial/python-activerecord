# src/rhosocial/activerecord/backend/dialect/mixins/auto_increment.py
"""The bare ``AUTO_INCREMENT`` column marker and its capability probe."""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import AutoIncrementClause


class AutoIncrementMixin:
    """Mixin for the parameterless ``AUTO_INCREMENT`` column marker.

    ``AUTO_INCREMENT`` is one mechanism, not three spellings of one thing: it
    is a **parameterless column marker**, and its seed/increment are
    *table-level* options (``AUTO_INCREMENT = 100``), which this node does not
    model. The SQL-standard parameterised clause is
    ``GENERATED ... AS IDENTITY`` (:class:`IdentityColumnMixin`), and
    PostgreSQL's ``SERIAL`` is a *type*, not a column clause at all.

    The probe defaults to ``False``. The direction is deliberate: a probe
    answering ``True`` by default would let :meth:`format_auto_increment_clause`
    emit ``AUTO_INCREMENT`` on a server that rejects it. Dialects that accept
    the marker (MySQL, MariaDB) declare ``True`` explicitly; a dialect whose
    auto-increment spelling is a different mechanism (SQLite's ``AUTOINCREMENT``
    only exists as part of an ``INTEGER PRIMARY KEY`` constraint) answers
    ``False`` rather than render SQL its server rejects.
    """

    def supports_auto_increment_column(self) -> bool:
        """Whether the dialect accepts a bare ``AUTO_INCREMENT`` column marker.

        Defaults to ``False``: a probe answering ``True`` by default would let
        :meth:`format_auto_increment_clause` emit the marker on a server that
        rejects it. Dialects that accept the marker declare ``True``.
        """
        return False

    def format_auto_increment_clause(self, expr: "AutoIncrementClause") -> Tuple[str, Tuple]:
        """Format the bare ``AUTO_INCREMENT`` column marker.

        :meth:`supports_auto_increment_column` is consulted unconditionally; a
        dialect that cannot express the marker refuses rather than emitting a
        token the server rejects. The marker carries no parameters, so there is
        no per-option gate and nothing to drop.

        Args:
            expr: The ``AutoIncrementClause`` carrying nothing but its dialect.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: If the dialect cannot express the marker.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_auto_increment_column():
            raise UnsupportedFeatureError(
                self.name, "AUTO_INCREMENT column",
                f"{self.name} does not support AUTO_INCREMENT columns."
            )
        return " AUTO_INCREMENT", ()
