# src/rhosocial/activerecord/backend/dialect/protocols/ddl/identity_column.py
"""IdentityColumnSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import IdentityClause


@runtime_checkable
class IdentityColumnSupport(Protocol):
    """SQL-standard ``GENERATED {ALWAYS|BY DEFAULT} AS IDENTITY`` column support.

    One protocol per mechanism: this one answers for the *parameterised*
    identity clause. The parameterless ``AUTO_INCREMENT`` marker is a separate
    protocol (:class:`AutoIncrementColumnSupport`), and PostgreSQL's ``SERIAL``
    is a type rather than a column clause.

    Every probe defaults to ``False``. A probe answering ``True`` by default
    would let :meth:`format_identity_clause` emit a clause the server rejects;
    dialects declare the capability they really have.
    """

    def supports_identity_column(self) -> bool:
        """Whether the dialect accepts a ``GENERATED ... AS IDENTITY`` column.

        Defaults to ``False``; a dialect that accepts the clause returns ``True``.
        """
        ...  # pragma: no cover

    def supports_identity_generation_always(self) -> bool:
        """Whether ``GENERATED ALWAYS`` can be expressed (not only ``BY DEFAULT``).

        Defaults to ``False``; a dialect that accepts the generation mode
        returns ``True``. A ``False`` answer makes the formatter refuse an
        ``ALWAYS`` request by name rather than downgrade it.
        """
        ...  # pragma: no cover

    def supports_identity_start(self) -> bool:
        """Whether the ``START WITH`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def supports_identity_increment(self) -> bool:
        """Whether the ``INCREMENT BY`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def supports_identity_minvalue(self) -> bool:
        """Whether the ``MINVALUE`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def supports_identity_maxvalue(self) -> bool:
        """Whether the ``MAXVALUE`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def supports_identity_cycle(self) -> bool:
        """Whether the ``CYCLE`` / ``NO CYCLE`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def format_identity_clause(self, expr: "IdentityClause") -> Tuple[str, tuple]:
        """Render the dialect's identity column clause.

        Raises rather than emitting an unsupported form: a clause the engine
        cannot parse is not a clause worth producing. An option the dialect
        cannot express is refused by name, never dropped.
        """
        ...  # pragma: no cover
