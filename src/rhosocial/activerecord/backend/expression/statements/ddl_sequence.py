# src/rhosocial/activerecord/backend/expression/statements/ddl_sequence.py
"""Sequence DDL statement expressions."""

from typing import Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..objects import Sequence

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CreateSequenceStatement(BaseExpression):
    """
    Represents a CREATE SEQUENCE statement.

    Sequences are used for generating unique numbers, typically for
    auto-increment columns. Not all databases support standalone sequences.

    Each spellable alternative has its own parameter, and "unspecified" is the
    state where none of a pair's parameters is set:

    * ``cycle`` / ``no_cycle`` -- CYCLE and NO CYCLE are two spellings;
    * ``cache`` / ``no_cache`` -- CACHE n and NO CACHE are two spellings;
    * ``order`` / ``no_order`` -- ORDER and NO ORDER are two spellings.

    Setting both parameters of a pair is invalid (API misuse, not a capability
    question), and ``cache`` must be a positive count: ``0`` is not a spelling
    of NO CACHE -- use ``no_cache=True``. The constructor only collects those
    values; :meth:`validate` (or any of the ``validate_*`` methods) reports the
    refusal, and a backend formatter decides whether to call it.

    Examples:
        # Basic sequence
        create_seq = CreateSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "user_id_seq")
        )

        # Sequence with options
        create_seq = CreateSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "order_id_seq"),
            start=1000,
            increment=1,
            minvalue=1000,
            maxvalue=999999,
            no_cycle=True
        )

        # Sequence with cache
        create_seq = CreateSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "high_throughput_seq"),
            start=1,
            cache=100
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        sequence: "Sequence",
        if_not_exists: bool = False,
        start: Optional[int] = None,
        increment: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cycle: bool = False,
        no_cycle: bool = False,
        cache: Optional[int] = None,
        no_cache: bool = False,
        order: bool = False,
        no_order: bool = False,
        owned_by: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.sequence = sequence
        self.if_not_exists = if_not_exists
        self.start = start
        self.increment = increment
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.cycle = cycle
        self.no_cycle = no_cycle
        self.cache = cache
        self.no_cache = no_cache
        self.order = order
        self.no_order = no_order
        self.owned_by = owned_by

    def validate_cycle_options(self) -> None:
        """Refuse CYCLE and NO CYCLE being requested together."""
        self.require_exclusive_options(self.cycle, self.no_cycle, "cycle", "no_cycle")

    def validate_cache_options(self) -> None:
        """Refuse CACHE n and NO CACHE being requested together."""
        self.require_exclusive_options(self.cache is not None, self.no_cache, "cache", "no_cache")

    def validate_order_options(self) -> None:
        """Refuse ORDER and NO ORDER being requested together."""
        self.require_exclusive_options(self.order, self.no_order, "order", "no_order")

    def validate_cache_value(self) -> None:
        """Refuse a non-positive CACHE count; NO CACHE has its own spelling."""
        if self.cache is not None and self.cache <= 0:
            raise ValueError(
                "cache must be a positive integer; use no_cache=True to spell NO CACHE"
            )

    def validate(self, strict: bool = True) -> None:
        """Public, opt-in validation; ``_render()`` never calls it.

        A backend formatter may call this (or just the ``validate_*`` method it
        cares about) before spelling the clause. The order matches the original
        constructor checks so a malformed combination reports the same error.
        """
        if not strict:
            return
        self.validate_cycle_options()
        self.validate_cache_options()
        self.validate_order_options()
        self.validate_cache_value()

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_sequence_statement"


class DropSequenceStatement(BaseExpression):
    """
    Represents a DROP SEQUENCE statement.

    Examples:
        # Basic drop
        drop_seq = DropSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "old_seq")
        )

        # Safe drop
        drop_seq = DropSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "deprecated_seq"),
            if_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        sequence: "Sequence",
        if_exists: bool = False,
    ):
        super().__init__(dialect)
        self.sequence = sequence
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_sequence_statement"


class AlterSequenceStatement(BaseExpression):
    """
    Represents an ALTER SEQUENCE statement.

    Examples:
        # Restart sequence
        alter_seq = AlterSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "user_id_seq"),
            restart=1000
        )

        # Change increment
        alter_seq = AlterSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "order_num_seq"),
            increment=2
        )

        # Set options
        alter_seq = AlterSequenceStatement(
            dialect,
            sequence=Sequence(dialect, "my_seq"),
            minvalue=1,
            maxvalue=1000000,
            cycle=True
        )

    Like :class:`CreateSequenceStatement`, each alternative of a two-spelling
    clause has its own parameter: ``cycle`` / ``no_cycle``, ``cache`` /
    ``no_cache``, ``order`` / ``no_order``. Setting both of a pair is invalid;
    ``cache`` must be a positive count (``no_cache=True`` spells NO CACHE).
    The constructor collects them; :meth:`validate` reports the refusal.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        sequence: "Sequence",
        restart: Optional[int] = None,
        start: Optional[int] = None,
        increment: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cycle: bool = False,
        no_cycle: bool = False,
        cache: Optional[int] = None,
        no_cache: bool = False,
        order: bool = False,
        no_order: bool = False,
        owned_by: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.sequence = sequence
        self.restart = restart
        self.start = start
        self.increment = increment
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.cycle = cycle
        self.no_cycle = no_cycle
        self.cache = cache
        self.no_cache = no_cache
        self.order = order
        self.no_order = no_order
        self.owned_by = owned_by

    def validate_cycle_options(self) -> None:
        """Refuse CYCLE and NO CYCLE being requested together."""
        self.require_exclusive_options(self.cycle, self.no_cycle, "cycle", "no_cycle")

    def validate_cache_options(self) -> None:
        """Refuse CACHE n and NO CACHE being requested together."""
        self.require_exclusive_options(self.cache is not None, self.no_cache, "cache", "no_cache")

    def validate_order_options(self) -> None:
        """Refuse ORDER and NO ORDER being requested together."""
        self.require_exclusive_options(self.order, self.no_order, "order", "no_order")

    def validate_cache_value(self) -> None:
        """Refuse a non-positive CACHE count; NO CACHE has its own spelling."""
        if self.cache is not None and self.cache <= 0:
            raise ValueError(
                "cache must be a positive integer; use no_cache=True to spell NO CACHE"
            )

    def validate(self, strict: bool = True) -> None:
        """Public, opt-in validation; ``_render()`` never calls it.

        A backend formatter may call this (or just the ``validate_*`` method it
        cares about) before spelling the clause. The order matches the original
        constructor checks so a malformed combination reports the same error.
        """
        if not strict:
            return
        self.validate_cycle_options()
        self.validate_cache_options()
        self.validate_order_options()
        self.validate_cache_value()

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_alter_sequence_statement"
