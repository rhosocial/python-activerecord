# src/rhosocial/activerecord/backend/dialect/mixins/ddl_sequence.py
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateSequenceExpression,
        DropSequenceExpression,
        AlterSequenceExpression,
    )


class SequenceMixin:
    """Mixin for sequence DDL support."""

    def supports_sequence(self) -> bool:
        """Whether sequence objects are supported."""
        return False

    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported."""
        return False

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported."""
        return False

    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported."""
        return False

    def supports_sequence_if_not_exists(self) -> bool:
        """Whether CREATE SEQUENCE IF NOT EXISTS is supported."""
        return False

    def supports_sequence_if_exists(self) -> bool:
        """Whether DROP SEQUENCE IF EXISTS is supported."""
        return False

    def supports_sequence_cycle(self) -> bool:
        """Whether CYCLE option is supported."""
        return False

    def supports_sequence_cache(self) -> bool:
        """Whether CACHE option is supported."""
        return False

    def supports_sequence_order(self) -> bool:
        """Whether ORDER option is supported."""
        return False

    def supports_sequence_owned_by(self) -> bool:
        """Whether OWNED BY clause is supported."""
        return False

    def format_create_sequence_statement(self, expr: "CreateSequenceExpression") -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement per SQL standard."""
        parts = ["CREATE SEQUENCE"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.sequence_name))

        if expr.start is not None:
            parts.append(f"START WITH {expr.start}")
        if expr.increment is not None:
            parts.append(f"INCREMENT BY {expr.increment}")
        if expr.minvalue is not None:
            parts.append(f"MINVALUE {expr.minvalue}")
        if expr.maxvalue is not None:
            parts.append(f"MAXVALUE {expr.maxvalue}")
        if expr.cycle:
            parts.append("CYCLE")
        else:
            parts.append("NO CYCLE")
        if expr.cache is not None:
            parts.append(f"CACHE {expr.cache}")
        if expr.order:
            parts.append("ORDER")
        if expr.owned_by:
            parts.append(f"OWNED BY {expr.owned_by}")

        return " ".join(parts), ()

    def format_drop_sequence_statement(self, expr: "DropSequenceExpression") -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement per SQL standard."""
        parts = ["DROP SEQUENCE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.sequence_name))
        return " ".join(parts), ()

    def format_alter_sequence_statement(self, expr: "AlterSequenceExpression") -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement per SQL standard."""
        parts = [f"ALTER SEQUENCE {self.format_identifier(expr.sequence_name)}"]

        if expr.restart is not None:
            parts.append(f"RESTART WITH {expr.restart}")
        if expr.start is not None:
            parts.append(f"START WITH {expr.start}")
        if expr.increment is not None:
            parts.append(f"INCREMENT BY {expr.increment}")
        if expr.minvalue is not None:
            parts.append(f"MINVALUE {expr.minvalue}")
        if expr.maxvalue is not None:
            parts.append(f"MAXVALUE {expr.maxvalue}")
        if expr.cycle is not None:
            parts.append("CYCLE" if expr.cycle else "NO CYCLE")
        if expr.cache is not None:
            parts.append(f"CACHE {expr.cache}")
        if expr.order is not None:
            parts.append("ORDER" if expr.order else "NO ORDER")
        if expr.owned_by is not None:
            if expr.owned_by:
                parts.append(f"OWNED BY {expr.owned_by}")
            else:
                parts.append("OWNED BY NONE")

        return " ".join(parts), ()
