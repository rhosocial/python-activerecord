# src/rhosocial/activerecord/backend/expression/statements/ddl_trigger.py
"""Trigger DDL statement expressions."""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from ..core import TableExpression
from ..bases import BaseExpression, SQLPredicate

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
    """
    SQL:1999 standard CREATE TRIGGER statement.

    Examples:
        # Basic trigger
        create_trigger = CreateTriggerExpression(
            dialect,
            trigger_name="update_timestamp",
            table=TableExpression(dialect, "users"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function_name="update_updated_at_column"
        )

        # Trigger with condition
        create_trigger = CreateTriggerExpression(
            dialect,
            trigger_name="check_status",
            table=TableExpression(dialect, "orders"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            update_columns=["status"],
            function_name="validate_status",
            level=TriggerLevel.ROW,
            condition=Column(dialect, "new.status") != Column(dialect, "old.status")
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_trigger_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger_name: str,
        table: "TableExpression",
        timing: TriggerTiming,
        events: List[TriggerEvent],
        function_name: "TableExpression",
        level: TriggerLevel = TriggerLevel.ROW,
        condition: Optional["SQLPredicate"] = None,
        update_columns: Optional[List[str]] = None,
        referencing: Optional[str] = None,
        if_not_exists: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table the trigger is attached to. Carries its own
                namespace, independently of ``schema_name``.
            function_name: The function the trigger body calls, as a
                TableExpression carrying its own namespace.
            schema_name: Namespace to qualify the trigger with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.trigger_name = trigger_name
        self.schema_name = schema_name
        self.table = table
        self.function = function_name
        self.timing = timing
        self.events = events
        
        self.level = level
        self.condition = condition
        self.update_columns = update_columns
        self.referencing = referencing
        self.if_not_exists = if_not_exists


class DropTriggerExpression(BaseExpression):
    """
    SQL:1999 standard DROP TRIGGER statement.

    Examples:
        drop_trigger = DropTriggerExpression(
            dialect,
            trigger_name="update_timestamp",
            table=TableExpression(dialect, "users")
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_trigger_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger_name: str,
        table: Optional["TableExpression"] = None,
        if_exists: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table carrying the trigger, or None to omit the
                ``ON`` clause. Carries its own namespace, independently of
                ``schema_name``.
            schema_name: Namespace to qualify the trigger with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.trigger_name = trigger_name
        self.schema_name = schema_name
        self.table = table
        self.if_exists = if_exists
