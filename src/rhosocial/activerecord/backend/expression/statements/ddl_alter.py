# src/rhosocial/activerecord/backend/expression/statements/ddl_alter.py
"""ALTER TABLE DDL statement expressions."""

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from ..bases import BaseExpression
from .ddl_table import ColumnDefinition, TableConstraint, IndexDefinition

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class AlterTableActionType(Enum):
    """Type of action for ALTER TABLE statement."""

    ADD_COLUMN = "ADD COLUMN"
    DROP_COLUMN = "DROP COLUMN"
    ALTER_COLUMN = "ALTER COLUMN"
    ADD_CONSTRAINT = "ADD CONSTRAINT"
    DROP_CONSTRAINT = "DROP CONSTRAINT"
    RENAME_COLUMN = "RENAME COLUMN"
    RENAME_TABLE = "RENAME TABLE"
    ADD_INDEX = "ADD INDEX"
    DROP_INDEX = "DROP INDEX"


class AlterTableAction(abc.ABC):
    """Abstract base class for a single action within an ALTER TABLE statement."""

    action_type: AlterTableActionType

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to the dialect's format_* method based on action type."""
        # Access dialect from the object's __dict__ which is set by AlterTableExpression
        if hasattr(self, "_dialect"):
            dialect = self._dialect
            if self.action_type == AlterTableActionType.ADD_COLUMN:
                return dialect.format_add_column_action(self)
            elif self.action_type == AlterTableActionType.DROP_COLUMN:
                return dialect.format_drop_column_action(self)
            elif self.action_type == AlterTableActionType.ALTER_COLUMN:
                return dialect.format_alter_column_action(self)
            elif self.action_type == AlterTableActionType.ADD_CONSTRAINT:
                return dialect.format_add_table_constraint_action(self)
            elif self.action_type == AlterTableActionType.DROP_CONSTRAINT:
                return dialect.format_drop_table_constraint_action(self)
            elif self.action_type == AlterTableActionType.RENAME_COLUMN:
                return dialect.format_rename_column_action(self)
            elif self.action_type == AlterTableActionType.RENAME_TABLE:
                return dialect.format_rename_table_action(self)
            elif self.action_type == AlterTableActionType.ADD_INDEX:
                return dialect.format_add_index_action(self)
            elif self.action_type == AlterTableActionType.DROP_INDEX:
                return dialect.format_drop_index_action(self)
            else:
                # Handle unknown action types
                return f"PROCESS {type(self).__name__}", ()
        else:
            raise AttributeError(
                "Dialect not set for AlterTableAction. It should be set by the parent AlterTableExpression."
            )


@dataclass
class AddColumn(AlterTableAction):
    """Represents an 'ADD COLUMN' action per SQL standard."""

    column: ColumnDefinition
    action_type: AlterTableActionType = AlterTableActionType.ADD_COLUMN
    dialect_options: Optional[Dict[str, Any]] = None  # dialect-specific options


@dataclass
class DropColumn(AlterTableAction):
    """Represents a 'DROP COLUMN' action per SQL standard."""

    column_name: str
    action_type: AlterTableActionType = AlterTableActionType.DROP_COLUMN
    if_exists: bool = False  # Non-standard but widely supported
    dialect_options: Optional[Dict[str, Any]] = None  # dialect-specific options


class ColumnAlterOperation(Enum):
    """SQL standard column operation types"""

    SET_DEFAULT = "SET DEFAULT"
    DROP_DEFAULT = "DROP DEFAULT"
    SET_NOT_NULL = "SET NOT NULL"  # Non-standard but widely supported
    DROP_NOT_NULL = "DROP NOT NULL"  # Non-standard but widely supported


@dataclass
class AlterColumn(AlterTableAction):
    """Represents an 'ALTER COLUMN' action per SQL standard."""

    column_name: str
    operation: Union[ColumnAlterOperation, str]  # operation type
    action_type: AlterTableActionType = AlterTableActionType.ALTER_COLUMN
    new_value: Any = None  # default value, etc.
    cascade: bool = False  # For constraint modifications
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class AddTableConstraint(AlterTableAction):
    """SQL standard ADD CONSTRAINT operation"""

    constraint: TableConstraint
    action_type: AlterTableActionType = AlterTableActionType.ADD_CONSTRAINT
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class DropTableConstraint(AlterTableAction):
    """SQL standard DROP CONSTRAINT operation"""

    constraint_name: str
    action_type: AlterTableActionType = AlterTableActionType.DROP_CONSTRAINT
    cascade: bool = False  # For dialect implementation
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class RenameColumn(AlterTableAction):
    """SQL standard RENAME COLUMN operation"""

    old_name: str
    new_name: str
    action_type: AlterTableActionType = AlterTableActionType.RENAME_COLUMN
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class RenameTable(AlterTableAction):
    """SQL standard RENAME TABLE operation"""

    old_name: str
    new_name: str
    action_type: AlterTableActionType = AlterTableActionType.RENAME_TABLE
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class AddConstraint(AlterTableAction):
    """Represents an 'ADD CONSTRAINT' action."""

    constraint: TableConstraint
    action_type: AlterTableActionType = AlterTableActionType.ADD_CONSTRAINT


