# src/rhosocial/activerecord/backend/expression/statements/__init__.py
"""
SQL DML (Data Manipulation Language), DQL (Data Query Language),
and DDL (Data Definition Language) statements.

These expression classes are responsible for collecting the parameters and structure
for a given SQL statement and delegating the actual SQL string generation
to a backend-specific dialect.
"""

# DQL
from .dql import SelectModifier, QueryExpression

# Re-export WhereClause and ForUpdateClause from query_parts for backward compatibility
from ..query_parts import WhereClause, ForUpdateClause

# EXPLAIN
from .explain import ExplainType, ExplainFormat, ExplainOptions, ExplainExpression

# DML
from .dml import (
    MergeActionType,
    MergeAction,
    MergeExpression,
    ReturningClause,
    DeleteExpression,
    UpdateExpression,
    InsertDataSource,
    ValuesSource,
    SelectSource,
    DefaultValuesSource,
    OnConflictClause,
    InsertExpression,
)

# Table DDL
from .ddl_table import (
    ColumnConstraintType,
    ColumnConstraint,
    GeneratedColumnType,
    ColumnDefinition,
    TableConstraintType,
    ReferentialAction,
    ConstraintValidation,
    TableConstraint,
    ForeignKeyConstraint,
    IndexDefinition,
    CreateTableExpression,
    DropTableExpression,
)

# ALTER TABLE DDL
from .ddl_alter import (
    AlterTableActionType,
    AlterTableAction,
    AddColumn,
    DropColumn,
    ColumnAlterOperation,
    AlterColumn,
    AddTableConstraint,
    DropTableConstraint,
    RenameColumn,
    RenameTable,
    AddConstraint,
    DropConstraint,
    RenameObject,
    AddIndex,
    DropIndex,
    AlterTableExpression,
)

# View DDL
from .ddl_view import (
    ColumnAlias,
    ViewAlgorithm,
    ViewCheckOption,
    ViewOptions,
    CreateViewExpression,
    DropViewExpression,
    CreateMaterializedViewExpression,
    DropMaterializedViewExpression,
    RefreshMaterializedViewExpression,
)

# Truncate DDL
from .ddl_truncate import TruncateExpression

# Schema DDL
from .ddl_schema import CreateSchemaExpression, DropSchemaExpression

# Index DDL
from .ddl_index import (
    CreateIndexExpression,
    DropIndexExpression,
    CreateFulltextIndexExpression,
    DropFulltextIndexExpression,
)

# Sequence DDL
from .ddl_sequence import (
    CreateSequenceExpression,
    DropSequenceExpression,
    AlterSequenceExpression,
)

# Trigger DDL
from .ddl_trigger import (
    TriggerTiming,
    TriggerEvent,
    TriggerLevel,
    CreateTriggerExpression,
    DropTriggerExpression,
)

# Function DDL
from .ddl_function import CreateFunctionExpression, DropFunctionExpression

# Re-export shared type alias
from ._types import FromSourceType

__all__ = [
    # DQL
    "SelectModifier",
    "QueryExpression",
    # Re-export from query_parts for backward compatibility
    "WhereClause",
    "ForUpdateClause",
    # EXPLAIN
    "ExplainType",
    "ExplainFormat",
    "ExplainOptions",
    "ExplainExpression",
    # DML
    "MergeActionType",
    "MergeAction",
    "MergeExpression",
    "ReturningClause",
    "DeleteExpression",
    "UpdateExpression",
    "InsertDataSource",
    "ValuesSource",
    "SelectSource",
    "DefaultValuesSource",
    "OnConflictClause",
    "InsertExpression",
    # Table DDL
    "ColumnConstraintType",
    "ColumnConstraint",
    "GeneratedColumnType",
    "ColumnDefinition",
    "TableConstraintType",
    "ReferentialAction",
    "ConstraintValidation",
    "TableConstraint",
    "ForeignKeyConstraint",
    "IndexDefinition",
    "CreateTableExpression",
    "DropTableExpression",
    # ALTER TABLE DDL
    "AlterTableActionType",
    "AlterTableAction",
    "AddColumn",
    "DropColumn",
    "ColumnAlterOperation",
    "AlterColumn",
    "AddTableConstraint",
    "DropTableConstraint",
    "RenameColumn",
    "RenameTable",
    "AddConstraint",
    "DropConstraint",
    "RenameObject",
    "AddIndex",
    "DropIndex",
    "AlterTableExpression",
    # View DDL
    "ColumnAlias",
    "ViewAlgorithm",
    "ViewCheckOption",
    "ViewOptions",
    "CreateViewExpression",
    "DropViewExpression",
    "CreateMaterializedViewExpression",
    "DropMaterializedViewExpression",
    "RefreshMaterializedViewExpression",
    # Truncate DDL
    "TruncateExpression",
    # Schema DDL
    "CreateSchemaExpression",
    "DropSchemaExpression",
    # Index DDL
    "CreateIndexExpression",
    "DropIndexExpression",
    "CreateFulltextIndexExpression",
    "DropFulltextIndexExpression",
    # Sequence DDL
    "CreateSequenceExpression",
    "DropSequenceExpression",
    "AlterSequenceExpression",
    # Trigger DDL
    "TriggerTiming",
    "TriggerEvent",
    "TriggerLevel",
    "CreateTriggerExpression",
    "DropTriggerExpression",
    # Function DDL
    "CreateFunctionExpression",
    "DropFunctionExpression",
    # Type aliases
    "FromSourceType",
]
