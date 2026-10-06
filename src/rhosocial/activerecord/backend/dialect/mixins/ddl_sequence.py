# src/rhosocial/activerecord/backend/dialect/mixins/ddl_sequence.py
"""Dialect mixin for sequence DDL support (CREATE/DROP/ALTER SEQUENCE)."""
from typing import Tuple, TYPE_CHECKING

from ...expression.objects import Sequence

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

    def supports_sequence_start(self) -> bool:
        """Whether the START WITH sequence option is supported.

        This describes the ``CREATE SEQUENCE ... START WITH`` clause, which
        sets the sequence's initial value. It says nothing about the ALTER-side
        clause of the same spelling; :meth:`supports_alter_sequence_start` is
        the probe that answers for ``ALTER SEQUENCE ... START``.

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

    def supports_sequence_increment(self) -> bool:
        """Whether the INCREMENT BY sequence option is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_minvalue(self) -> bool:
        """Whether the MINVALUE sequence option is supported.

        Defaults to False.
        """
        return False

    def supports_sequence_maxvalue(self) -> bool:
        """Whether the MAXVALUE sequence option is supported.

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

        :meth:`supports_sequence` is consulted first and unconditionally, so a
        dialect that declares no sequence object refuses the statement even if
        it inherited this mixin by mistake.

        Every option the expression carries is then gated by its own probe
        before its clause is emitted -- :meth:`supports_sequence_if_not_exists`
        for IF NOT EXISTS, :meth:`supports_sequence_start` for START WITH,
        :meth:`supports_sequence_increment` for INCREMENT BY,
        :meth:`supports_sequence_minvalue` for MINVALUE,
        :meth:`supports_sequence_maxvalue` for MAXVALUE,
        :meth:`supports_sequence_cycle` for CYCLE,
        :meth:`supports_sequence_cache` for CACHE,
        :meth:`supports_sequence_order` for ORDER, and
        :meth:`supports_sequence_owned_by` for OWNED BY. An option whose probe
        is False raises ``UnsupportedFeatureError`` naming that option rather
        than dropping the clause, which would change the statement's meaning.

        ``NO CYCLE`` is the SQL default, so the clause is emitted only where
        :meth:`supports_sequence_cycle` accepts it; omitting it keeps the same
        meaning on a dialect that does not.

        Args:
            expr: CreateSequenceExpression carrying the sequence name and
                optional start, increment, min/max value, cycle, cache, order,
                and owned-by options.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``CreateSequenceExpression.sequence`` is not a Sequence. A
            table would render as a well-formed CREATE SEQUENCE over that table's
            name.
            UnsupportedFeatureError: If the dialect has no sequence object, or
                does not support an option the expression asked for.
        """
        if not isinstance(expr.sequence, Sequence):
            raise TypeError(
                f"CreateSequenceExpression.sequence must be a Sequence, "
                f"got {type(expr.sequence).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_sequence():
            raise UnsupportedFeatureError(
                self.name, "CREATE SEQUENCE",
                f"{self.name} has no sequence object to create."
            )
        parts = ["CREATE SEQUENCE"]
        if expr.if_not_exists:
            if not self.supports_sequence_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "CREATE SEQUENCE IF NOT EXISTS",
                    f"{self.name} does not support CREATE SEQUENCE IF NOT EXISTS."
                )
            parts.append("IF NOT EXISTS")
        parts.append(expr.sequence.to_sql()[0])

        if expr.start is not None:
            if not self.supports_sequence_start():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE START",
                    f"{self.name} does not support the START WITH sequence option."
                )
            parts.append(f"START WITH {expr.start}")
        if expr.increment is not None:
            if not self.supports_sequence_increment():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE INCREMENT",
                    f"{self.name} does not support the INCREMENT BY sequence option."
                )
            parts.append(f"INCREMENT BY {expr.increment}")
        if expr.minvalue is not None:
            if not self.supports_sequence_minvalue():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE MINVALUE",
                    f"{self.name} does not support the MINVALUE sequence option."
                )
            parts.append(f"MINVALUE {expr.minvalue}")
        if expr.maxvalue is not None:
            if not self.supports_sequence_maxvalue():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE MAXVALUE",
                    f"{self.name} does not support the MAXVALUE sequence option."
                )
            parts.append(f"MAXVALUE {expr.maxvalue}")
        if expr.cycle:
            if not self.supports_sequence_cycle():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE CYCLE",
                    f"{self.name} does not support the CYCLE sequence option."
                )
            parts.append("CYCLE")
        elif self.supports_sequence_cycle():
            # NO CYCLE is the default; only spell it where the words are legal.
            parts.append("NO CYCLE")
        if expr.cache is not None:
            if not self.supports_sequence_cache():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE CACHE",
                    f"{self.name} does not support the CACHE sequence option."
                )
            parts.append(f"CACHE {expr.cache}")
        if expr.order:
            if not self.supports_sequence_order():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE ORDER",
                    f"{self.name} does not support the ORDER sequence option."
                )
            parts.append("ORDER")
        if expr.owned_by:
            if not self.supports_sequence_owned_by():
                raise UnsupportedFeatureError(
                    self.name, "SEQUENCE OWNED BY",
                    f"{self.name} does not support the OWNED BY sequence option."
                )
            parts.append(f"OWNED BY {expr.owned_by}")

        return " ".join(parts), ()

    def format_drop_sequence_statement(self, expr: "DropSequenceExpression") -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement per SQL standard.

        :meth:`supports_sequence` is consulted first and unconditionally, so a
        dialect that declares no sequence object refuses the statement even if
        it inherited this mixin by mistake. ``IF EXISTS`` is then gated by
        :meth:`supports_sequence_if_exists`; when the expression asks for it
        and the probe is False, the formatter raises ``UnsupportedFeatureError``
        instead of dropping the clause.

        Args:
            expr: DropSequenceExpression carrying the sequence name and
                optional ``if_exists`` flag.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``DropSequenceExpression.sequence`` is not a Sequence. A
            table would render as a well-formed DROP SEQUENCE over that table's
            name.
            UnsupportedFeatureError: If the dialect has no sequence object, or
                does not support DROP SEQUENCE IF EXISTS.
        """
        if not isinstance(expr.sequence, Sequence):
            raise TypeError(
                f"DropSequenceExpression.sequence must be a Sequence, "
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

    def format_alter_sequence_statement(self, expr: "AlterSequenceExpression") -> Tuple[str, tuple]:
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

        ``cycle=False`` asks for the SQL default, so ``NO CYCLE`` is emitted
        only where :meth:`supports_sequence_cycle` accepts the words; an
        explicit ``cycle=True`` whose probe is False raises.

        Args:
            expr: AlterSequenceExpression carrying the sequence name and the
                options to change (restart, start, increment, min/max value,
                cycle, cache, order, and owned-by).

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``AlterSequenceExpression.sequence`` is not a Sequence. A
            table would render as a well-formed ALTER SEQUENCE over that table's
            name.
            UnsupportedFeatureError: If the dialect has no sequence object, or
                does not support an option the expression asked for.
        """
        if not isinstance(expr.sequence, Sequence):
            raise TypeError(
                f"AlterSequenceExpression.sequence must be a Sequence, "
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
        if expr.cycle is not None:
            if expr.cycle:
                if not self.supports_sequence_cycle():
                    raise UnsupportedFeatureError(
                        self.name, "ALTER SEQUENCE CYCLE",
                        f"{self.name} does not support the CYCLE sequence option."
                    )
                parts.append("CYCLE")
            elif self.supports_sequence_cycle():
                # NO CYCLE is the default; only spell it where it is legal.
                parts.append("NO CYCLE")
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
