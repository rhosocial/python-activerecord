# src/rhosocial/activerecord/backend/expression/statements/__init__.py
"""
SQL DML (Data Manipulation Language), DQL (Data Query Language),
and DDL (Data Definition Language) statements.

These expression classes are responsible for collecting the parameters and structure
for a given SQL statement and delegating the actual SQL string generation
to a backend-specific dialect.
"""

# DQL
from .dql import SelectModifier, QueryStatement

# Re-export WhereClause and ForUpdateClause from query_parts for backward compatibility
from ..query_parts import WhereClause, ForUpdateClause

# EXPLAIN
from .explain import ExplainType, ExplainFormat, ExplainOptions, ExplainStatement

# DML
from .dml import (
    MergeActionType,
    MergeAction,
    MergeStatement,
    ReturningClause,
    DeleteStatement,
    UpdateStatement,
    InsertDataSource,
    ValuesSource,
    SelectSource,
    DefaultValuesSource,
    OnConflictClause,
    InsertStatement,
)

# Table DDL
from .ddl_table import (
    ColumnConstraintType,
    ForeignKeyMatchType,
    ColumnConstraint,
    DefaultValueClause,
    ColumnClause,
    CollationClause,
    CharacterSetClause,
    IdentityClause,
    AutoIncrementClause,
    ReferencesClause,
    ColumnCommentClause,
    TableCommentClause,
    GeneratedColumnType,
    GeneratedColumnExpression,
    ColumnDefinition,
    TableConstraintType,
    ReferentialAction,
    ConstraintValidation,
    TableConstraint,
    ForeignKeyConstraint,
    IndexDefinition,
    CreateTableStatement,
    CreateTableAsStatement,
    CreateTableLikeStatement,
    CreateTableCloneStatement,
    CreateTableFromTemplateStatement,
    CreateTableOptions,
    CreateTableCloneMode,
    DropTableStatement,
    StorageOptionsExpression,
)

# COMMENT ON DDL
from .ddl_comment import CommentObjectType, CommentOnStatement

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
    AlterConstraint,
    ValidateConstraint,
    AlterConstraintAction,
    ValidateConstraintAction,
    AlterTableConstraint,
    ValidateTableConstraint,
    RenameTable,
    RenameObject,
    AddIndex,
    DropIndex,
    AlterTableStatement,
)

# View DDL
from .ddl_view import (
    ColumnAlias,
    ViewAlgorithm,
    ViewCheckOption,
    ViewOptions,
    CreateViewStatement,
    DropViewStatement,
    CreateMaterializedViewStatement,
    DropMaterializedViewStatement,
    RefreshMaterializedViewStatement,
)

# Truncate DDL
from .ddl_truncate import TruncateStatement

# Schema DDL
from .ddl_schema import CreateSchemaStatement, DropSchemaStatement

# Index DDL
from .ddl_index import (
    CreateIndexStatement,
    DropIndexStatement,
    CreateFulltextIndexStatement,
    DropFulltextIndexStatement,
)

# Sequence DDL
from .ddl_sequence import (
    CreateSequenceStatement,
    DropSequenceStatement,
    AlterSequenceStatement,
)

from .ddl_type import (
    TypeDefinition,
    TypeAlterAction,
    CreateTypeStatement,
    AlterTypeStatement,
    DropTypeStatement,
)

from .ddl_domain import (
    DomainNullability,
    DomainValueExpression,
    DomainCheckConstraint,
    DomainAlterAction,
    SetDomainDefaultAction,
    DropDomainDefaultAction,
    SetDomainNotNullAction,
    DropDomainNotNullAction,
    AddDomainCheckAction,
    DropDomainCheckAction,
    RenameDomainAction,
    CreateDomainStatement,
    AlterDomainStatement,
    DropDomainStatement,
)

# Trigger DDL
from .ddl_trigger import (
    TriggerTiming,
    TriggerEvent,
    TriggerLevel,
    CreateTriggerStatement,
    DropTriggerStatement,
)

# Function DDL
from .ddl_function import CreateFunctionStatement, DropFunctionStatement

# Partition DDL
from .ddl_partition import (
    PartitionClause,
    PartitionDefinition,
    PartitionStrategy,
    SubpartitionDefinition,
)

# Filter clause expression
from .filter_clause import FilterClauseExpression

# Fulltext match expression
from .fulltext_match import FulltextMatchExpression

