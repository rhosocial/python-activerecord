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
            cycle=False
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
        cache: Optional[int] = None,
        order: bool = False,
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
        self.cache = cache
        self.order = order
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
        cycle: Optional[bool] = None,
        cache: Optional[int] = None,
        order: Optional[bool] = None,
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
        self.cache = cache
        self.order = order
        self.owned_by = owned_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_alter_sequence_statement"
