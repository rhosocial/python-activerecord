# src/rhosocial/activerecord/backend/dialect/mixins/drop_sequence_mixin.py
"""Per-statement mixin for DropSequenceSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Sequence

class DropSequenceMixin:
    def supports_drop_sequence(self) -> bool:
            """Whether DROP SEQUENCE is supported.

            Defaults to False.
            """
            return False

    def supports_sequence_if_exists(self) -> bool:
            """Whether DROP SEQUENCE IF EXISTS is supported.

            Defaults to False.
            """
            return False

    def format_drop_sequence_statement(self, expr: "DropSequenceStatement") -> Tuple[str, tuple]:
            """Format DROP SEQUENCE statement per SQL standard.

            :meth:`supports_sequence` is consulted first and unconditionally, so a
            dialect that declares no sequence object refuses the statement even if
            it inherited this mixin by mistake. ``IF EXISTS`` is then gated by
            :meth:`supports_sequence_if_exists`; when the expression asks for it
            and the probe is False, the formatter raises ``UnsupportedFeatureError``
            instead of dropping the clause.

            Args:
                expr: DropSequenceStatement carrying the sequence name and
                    optional ``if_exists`` flag.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``DropSequenceStatement.sequence`` is not a Sequence. A
                table would render as a well-formed DROP SEQUENCE over that table's
                name.
                UnsupportedFeatureError: If the dialect has no sequence object, or
                    does not support DROP SEQUENCE IF EXISTS.
            """
            if not isinstance(expr.sequence, Sequence):
                raise TypeError(
                    f"DropSequenceStatement.sequence must be a Sequence, "
                    f"got {type(expr.sequence).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            if not self.supports_sequence():
                raise UnsupportedFeatureError(
                    self.name, "DROP SEQUENCE",
                    f"{self.name} has no sequence object to drop."
                )
            parts = ["DROP SEQUENCE"]
            if expr.if_exists:
                if not self.supports_sequence_if_exists():
                    raise UnsupportedFeatureError(
                        self.name, "DROP SEQUENCE IF EXISTS",
                        f"{self.name} does not support DROP SEQUENCE IF EXISTS."
                    )
                parts.append("IF EXISTS")
            parts.append(expr.sequence.to_sql()[0])
            return " ".join(parts), ()
