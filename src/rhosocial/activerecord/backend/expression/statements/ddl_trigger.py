# src/rhosocial/activerecord/backend/expression/statements/ddl_trigger.py
"""Trigger DDL statement expressions."""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate
from ..objects import Function, Table, Trigger

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class TriggerTiming(str, Enum):
    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    """Trigger execution timing."""

    BEFORE = "BEFORE"
    AFTER = "AFTER"
    INSTEAD_OF = "INSTEAD OF"


class TriggerEvent(str, Enum):
    """Trigger event types."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"


class TriggerLevel(str, Enum):
    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    """Trigger execution level."""

    ROW = "FOR EACH ROW"
    STATEMENT = "FOR EACH STATEMENT"


class CreateTriggerStatement(BaseExpression):
    """SQL:1999 standard CREATE TRIGGER statement.

    :attr:`function` is required but may be ``None``: a trigger body is either a
    function call (PostgreSQL-style) or a list of statements (SQLite / MySQL /
    SQL Server style), and the two are the same node in this grammar. ``None``
    is therefore a value the position carries, not a missing field.

    Examples:
        # Basic trigger
        create_trigger = CreateTriggerStatement(
            dialect,
            trigger=Trigger(dialect, "update_timestamp"),
            table=Table(dialect, "users"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function=Function(dialect, "update_updated_at_column")
        )

        # Trigger with a statement body (SQLite / MySQL / SQL Server style).
        # ``function`` is required positionally, so a body-only trigger says
        # ``function=None`` instead of omitting it.
        create_trigger = CreateTriggerStatement(
            dialect,
            trigger=Trigger(dialect, "update_user_timestamp"),
            table=Table(dialect, "users"),
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.UPDATE],
            function=None,
            body=[UpdateStatement(dialect, table=Table(dialect, "users"),
                                  assignments={"created_at": CurrentTimestampFunction(dialect)})]
        )

        # Trigger with condition
        create_trigger = CreateTriggerStatement(
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
        function: Optional["Function"],
        level: TriggerLevel = TriggerLevel.ROW,
        condition: Optional["SQLPredicate"] = None,
        update_columns: Optional[List[str]] = None,
        referencing: Optional[str] = None,
        if_not_exists: bool = False,
        body: Optional[List[BaseExpression]] = None,
    ):
        super().__init__(dialect)
        # Collect only: whether a body is present at all is decided by
        # check_renderable(), so a trigger read back from an artifact always
        # builds and an incomplete one is refused by name at render time.
        self.trigger = trigger
        self.table = table
        self.timing = timing
        self.events = events
        self.function = function
        self.body = tuple(body) if body is not None else None
        self.level = level
        self.condition = condition
        self.update_columns = update_columns
        self.referencing = referencing
        self.if_not_exists = if_not_exists

    #: A trigger body is either a function call or own statements; ``None`` is
    #: the value this position carries when the other one is used.
    NULLABLE_REQUIRED = frozenset({"function"})

    def check_renderable(self) -> None:
        """A trigger needs exactly one of ``function`` / ``body``."""
        if (self.function is None) == (self.body is None):
            raise TypeError(
                f"{type(self).__name__} needs exactly one of function or body: "
                "a trigger either executes a function or carries own statements"
            )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_trigger_statement"


class DropTriggerStatement(BaseExpression):
    """SQL:1999 standard DROP TRIGGER statement.

    Examples:
        drop_trigger = DropTriggerStatement(
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
