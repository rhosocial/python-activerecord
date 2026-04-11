# src/rhosocial/activerecord/backend/expression/statements/ddl_sequence.py
"""Sequence DDL statement expressions."""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..bases import BaseExpression

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
            sequence_name="user_id_seq"
        )

        # Sequence with options
        create_seq = CreateSequenceExpression(
            dialect,
            sequence_name="order_id_seq",
            start=1000,
            increment=1,
            minvalue=1000,
            maxvalue=999999,
            cycle=False
        )

        # Sequence with cache
        create_seq = CreateSequenceExpression(
            dialect,
            sequence_name="high_throughput_seq",
            start=1,
            cache=100
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        sequence_name: str,
        if_not_exists: bool = False,
        start: Optional[int] = None,
        increment: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cycle: bool = False,
        cache: Optional[int] = None,
        order: bool = False,
        owned_by: Optional[str] = None,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.sequence_name = sequence_name
        self.if_not_exists = if_not_exists
        self.start = start
        self.increment = increment
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.cycle = cycle
        self.cache = cache
        self.order = order
        self.owned_by = owned_by
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_sequence_statement(self)


class DropSequenceExpression(BaseExpression):
    """
    Represents a DROP SEQUENCE statement.

    Examples:
        # Basic drop
        drop_seq = DropSequenceExpression(
            dialect,
            sequence_name="old_seq"
        )

        # Safe drop
        drop_seq = DropSequenceExpression(
            dialect,
            sequence_name="deprecated_seq",
            if_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        sequence_name: str,
        if_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.sequence_name = sequence_name
        self.if_exists = if_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_sequence_statement(self)


class AlterSequenceExpression(BaseExpression):
    """
    Represents an ALTER SEQUENCE statement.

    Examples:
        # Restart sequence
        alter_seq = AlterSequenceExpression(
            dialect,
            sequence_name="user_id_seq",
            restart=1000
        )

        # Change increment
        alter_seq = AlterSequenceExpression(
            dialect,
            sequence_name="order_num_seq",
            increment=2
        )

        # Set options
        alter_seq = AlterSequenceExpression(
            dialect,
            sequence_name="my_seq",
            minvalue=1,
            maxvalue=1000000,
            cycle=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        sequence_name: str,
        restart: Optional[int] = None,
        start: Optional[int] = None,
        increment: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cycle: Optional[bool] = None,
        cache: Optional[int] = None,
        order: Optional[bool] = None,
        owned_by: Optional[str] = None,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.sequence_name = sequence_name
        self.restart = restart
        self.start = start
        self.increment = increment
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.cycle = cycle
        self.cache = cache
        self.order = order
        self.owned_by = owned_by
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_alter_sequence_statement(self)