@dataclass
class DropConstraint(AlterTableAction):
    """Represents a 'DROP CONSTRAINT' action."""

    constraint_name: str
    cascade: bool = False  # Whether to CASCADE the constraint drop
    action_type: AlterTableActionType = AlterTableActionType.DROP_CONSTRAINT


@dataclass
class RenameObject(AlterTableAction):
    """Represents a 'RENAME' action for columns or tables."""

    old_name: str
    new_name: str
    action_type: AlterTableActionType = AlterTableActionType.RENAME_COLUMN
    object_type: str = "COLUMN"  # "COLUMN", "TABLE", or "INDEX"
    dialect_options: Optional[Dict[str, Any]] = None  # dialect-specific options


@dataclass
class AddIndex(AlterTableAction):
    """Represents an 'ADD INDEX' action."""

    index: IndexDefinition
    action_type: AlterTableActionType = AlterTableActionType.ADD_INDEX


@dataclass
class DropIndex(AlterTableAction):
    """Represents a 'DROP INDEX' action."""

    index_name: str
    if_exists: bool = False
    action_type: AlterTableActionType = AlterTableActionType.DROP_INDEX


class AlterTableExpression(BaseExpression):
    """
    Represents a comprehensive ALTER TABLE statement supporting SQL standard functionality.

    The ALTER TABLE statement allows for modification of an existing table's structure,
    including adding/dropping columns, altering column properties, managing constraints
    and indexes, and renaming objects per SQL standard. Different SQL databases support
    different subsets of ALTER TABLE functionality, with variations in syntax.

    This class collects all ALTER TABLE parameters and delegates the actual SQL generation
    to a backend-specific dialect for database-specific syntax.

    Examples:
        # Add column
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[AddColumn(ColumnDefinition("email", "VARCHAR(100)"))]
        )

        # Drop column
        alter_expr = AlterTableExpression(
            dialect,
            table_name="products",
            actions=[DropColumn("description")]
        )

        # Multiple actions in one statement
        alter_expr = AlterTableExpression(
            dialect,
            table_name="orders",
            actions=[
                AddColumn(ColumnDefinition("status", "VARCHAR(20)")),
                RenameColumn("id", "order_id")
            ]
        )

        # Add constraint
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[
                AddTableConstraint(
                    TableConstraint(
                        constraint_type=TableConstraintType.CHECK,
                        check_condition=Column(dialect, "age") > Literal(dialect, 0)
                    )
                )
            ]
        )

        # Alter column properties
        alter_expr = AlterTableExpression(
            dialect,
            table_name="products",
            actions=[
                AlterColumn(
                    "price",
                    operation=ColumnAlterOperation.SET_DEFAULT,
                    new_value="0.00"
                )
            ]
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        actions: List[
            Union[
                AlterTableAction,
                "AddTableConstraint",
                "DropTableConstraint",
                "RenameColumn",
                "RenameTable",
                "AlterColumn",
            ]
        ],
        *,  # Force keyword arguments
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an ALTER TABLE expression with the specified modifications per SQL standard.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table_name: Name of the table to alter
            actions: List of actions to perform on the table (per SQL standard)
            dialect_options: Additional database-specific parameters

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        super().__init__(dialect)
        self.table_name = table_name
        # Inject dialect to all actions for ToSQLProtocol compliance
        self.actions = []
        for action in actions:
            action._dialect = dialect
            self.actions.append(action)
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """
        Generate the SQL string and parameters for this ALTER TABLE expression per SQL standard.

        This method delegates the SQL generation to the configured dialect, allowing for
        database-specific variations in ALTER TABLE syntax while maintaining standard compliance.

        Returns:
            A tuple containing:
            - str: The complete ALTER TABLE SQL string
            - tuple: The parameter values for prepared statement execution
        """
        return self.dialect.format_alter_table_statement(self)
