# src/rhosocial/activerecord/backend/expression/statements/ddl_alter.py
"""ALTER TABLE DDL statement expressions."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLQueryAndParams
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
    MODIFY_COLUMN = "MODIFY COLUMN"  # MySQL/MariaDB specific
    CHANGE_COLUMN = "CHANGE COLUMN"  # MySQL/MariaDB specific


class AlterTableAction(BaseExpression):
    """Abstract base class for a single action within an ALTER TABLE statement.

    All ALTER TABLE action subclasses inherit from BaseExpression, binding
    a dialect at construction time and delegating SQL generation to the
    dialect's format_*_action methods via to_sql().
    """

    action_type: AlterTableActionType

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegate to the dialect's format_* method based on action type."""
        dialect = self.dialect
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
        elif self.action_type == AlterTableActionType.MODIFY_COLUMN:
            return dialect.format_modify_column_action(self)
        elif self.action_type == AlterTableActionType.CHANGE_COLUMN:
            return dialect.format_change_column_action(self)
        else:
            # Handle unknown action types
            return f"PROCESS {type(self).__name__}", ()


class AddColumn(AlterTableAction):
    """Represents an 'ADD COLUMN' action per SQL standard."""

    action_type: AlterTableActionType = AlterTableActionType.ADD_COLUMN
    column: ColumnDefinition
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: ColumnDefinition,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.column: ColumnDefinition = column
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class DropColumn(AlterTableAction):
    """Represents a 'DROP COLUMN' action per SQL standard."""

    action_type: AlterTableActionType = AlterTableActionType.DROP_COLUMN
    column_name: str
    if_exists: bool
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column_name: str,
        *,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.column_name: str = column_name
        self.if_exists: bool = if_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class ColumnAlterOperation(Enum):
    """SQL standard column operation types"""

    SET_DEFAULT = "SET DEFAULT"
    DROP_DEFAULT = "DROP DEFAULT"
    SET_NOT_NULL = "SET NOT NULL"  # Non-standard but widely supported
    DROP_NOT_NULL = "DROP NOT NULL"  # Non-standard but widely supported


class AlterColumn(AlterTableAction):
    """Represents an 'ALTER COLUMN' action per SQL standard."""

    action_type: AlterTableActionType = AlterTableActionType.ALTER_COLUMN
    column_name: str
    operation: Union[ColumnAlterOperation, str]
    new_value: Any
    cascade: bool
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column_name: str,
        operation: Union[ColumnAlterOperation, str],
        *,
        new_value: Any = None,
        cascade: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.column_name: str = column_name
        self.operation: Union[ColumnAlterOperation, str] = operation
        self.new_value: Any = new_value
        self.cascade: bool = cascade
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class AddTableConstraint(AlterTableAction):
    """SQL standard ADD CONSTRAINT operation"""

    action_type: AlterTableActionType = AlterTableActionType.ADD_CONSTRAINT
    constraint: TableConstraint
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        constraint: TableConstraint,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.constraint: TableConstraint = constraint
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class DropTableConstraint(AlterTableAction):
    """SQL standard DROP CONSTRAINT operation"""

    action_type: AlterTableActionType = AlterTableActionType.DROP_CONSTRAINT
    constraint_name: str
    cascade: bool
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        constraint_name: str,
        *,
        cascade: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.constraint_name: str = constraint_name
        self.cascade: bool = cascade
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class RenameColumn(AlterTableAction):
    """SQL standard RENAME COLUMN operation"""

    action_type: AlterTableActionType = AlterTableActionType.RENAME_COLUMN
    old_name: str
    new_name: str
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        old_name: str,
        new_name: str,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.old_name: str = old_name
        self.new_name: str = new_name
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class RenameTable(AlterTableAction):
    """SQL standard RENAME TABLE operation"""

    action_type: AlterTableActionType = AlterTableActionType.RENAME_TABLE
    old_name: str
    new_name: str
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        old_name: str,
        new_name: str,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.old_name: str = old_name
        self.new_name: str = new_name
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class AddConstraint(AlterTableAction):
    """Represents an 'ADD CONSTRAINT' action."""

    action_type: AlterTableActionType = AlterTableActionType.ADD_CONSTRAINT
    constraint: TableConstraint

    def __init__(
        self,
        dialect: "SQLDialectBase",
        constraint: TableConstraint,
    ) -> None:
        super().__init__(dialect)
        self.constraint: TableConstraint = constraint


