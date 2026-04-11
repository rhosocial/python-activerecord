# src/rhosocial/activerecord/backend/expression/statements/ddl_trigger.py
"""Trigger DDL statement expressions."""

from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

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
    """SQL:1999 standard CREATE TRIGGER statement.

    Examples:
        # Basic trigger
        create_trigger = CreateTriggerExpression(
            dialect,
            trigger_name="update_timestamp",
            table_name="users",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function_name="update_updated_at_column"
        )

        # Trigger with condition
        create_trigger = CreateTriggerExpression(
            dialect,
            trigger_name="check_status",
            table_name="orders",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            update_columns=["status"],
            function_name="validate_status",
            level=TriggerLevel.ROW,
            condition=Column(dialect, "new.status") != Column(dialect, "old.status")
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger_name: str,
        table_name: str,
        timing: TriggerTiming,
        events: List[TriggerEvent],
        function_name: str,
        level: TriggerLevel = TriggerLevel.ROW,
        condition: Optional["SQLPredicate"] = None,
        update_columns: Optional[List[str]] = None,
        referencing: Optional[str] = None,
        if_not_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.trigger_name = trigger_name
        self.table_name = table_name
        self.timing = timing
        self.events = events
        self.function_name = function_name
        self.level = level
        self.condition = condition
        self.update_columns = update_columns
        self.referencing = referencing
        self.if_not_exists = if_not_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_trigger_statement(self)


class DropTriggerExpression(BaseExpression):
    """SQL:1999 standard DROP TRIGGER statement.

    Examples:
        drop_trigger = DropTriggerExpression(
            dialect,
            trigger_name="update_timestamp",
            table_name="users"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger_name: str,
        table_name: Optional[str] = None,
        if_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.trigger_name = trigger_name
        self.table_name = table_name
        self.if_exists = if_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_trigger_statement(self)
