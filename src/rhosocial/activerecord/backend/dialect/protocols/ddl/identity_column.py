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

    Gating and spelling are separate: the probes answer whether an option can
    be expressed, and the ``identity_*_keyword`` hooks answer how the dialect
    spells it. The hooks default to the SQL-standard spellings, so a dialect
    with a different grammar overrides the hook rather than copying the
    formatter (a copy would duplicate the gating too).
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

    def supports_identity_order(self) -> bool:
        """Whether the ``ORDER`` / ``NO ORDER`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def supports_identity_cache(self) -> bool:
        """Whether the ``CACHE`` / ``NO CACHE`` identity option can be expressed.

        Defaults to ``False``; a dialect that accepts the option returns ``True``.
        """
        ...  # pragma: no cover

    def identity_cycle_keyword(self, cycle: bool) -> str:
        """The dialect's spelling of an explicit cycle setting.

        Defaults to the SQL-standard ``CYCLE`` / ``NO CYCLE``; a dialect whose
        grammar spells the negative form differently (Oracle's ``NOCYCLE``)
        overrides this hook.
        """
        ...  # pragma: no cover

    def identity_order_keyword(self, order: bool) -> str:
        """The dialect's spelling of an explicit order setting.

        Defaults to the SQL-standard ``ORDER`` / ``NO ORDER``.
        """
        ...  # pragma: no cover

    def identity_cache_keyword(self, cache: int) -> str:
        """The dialect's spelling of a positive cache setting.

        Defaults to the SQL-standard ``CACHE n``. The negative spelling has
        its own hook, :meth:`identity_no_cache_keyword`; there is no sentinel
        count for it.
        """
        ...  # pragma: no cover

    def identity_no_cache_keyword(self) -> str:
        """The dialect's spelling of ``NO CACHE``.

        Defaults to the SQL-standard ``NO CACHE``; a dialect whose grammar
        spells the negative form differently (Oracle's ``NOCACHE``) overrides
        this hook.
        """
        ...  # pragma: no cover

    def format_identity_clause(self, expr: "IdentityClause") -> Tuple[str, tuple]:
        """Render the dialect's identity column clause.

        Raises rather than emitting an unsupported form: a clause the engine
        cannot parse is not a clause worth producing. An option the dialect
        cannot express is refused by name, never dropped.
        """
        ...  # pragma: no cover