class DropConstraint(AlterTableAction):
    """Represents a 'DROP CONSTRAINT' action."""

    action_type: AlterTableActionType = AlterTableActionType.DROP_CONSTRAINT
    constraint_name: str
    cascade: bool

    def __init__(
        self,
        dialect: "SQLDialectBase",
        constraint_name: str,
        *,
        cascade: bool = False,
    ) -> None:
        super().__init__(dialect)
        self.constraint_name: str = constraint_name
        self.cascade: bool = cascade


class RenameObject(AlterTableAction):
    """Represents a 'RENAME' action for columns or tables."""

    action_type: AlterTableActionType = AlterTableActionType.RENAME_COLUMN
    old_name: str
    new_name: str
    object_type: str
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        old_name: str,
        new_name: str,
        *,
        object_type: str = "COLUMN",
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.old_name: str = old_name
        self.new_name: str = new_name
        self.object_type: str = object_type
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class AddIndex(AlterTableAction):
    """Represents an 'ADD INDEX' action."""

    action_type: AlterTableActionType = AlterTableActionType.ADD_INDEX
    index: IndexDefinition

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: IndexDefinition,
    ) -> None:
        super().__init__(dialect)
        self.index: IndexDefinition = index


class DropIndex(AlterTableAction):
    """Represents a 'DROP INDEX' action."""

    action_type: AlterTableActionType = AlterTableActionType.DROP_INDEX
    index_name: str
    if_exists: bool

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        *,
        if_exists: bool = False,
    ) -> None:
        super().__init__(dialect)
        self.index_name: str = index_name
        self.if_exists: bool = if_exists


class ModifyColumn(AlterTableAction):
    """Represents a 'MODIFY COLUMN' action.

    Redefines a column with a complete new specification.
    This is MySQL/MariaDB specific syntax; the SQL standard
    uses ALTER COLUMN for individual property changes.
    """

    action_type: AlterTableActionType = AlterTableActionType.MODIFY_COLUMN
    column: ColumnDefinition
    first: bool
    after_column: Optional[str]
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: ColumnDefinition,
        *,
        first: bool = False,
        after_column: Optional[str] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.column: ColumnDefinition = column
        self.first: bool = first
        self.after_column: Optional[str] = after_column
        self.dialect_options: Dict[str, Any] = dialect_options or {}


class ChangeColumn(AlterTableAction):
    """Represents a 'CHANGE COLUMN' action.

    Renames a column and redefines it with a complete new specification.
    This is MySQL/MariaDB specific syntax.
    """

    action_type: AlterTableActionType = AlterTableActionType.CHANGE_COLUMN
    old_name: str
    column: ColumnDefinition
    first: bool
    after_column: Optional[str]
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        old_name: str,
        column: ColumnDefinition,
        *,
        first: bool = False,
        after_column: Optional[str] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(dialect)
        self.old_name: str = old_name
        self.column: ColumnDefinition = column
        self.first: bool = first
        self.after_column: Optional[str] = after_column
        self.dialect_options: Dict[str, Any] = dialect_options or {}


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
            actions=[AddColumn(dialect, column=ColumnDefinition("email", "VARCHAR(100)"))]
        )

        # Drop column
        alter_expr = AlterTableExpression(
            dialect,
            table_name="products",
            actions=[DropColumn(dialect, column_name="description")]
        )

        # Multiple actions in one statement
        alter_expr = AlterTableExpression(
            dialect,
            table_name="orders",
            actions=[
                AddColumn(dialect, column=ColumnDefinition("status", "VARCHAR(20)")),
                RenameColumn(dialect, old_name="id", new_name="order_id")
            ]
        )

        # Add constraint
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[
                AddTableConstraint(
                    dialect,
                    constraint=TableConstraint(
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
                    dialect,
                    column_name="price",
                    operation=ColumnAlterOperation.SET_DEFAULT,
                    new_value="0.00"
                )
            ]
        )
    """

    table_name: str
    actions: List[AlterTableAction]
    dialect_options: Dict[str, Any]

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        actions: List[AlterTableAction],
        *,  # Force keyword arguments
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize an ALTER TABLE expression with the specified modifications per SQL standard.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table_name: Name of the table to alter
            actions: List of actions to perform on the table (per SQL standard)
            dialect_options: Additional database-specific parameters

        Raises:
            ValueError: If required parameters are missing or invalid
            TypeError: If any action is not an AlterTableAction instance
        """
        super().__init__(dialect)
        self.table_name: str = table_name
        # Validate all actions are AlterTableAction instances (dialect already bound)
        for action in actions:
            if not isinstance(action, AlterTableAction):
                raise TypeError(f"actions must be AlterTableAction instances, got {type(action).__name__}")
        self.actions: List[AlterTableAction] = list(actions)
        self.dialect_options: Dict[str, Any] = dialect_options or {}

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
