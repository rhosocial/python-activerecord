# src/rhosocial/activerecord/backend/dialect/mixins/ddl_sequence.py
"""Dialect mixin for sequence DDL support (CREATE/DROP/ALTER SEQUENCE)."""
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateSequenceExpression,
        DropSequenceExpression,
        AlterSequenceExpression,
    )


class SequenceMixin:
    """Mixin adding support for sequence DDL statements."""

    def supports_sequence(self) -> bool:
        """Whether sequence objects are supported.

        Defaults to False.
        """
        return False

    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported.

        Defaults to False.
        """
        return False

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported.

        Defaults to False.
        """
        return False

    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_if_not_exists(self) -> bool:
        """Whether CREATE SEQUENCE IF NOT EXISTS is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_if_exists(self) -> bool:
        """Whether DROP SEQUENCE IF EXISTS is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_cycle(self) -> bool:
        """Whether CYCLE option is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_cache(self) -> bool:
        """Whether CACHE option is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_order(self) -> bool:
        """Whether ORDER option is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_owned_by(self) -> bool:
        """Whether OWNED BY clause is supported.

        Defaults to False.
        """
        return False

    def format_create_sequence_statement(self, expr: "CreateSequenceExpression") -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement per SQL standard.

        Args:
            expr: CreateSequenceExpression carrying the sequence name and
                optional start, increment, min/max value, cycle, cache, order,
                and owned-by options.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                specific sequence options.
        """
        from ..exceptions import UnsupportedFeatureError
        parts = ["CREATE SEQUENCE"]
        if expr.if_not_exists:
            if not self.supports_sequence_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "CREATE SEQUENCE IF NOT EXISTS",
                    f"{self.name} does not support CREATE SEQUENCE IF NOT EXISTS."
                )
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
            if not self.supports_sequence_cycle():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE CYCLE",
                    f"{self.name} does not support SEQUENCE CYCLE."
                )
            parts.append("CYCLE")
        else:
            parts.append("NO CYCLE")
        if expr.cache is not None:
            if not self.supports_sequence_cache():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE CACHE",
                    f"{self.name} does not support SEQUENCE CACHE."
                )
            parts.append(f"CACHE {expr.cache}")
        if expr.order:
            if not self.supports_sequence_order():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE ORDER",
                    f"{self.name} does not support SEQUENCE ORDER."
                )
            parts.append("ORDER")
        if expr.owned_by:
            if not self.supports_sequence_owned_by():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE OWNED BY",
                    f"{self.name} does not support SEQUENCE OWNED BY."
                )
            parts.append(f"OWNED BY {expr.owned_by}")

        return " ".join(parts), ()

    def format_drop_sequence_statement(self, expr: "DropSequenceExpression") -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement per SQL standard.

        Args:
            expr: DropSequenceExpression carrying the sequence name and
                optional ``if_exists`` flag.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                DROP SEQUENCE IF EXISTS.
        """
        from ..exceptions import UnsupportedFeatureError
        parts = ["DROP SEQUENCE"]
        if expr.if_exists:
            if not self.supports_sequence_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP SEQUENCE IF EXISTS",
                    f"{self.name} does not support DROP SEQUENCE IF EXISTS."
                )
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.sequence_name))
        return " ".join(parts), ()

    def format_alter_sequence_statement(self, expr: "AlterSequenceExpression") -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement per SQL standard.

        Args:
            expr: AlterSequenceExpression carrying the sequence name and the
                options to change (restart, start, increment, min/max value,
                cycle, cache, order, and owned-by).

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.
        """
        from ..exceptions import UnsupportedFeatureError
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
        if expr.order is not None:
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
