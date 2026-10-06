# src/rhosocial/activerecord/backend/dialect/mixins/identity_column.py
"""Identity-column capability probes and the SQL-standard clause formatter."""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import IdentityClause


class IdentityColumnMixin:
    """Mixin for SQL-standard ``GENERATED ... AS IDENTITY`` column support.

    The identity clause is a *parameterised* column clause: the generation
    mode (``ALWAYS`` / ``BY DEFAULT``) plus optional sequence attributes
    (start, increment, min/max value, cycle). One probe answers for the
    mechanism as a whole and one probe answers for each option, so a dialect
    can say exactly which part of the clause it can express. The formatter
    consults every probe before emitting its clause.

    This is not ``AUTO_INCREMENT`` (a parameterless marker, carried by
    :class:`AutoIncrementClause` and :class:`AutoIncrementMixin`) and not
    ``SERIAL`` (a PostgreSQL *type*, not a column clause).

    Every probe defaults to ``False``. The direction is deliberate: a probe
    answering ``True`` by default would let the formatter emit a clause the
    server rejects, and the default must hold for dialects that have not
    declared the capability yet. Dialects that accept the clause declare
    ``True`` explicitly.
    """

    def supports_identity_column(self) -> bool:
        """Whether the dialect accepts a ``GENERATED ... AS IDENTITY`` column.

        Defaults to ``False``: a probe answering ``True`` by default would let
        :meth:`format_identity_clause` emit the clause on a server that has
        never accepted it. Dialects that accept the clause declare ``True``.
        """
        return False

    def supports_identity_generation_always(self) -> bool:
        """Whether ``GENERATED ALWAYS AS IDENTITY`` can be expressed.

        ``ALWAYS`` means the server rejects user-supplied values for the
        column, so a dialect that can only express ``BY DEFAULT`` must answer
        ``False`` here rather than downgrade the request. Defaults to
        ``False``, the fail-closed direction.
        """
        return False

    def supports_identity_start(self) -> bool:
        """Whether the ``START WITH`` identity option can be expressed.

        Defaults to ``False``, the fail-closed direction: a requested start
        that cannot be expressed is refused by the formatter, never dropped.
        """
        return False

    def supports_identity_increment(self) -> bool:
        """Whether the ``INCREMENT BY`` identity option can be expressed.

        Defaults to ``False``, the fail-closed direction.
        """
        return False

    def supports_identity_minvalue(self) -> bool:
        """Whether the ``MINVALUE`` identity option can be expressed.

        Defaults to ``False``, the fail-closed direction.
        """
        return False

    def supports_identity_maxvalue(self) -> bool:
        """Whether the ``MAXVALUE`` identity option can be expressed.

        Defaults to ``False``, the fail-closed direction.
        """
        return False

    def supports_identity_cycle(self) -> bool:
        """Whether the ``CYCLE`` / ``NO CYCLE`` identity option can be expressed.

        Defaults to ``False``, the fail-closed direction: an explicit cycle
        setting that cannot be expressed is refused by the formatter, never
        dropped.
        """
        return False

    def format_identity_clause(self, expr: "IdentityClause") -> Tuple[str, Tuple]:
        """Format the SQL-standard identity clause.

        Renders `` GENERATED {ALWAYS|BY DEFAULT} AS IDENTITY`` with optional
        ``(START WITH ... INCREMENT BY ... MINVALUE ... MAXVALUE ... CYCLE ...)``.
        Dialects with a different spelling (SQL Server / Snowflake
        ``IDENTITY(seed, inc)``) override this method; their override carries
        the same per-option gating.

        Every gate fails closed and refuses by name rather than dropping the
        clause:

        * :meth:`supports_identity_column` gates the clause as a whole;
        * :meth:`supports_identity_generation_always` gates ``ALWAYS``;
        * :meth:`supports_identity_start` / ``_increment`` / ``_minvalue`` /
          ``_maxvalue`` / ``_cycle`` gate each requested option.

        An option whose probe is ``False`` raises ``UnsupportedFeatureError``
        naming that option: dropping it would change the statement's meaning,
        and there is no downgrade or escape.

        Args:
            expr: The ``IdentityClause`` carrying the identity parameters.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: If the dialect cannot express the clause,
                the requested generation mode, or one of the requested options.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_identity_column():
            raise UnsupportedFeatureError(
                self.name, "IDENTITY column",
                f"{self.name} does not support IDENTITY columns."
            )
        generation = (expr.generation or "BY DEFAULT").upper()
        if generation == "ALWAYS" and not self.supports_identity_generation_always():
            raise UnsupportedFeatureError(
                self.name, "IDENTITY GENERATED ALWAYS",
                f"{self.name} cannot express GENERATED ALWAYS for an identity "
                f"column; only BY DEFAULT is available."
            )
        sql = f" GENERATED {generation} AS IDENTITY"
        attributes = []
        if expr.start is not None:
            if not self.supports_identity_start():
                raise UnsupportedFeatureError(
                    self.name, "IDENTITY START",
                    f"{self.name} does not support the START WITH identity option."
                )
            attributes.append(f"START WITH {expr.start}")
        if expr.increment is not None:
            if not self.supports_identity_increment():
                raise UnsupportedFeatureError(
                    self.name, "IDENTITY INCREMENT",
                    f"{self.name} does not support the INCREMENT BY identity option."
                )
            attributes.append(f"INCREMENT BY {expr.increment}")
        if expr.minvalue is not None:
            if not self.supports_identity_minvalue():
                raise UnsupportedFeatureError(
                    self.name, "IDENTITY MINVALUE",
                    f"{self.name} does not support the MINVALUE identity option."
                )
            attributes.append(f"MINVALUE {expr.minvalue}")
        if expr.maxvalue is not None:
            if not self.supports_identity_maxvalue():
                raise UnsupportedFeatureError(
                    self.name, "IDENTITY MAXVALUE",
                    f"{self.name} does not support the MAXVALUE identity option."
                )
            attributes.append(f"MAXVALUE {expr.maxvalue}")
        if expr.cycle is not None:
            if not self.supports_identity_cycle():
                raise UnsupportedFeatureError(
                    self.name, "IDENTITY CYCLE",
                    f"{self.name} does not support the CYCLE identity option."
                )
            attributes.append("CYCLE" if expr.cycle else "NO CYCLE")
        if attributes:
            sql += f" ({' '.join(attributes)})"
        return sql, ()
