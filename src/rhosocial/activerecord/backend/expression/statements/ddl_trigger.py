# src/rhosocial/activerecord/backend/expression/statements/ddl_trigger.py
"""Trigger DDL statement expressions."""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate
from ..objects import Function, Table, Trigger

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class TriggerTiming(Enum):
    """Trigger execution timing."""

    BEFORE = "BEFORE"
    AFTER = "AFTER"
    INSTEAD_OF = "INSTEAD OF"


class TriggerEvent(Enum):
    """Trigger event types."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"


class TriggerLevel(Enum):
    """Trigger execution level."""

    ROW = "FOR EACH ROW"
    STATEMENT = "FOR EACH STATEMENT"


class CreateTriggerExpression(BaseExpression):
    """SQL:1999 standard CREATE TRIGGER statement.

    Examples:
        # Basic trigger
        create_trigger = CreateTriggerExpression(
            dialect,
            trigger=Trigger(dialect, "update_timestamp"),
            table=Table(dialect, "users"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function=Function(dialect, "update_updated_at_column")
        )

        # Trigger with condition
        create_trigger = CreateTriggerExpression(
            dialect,
            trigger=Trigger(dialect, "check_status"),
            table=Table(dialect, "orders"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            update_columns=["status"],
            function=Function(dialect, "validate_status"),
            level=TriggerLevel.ROW,
            condition=Column(dialect, "new.status") != Column(dialect, "old.status")
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger: "Trigger",
        table: "Table",
        timing: TriggerTiming,
        events: List[TriggerEvent],
        function: "Function",
        level: TriggerLevel = TriggerLevel.ROW,
        condition: Optional["SQLPredicate"] = None,
        update_columns: Optional[List[str]] = None,
        referencing: Optional[str] = None,
        if_not_exists: bool = False,
    ):
        super().__init__(dialect)
        self.trigger = trigger
        self.table = table
        self.timing = timing
        self.events = events
        self.function = function
        self.level = level
        self.condition = condition
        self.update_columns = update_columns
        self.referencing = referencing
        self.if_not_exists = if_not_exists

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_trigger_statement"


class DropTriggerExpression(BaseExpression):
    """SQL:1999 standard DROP TRIGGER statement.

    Examples:
        drop_trigger = DropTriggerExpression(
            dialect,
            trigger=Trigger(dialect, "update_timestamp"),
            table=Table(dialect, "users")
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger: "Trigger",
        table: Optional["Table"] = None,
        if_exists: bool = False,
    ):
        super().__init__(dialect)
        # A trigger can be named by its own name alone, so the table is
        # optional. The formatter checks its kind when one is given.
        self.trigger = trigger
        self.table = table
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_trigger_statement"
