# src/rhosocial/activerecord/backend/expression/statements/ddl_sequence.py
"""Sequence DDL statement expressions."""

from typing import Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..objects import Sequence

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CreateSequenceExpression(BaseExpression):
    """
    Represents a CREATE SEQUENCE statement.

    Sequences are used for generating unique numbers, typically for
    auto-increment columns. Not all databases support standalone sequences.

    Each spellable alternative has its own parameter, and "unspecified" is the
    state where none of a pair's parameters is set:

    * ``cycle`` / ``no_cycle`` -- CYCLE and NO CYCLE are two spellings;
    * ``cache`` / ``no_cache`` -- CACHE n and NO CACHE are two spellings;
    * ``order`` / ``no_order`` -- ORDER and NO ORDER are two spellings.

    Setting both parameters of a pair raises ``ValueError`` (API misuse, not a
    capability question). ``cache`` must be a positive count: ``0`` is not a
    spelling of NO CACHE -- use ``no_cache=True``.

    Examples:
        # Basic sequence
        create_seq = CreateSequenceExpression(
            dialect,
            sequence=Sequence(dialect, "user_id_seq")
        )

        # Sequence with options
        create_seq = CreateSequenceExpression(
            dialect,
            sequence=Sequence(dialect, "order_id_seq"),
            start=1000,
            increment=1,
            minvalue=1000,
            maxvalue=999999,
            no_cycle=True
        )

        # Sequence with cache
        create_seq = CreateSequenceExpression(
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
        if cycle and no_cycle:
            raise ValueError("cycle and no_cycle are mutually exclusive options")
        if cache is not None and no_cache:
            raise ValueError("cache and no_cache are mutually exclusive options")
        if order and no_order:
            raise ValueError("order and no_order are mutually exclusive options")
        if cache is not None and cache <= 0:
            raise ValueError(
                "cache must be a positive integer; use no_cache=True to spell NO CACHE"
            )
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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_sequence_statement"


class DropSequenceExpression(BaseExpression):
    """
    Represents a DROP SEQUENCE statement.

    Examples:
        # Basic drop
        drop_seq = DropSequenceExpression(
            dialect,
            sequence=Sequence(dialect, "old_seq")
        )

        # Safe drop
        drop_seq = DropSequenceExpression(
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


class AlterSequenceExpression(BaseExpression):
    """
    Represents an ALTER SEQUENCE statement.

    Examples:
        # Restart sequence
        alter_seq = AlterSequenceExpression(
            dialect,
            sequence=Sequence(dialect, "user_id_seq"),
            restart=1000
        )

        # Change increment
        alter_seq = AlterSequenceExpression(
            dialect,
            sequence=Sequence(dialect, "order_num_seq"),
            increment=2
        )

        # Set options
        alter_seq = AlterSequenceExpression(
            dialect,
            sequence=Sequence(dialect, "my_seq"),
            minvalue=1,
            maxvalue=1000000,
            cycle=True
        )

    Like :class:`CreateSequenceExpression`, each alternative of a two-spelling
    clause has its own parameter: ``cycle`` / ``no_cycle``, ``cache`` /
    ``no_cache``, ``order`` / ``no_order``. Setting both of a pair raises
    ``ValueError``; ``cache`` must be a positive count (``no_cache=True``
    spells NO CACHE).
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
        if cycle and no_cycle:
            raise ValueError("cycle and no_cycle are mutually exclusive options")
        if cache is not None and no_cache:
            raise ValueError("cache and no_cache are mutually exclusive options")
        if order and no_order:
            raise ValueError("order and no_order are mutually exclusive options")
        if cache is not None and cache <= 0:
            raise ValueError(
                "cache must be a positive integer; use no_cache=True to spell NO CACHE"
            )
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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_alter_sequence_statement"
