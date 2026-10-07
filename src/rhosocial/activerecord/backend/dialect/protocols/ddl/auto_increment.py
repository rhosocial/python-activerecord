# src/rhosocial/activerecord/backend/dialect/protocols/ddl/auto_increment.py
"""AutoIncrementColumnSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import AutoIncrementClause


@runtime_checkable
class AutoIncrementColumnSupport(Protocol):
    """The parameterless ``AUTO_INCREMENT`` column marker.

    One protocol per mechanism: ``AUTO_INCREMENT`` has no parameter space (its
    seed and increment are table-level options), so it is a different mechanism
    from the parameterised SQL-standard identity clause
    (:class:`IdentityColumnSupport`). A dialect may support one, both, or
    neither; MariaDB, for example, supports both.

    The probe defaults to ``False``. A probe answering ``True`` by default
    would let :meth:`format_auto_increment_clause` emit the marker on a server
    that rejects it; dialects declare the capability they really have.
    """

    def supports_auto_increment_column(self) -> bool:
        """Whether the dialect accepts a bare ``AUTO_INCREMENT`` column marker.

        Defaults to ``False``; a dialect that accepts the marker returns ``True``.
        """
        ...  # pragma: no cover

    def format_auto_increment_clause(self, expr: "AutoIncrementClause") -> Tuple[str, tuple]:
        """Render the dialect's ``AUTO_INCREMENT`` column marker.

        Raises rather than emitting an unsupported form: a marker the engine
        cannot parse is not a marker worth producing.
        """
        ...  # pragma: no cover
