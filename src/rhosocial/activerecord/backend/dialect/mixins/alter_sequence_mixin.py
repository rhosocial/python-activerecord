# src/rhosocial/activerecord/backend/dialect/mixins/alter_sequence_mixin.py
"""Per-statement mixin for AlterSequenceSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Sequence

class AlterSequenceMixin:
    def supports_alter_sequence(self) -> bool:
            """Whether ALTER SEQUENCE is supported.

            Defaults to False.
            """
            return False

    def supports_alter_sequence_start(self) -> bool:
            """Whether the ``ALTER SEQUENCE ... START`` clause is supported.

            This describes a different clause from the one
            :meth:`supports_sequence_start` describes. That probe answers for
            ``CREATE SEQUENCE ... START WITH``, which sets the sequence's *initial*
            value; this one answers for ``ALTER SEQUENCE ... START WITH``, which
            several engines refuse outright. A ``True`` for CREATE therefore does
            not imply a ``True`` here, and the two are not interchangeable.

            Defaults to False, deliberately: a probe answering True by default
            would let :meth:`format_alter_sequence_statement` emit ``START WITH``
            on ALTER and hand the server SQL it rejects. ``False`` fails closed, so
            the dialects that accept the clause declare ``True`` explicitly.
            """
            return False

    def format_alter_sequence_statement(self, expr: "AlterSequenceStatement") -> Tuple[str, tuple]:
            """Format ALTER SEQUENCE statement per SQL standard.

            :meth:`supports_sequence` is consulted first and unconditionally, so a
            dialect that declares no sequence object refuses the statement even if
            it inherited this mixin by mistake.

            RESTART WITH is unconditional once the master switch is on, because no
            dialect in the tree varies it. The other options are each gated before
            their clause is emitted: :meth:`supports_alter_sequence_start` for
            START WITH -- *not* :meth:`supports_sequence_start`, which answers for
            the CREATE-side clause of the same spelling and is consulted by
            :meth:`format_create_sequence_statement` alone --
            :meth:`supports_sequence_increment` for INCREMENT BY,
            :meth:`supports_sequence_minvalue` for MINVALUE,
            :meth:`supports_sequence_maxvalue` for MAXVALUE,
            :meth:`supports_sequence_cycle` for CYCLE,
            :meth:`supports_sequence_cache` for CACHE,
            :meth:`supports_sequence_order` for ORDER, and
            :meth:`supports_sequence_owned_by` for OWNED BY. A requested option
            whose probe is False raises ``UnsupportedFeatureError`` naming it
            instead of the clause being dropped.

            Each two-spelling option carries one parameter per spelling: ``cycle``
            / ``no_cycle``, ``cache`` / ``no_cache``, ``order`` / ``no_order``.
            The parameter selects the spelling; the probe gates whether the
            dialect can express the option at all. An unset pair renders nothing,
            and an explicit spelling whose probe is False raises.

            Args:
                expr: AlterSequenceStatement carrying the sequence name and the
                    options to change (restart, start, increment, min/max value,
                    cycle, cache, order, and owned-by).

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``AlterSequenceStatement.sequence`` is not a Sequence. A
                table would render as a well-formed ALTER SEQUENCE over that table's
                name.
                UnsupportedFeatureError: If the dialect has no sequence object, or
                    does not support an option the expression asked for.
            """
            if not isinstance(expr.sequence, Sequence):
                raise TypeError(
                    f"AlterSequenceStatement.sequence must be a Sequence, "
                    f"got {type(expr.sequence).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            if not self.supports_sequence():
                raise UnsupportedFeatureError(
                    self.name, "ALTER SEQUENCE",
                    f"{self.name} has no sequence object to alter."
                )
            parts = [f"ALTER SEQUENCE {expr.sequence.to_sql()[0]}"]

            if expr.restart is not None:
                parts.append(f"RESTART WITH {expr.restart}")
            if expr.start is not None:
                if not self.supports_alter_sequence_start():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE START",
                        f"{self.name} does not support the START WITH sequence option."
                    )
                parts.append(f"START WITH {expr.start}")
            if expr.increment is not None:
                if not self.supports_sequence_increment():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE INCREMENT",
                        f"{self.name} does not support the INCREMENT BY sequence option."
                    )
                parts.append(f"INCREMENT BY {expr.increment}")
            if expr.minvalue is not None:
                if not self.supports_sequence_minvalue():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE MINVALUE",
                        f"{self.name} does not support the MINVALUE sequence option."
                    )
                parts.append(f"MINVALUE {expr.minvalue}")
            if expr.maxvalue is not None:
                if not self.supports_sequence_maxvalue():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE MAXVALUE",
                        f"{self.name} does not support the MAXVALUE sequence option."
                    )
                parts.append(f"MAXVALUE {expr.maxvalue}")
            if expr.cycle or expr.no_cycle:
                if not self.supports_sequence_cycle():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE CYCLE",
                        f"{self.name} does not support the CYCLE sequence option."
                    )
                parts.append("CYCLE" if expr.cycle else "NO CYCLE")
            if expr.cache is not None:
                if not self.supports_sequence_cache():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE CACHE",
                        f"{self.name} does not support the CACHE sequence option."
                    )
                parts.append(f"CACHE {expr.cache}")
            if expr.no_cache:
                if not self.supports_sequence_cache():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE CACHE",
                        f"{self.name} does not support the CACHE sequence option."
                    )
                parts.append("NO CACHE")
            if expr.order or expr.no_order:
                if not self.supports_sequence_order():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE ORDER",
                        f"{self.name} does not support the ORDER sequence option."
                    )
                parts.append("ORDER" if expr.order else "NO ORDER")
            if expr.owned_by is not None:
                if not self.supports_sequence_owned_by():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE OWNED BY",
                        f"{self.name} does not support the OWNED BY sequence option."
                    )
                if expr.owned_by:
                    parts.append(f"OWNED BY {expr.owned_by}")
                else:
                    parts.append("OWNED BY NONE")

            return " ".join(parts), ()
