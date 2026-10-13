from ._types import FromSourceType
from .fulltext_match import FulltextMatch
from .filter_clause import FilterClause
from .ddl_partition import (
    PartitionClause,
    PartitionDefinition,
    PartitionStrategy,
    SubpartitionDefinition,
)
from .ddl_function import CreateFunctionStatement, DropFunctionStatement
from .ddl_trigger import (
    TriggerTiming,
    TriggerEvent,
    TriggerLevel,
    CreateTriggerStatement,
    DropTriggerStatement,
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
from .ddl_type import (
    TypeDefinition,
    TypeAlterAction,
    CreateTypeStatement,
    AlterTypeStatement,
    DropTypeStatement,
)
from .ddl_sequence import (
    CreateSequenceStatement,
    DropSequenceStatement,
    AlterSequenceStatement,
)
from .ddl_index import (
    CreateIndexStatement,
    DropIndexStatement,
    CreateFulltextIndexStatement,
    DropFulltextIndexStatement,
)
from .ddl_schema import CreateSchemaStatement, DropSchemaStatement
from .ddl_truncate import TruncateStatement
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
from .ddl_comment import CommentObjectType, CommentOnStatement
from .ddl_table import (
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
    ColumnDefinition,
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
    ColumnConstraintBranch,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnCheckConstraint,
    ColumnDefaultConstraint,
    ColumnForeignKeyConstraint,
    ColumnGeneratedConstraint,
    TableConstraintBranch,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
    TableCheckConstraint,
    TableForeignKeyConstraint,
    TableExcludeConstraint,
)
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
from .explain import ExplainType, ExplainFormat, ExplainOptions, ExplainStatement
from ..query_parts import WhereClause, ForUpdateClause
from .dql import SelectModifier, QueryStatement
# src/rhosocial/activerecord/backend/expression/statements/__init__.py
"""
SQL DML (Data Manipulation Language), DQL (Data Query Language),
and DDL (Data Definition Language) statements.

These expression classes are responsible for collecting the parameters and structure
for a given SQL statement and delegating the actual SQL string generation
to a backend-specific dialect.
"""

# DQL

# Re-export WhereClause and ForUpdateClause from query_parts for backward compatibility

# EXPLAIN

# DML

# Table DDL

# COMMENT ON DDL

# ALTER TABLE DDL

# View DDL

# Truncate DDL

# Schema DDL

# Index DDL

# Sequence DDL



# Trigger DDL

# Function DDL

# Partition DDL

# Filter clause expression

# Fulltext match expression

# Re-export shared type alias

__all__ = [
    "SelectModifier",
    "QueryStatement",
    "WhereClause",
    "ForUpdateClause",
    "ExplainType",
    "ExplainFormat",
    "ExplainOptions",
    "ExplainStatement",
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
    "ForeignKeyMatchType",
    "ColumnConstraintBranch",
    "ColumnPrimaryKeyConstraint",
    "ColumnUniqueConstraint",
    "ColumnNotNullConstraint",
    "ColumnNullableConstraint",
    "ColumnCheckConstraint",
    "ColumnDefaultConstraint",
    "ColumnForeignKeyConstraint",
    "ColumnGeneratedConstraint",
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
    "ColumnDefinition",
    "ReferentialAction",
    "ConstraintValidation",
    "TableConstraintBranch",
    "TablePrimaryKeyConstraint",
    "TableUniqueConstraint",
    "TableCheckConstraint",
    "TableForeignKeyConstraint",
    "TableExcludeConstraint",
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
    "CommentObjectType",
    "CommentOnStatement",
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
    "ColumnAlias",
    "ViewAlgorithm",
    "ViewCheckOption",
    "ViewOptions",
    "CreateViewStatement",
    "DropViewStatement",
    "CreateMaterializedViewStatement",
    "DropMaterializedViewStatement",
    "RefreshMaterializedViewStatement",
    "TruncateStatement",
    "CreateSchemaStatement",
    "DropSchemaStatement",
    "CreateIndexStatement",
    "DropIndexStatement",
    "CreateFulltextIndexStatement",
    "DropFulltextIndexStatement",
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
    "TriggerTiming",
    "TriggerEvent",
    "TriggerLevel",
    "CreateTriggerStatement",
    "DropTriggerStatement",
    "CreateFunctionStatement",
    "DropFunctionStatement",
    "PartitionClause",
    "PartitionDefinition",
    "PartitionStrategy",
    "SubpartitionDefinition",
    "FilterClause",
    "FulltextMatch",
    "FromSourceType",
]