# Re-export shared type alias
from ._types import FromSourceType
from ..objects import Table

__all__ = [
    # DQL
    "SelectModifier",
    "QueryStatement",
    # Re-export from query_parts for backward compatibility
    "WhereClause",
    "ForUpdateClause",
    # EXPLAIN
    "ExplainType",
    "ExplainFormat",
    "ExplainOptions",
    "ExplainStatement",
    # DML
    "MergeActionType",
    "MergeAction",
    "MergeStatement",
    "ReturningClause",
    "DeleteStatement",
    "UpdateStatement",
    "InsertDataSource",
    "ValuesSource",
    "SelectSource",
    "DefaultValuesSource",
    "OnConflictClause",
    "InsertStatement",
    # Table DDL
    "ColumnConstraintType",
    "ForeignKeyMatchType",
    "ColumnConstraint",
    "DefaultValueClause",
    "ColumnClause",
    "CollationClause",
    "CharacterSetClause",
    "IdentityClause",
    "AutoIncrementClause",
    "ReferencesClause",
    "ColumnCommentClause",
    "TableCommentClause",
    "GeneratedColumnType",
    "GeneratedColumnExpression",
    "ColumnDefinition",
    "TableConstraintType",
    "ReferentialAction",
    "ConstraintValidation",
    "TableConstraint",
    "ForeignKeyConstraint",
    "IndexDefinition",
    "CreateTableStatement",
    "CreateTableAsStatement",
    "CreateTableLikeStatement",
    "CreateTableCloneStatement",
    "CreateTableFromTemplateStatement",
    "CreateTableOptions",
    "CreateTableCloneMode",
    "DropTableStatement",
    "StorageOptionsExpression",
    # COMMENT ON DDL
    "CommentObjectType",
    "CommentOnStatement",
    # ALTER TABLE DDL
    "AlterTableActionType",
    "AlterTableAction",
    "AddColumn",
    "DropColumn",
    "ColumnAlterOperation",
    "AlterColumn",
    "AddTableConstraint",
    "DropTableConstraint",
    "AlterConstraint",
    "ValidateConstraint",
    "AlterConstraintAction",
    "ValidateConstraintAction",
    "AlterTableConstraint",
    "ValidateTableConstraint",
    "RenameTable",
    "RenameObject",
    "AddIndex",
    "DropIndex",
    "AlterTableStatement",
    # View DDL
    "ColumnAlias",
    "ViewAlgorithm",
    "ViewCheckOption",
    "ViewOptions",
    "CreateViewStatement",
    "DropViewStatement",
    "CreateMaterializedViewStatement",
    "DropMaterializedViewStatement",
    "RefreshMaterializedViewStatement",
    # Truncate DDL
    "TruncateStatement",
    # Schema DDL
    "CreateSchemaStatement",
    "DropSchemaStatement",
    # Index DDL
    "CreateIndexStatement",
    "DropIndexStatement",
    "CreateFulltextIndexStatement",
    "DropFulltextIndexStatement",
    # Sequence DDL
    "CreateSequenceStatement",
    "DropSequenceStatement",
    "AlterSequenceStatement",
    "TypeDefinition",
    "TypeAlterAction",
    "CreateTypeStatement",
    "AlterTypeStatement",
    "DropTypeStatement",
    "DomainNullability",
    "DomainValueExpression",
    "DomainCheckConstraint",
    "DomainAlterAction",
    "SetDomainDefaultAction",
    "DropDomainDefaultAction",
    "SetDomainNotNullAction",
    "DropDomainNotNullAction",
    "AddDomainCheckAction",
    "DropDomainCheckAction",
    "RenameDomainAction",
    "CreateDomainStatement",
    "AlterDomainStatement",
    "DropDomainStatement",
    # Trigger DDL
    "TriggerTiming",
    "TriggerEvent",
    "TriggerLevel",
    "CreateTriggerStatement",
    "DropTriggerStatement",
    # Function DDL
    "CreateFunctionStatement",
    "DropFunctionStatement",
    # Partition DDL
    "PartitionClause",
    "PartitionDefinition",
    "PartitionStrategy",
    "SubpartitionDefinition",
    # Filter clause expression
    "FilterClauseExpression",
    # Fulltext match expression
    "FulltextMatchExpression",
    # Type aliases
    "FromSourceType",
]
