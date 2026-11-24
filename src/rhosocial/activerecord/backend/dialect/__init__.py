# src/rhosocial/activerecord/backend/dialect/__init__.py
"""
SQL dialect system for rhosocial-activerecord.

This package provides a protocol-based dialect system that enables fine-grained
feature detection and graceful handling of database-specific SQL features.

Architecture:
- Base classes define core SQL interfaces
- Protocols declare optional advanced features
- Concrete dialects are implemented in their respective backend packages
- Exceptions provide clear error messages when features aren't available

Usage:
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport

dialect = SQLiteDialect()

# Check protocol implementation
if isinstance(dialect, WindowFunctionSupport):
    if dialect.supports_window_functions():
        # Use window functions
        pass

# Or use helper methods
try:
    dialect.require_protocol(WindowFunctionSupport, "window functions", "MyQuery")
    dialect.check_feature_support("supports_rollup", "ROLLUP")
except ProtocolNotImplementedError as e:
    print(f"Protocol not implemented: {e}")
except UnsupportedFeatureError as e:
    print(f"Feature not supported: {e}")
"""

from .base import SQLDialectBase
from .exceptions import (
    UnsupportedFeatureError,
    UnsupportedDataTypeError,
    ProtocolNotImplementedError,
    DialectNotAdaptedException,
)
from .partition_capability import PartitionCapability
from .protocols import (
    # Named objects -- naming one, not creating or dropping it
    NamespaceSupport,
    TableObjectSupport,
    ViewObjectSupport,
    MaterializedViewObjectSupport,
    ForeignTableObjectSupport,
    IndexObjectSupport,
    SequenceObjectSupport,
    TriggerObjectSupport,
    RoutineObjectSupport,
    TypeObjectSupport,
    SynonymObjectSupport,
    # Query features
    WindowFunctionSupport,
    CTESupport,
    AdvancedGroupingSupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    ArraySupport,
    JSONSupport,
    UUIDSupport,
    ExplainSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    GraphTableSupport,
    WildcardSupport,
    JoinSupport,
    SetOperationSupport,
    ILIKESupport,
    SQLFunctionSupport,
    DataTypeSupport,
    CollationSupport,
    SQLXMLSupport,
    SQLXMLParsingSupport,
    SQLXMLSerializationSupport,
    SQLXMLConstructionSupport,
    SQLXMLAggregationSupport,
    SQLXMLQueryingSupport,
    # DDL statements
    CommentSupport,
    CreateDatabaseSupport,
    DropDatabaseSupport,
    AlterDatabaseSupport,
    PartitionSupport,
    ConstraintSupport,
    TruncateSupport,
    TransactionalDDLSupport,
    CreateSchemaSupport,
    DropSchemaSupport,
    GeneratedColumnSupport,
    AutoIncrementColumnSupport,
    IdentityColumnSupport,
    ColumnAttributeSupport,
    AlterTableModifierSupport,
    # Introspection and sessions
    IntrospectionSupport,
    TransactionControlSupport,
)
from .mixins import (
    WindowFunctionMixin,
    CTEMixin,
    UpsertMixin,
    LateralJoinMixin,
    ArrayMixin,
    TrimMixin,
    LpadMixin,
    RepeatMixin,
    RpadMixin,
    JSONMixin,
    UUIDMixin,
    ExplainMixin,
    MergeMixin,
    TemporalTableMixin,
    PivotMixin,
    GraphMixin,
    JoinMixin,
    SetOperationMixin,
    # DDL Mixins
    TableMixin,
    PartitionMixin,
    ConstraintMixin,
    CommentMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    ILIKEMixin,
    GeneratedColumnMixin,
    AutoIncrementColumnMixin,
    IdentityColumnMixin,
    DataTypeMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    RelationSourceMixin,
)

# Import Explain types from expression module to make them available in dialect module
from ..expression import ExplainType, ExplainFormat, ExplainOptions

__all__ = [
    # Base classes
    "SQLDialectBase",
    # Capability vocabulary
    "PartitionCapability",
    # Exceptions
    "UnsupportedFeatureError",
    "UnsupportedDataTypeError",
    "ProtocolNotImplementedError",
    "DialectNotAdaptedException",
    # Protocols
    "WindowFunctionSupport",
    "CTESupport",
    "AdvancedGroupingSupport",
    "ReturningSupport",
    "UpsertSupport",
    "LateralJoinSupport",
    "ArraySupport",
    "JSONSupport",
    "UUIDSupport",
    "ExplainSupport",
    "FilterClauseSupport",
    "OrderedSetAggregationSupport",
    "MergeSupport",
    "TemporalTableSupport",
    "QualifyClauseSupport",
    "LockingSupport",
    "GraphSupport",
    "WildcardSupport",
    "JoinSupport",
    "SetOperationSupport",
    # Named-object protocols
    "NamespaceSupport",
    "TableObjectSupport",
    "ViewObjectSupport",
    "MaterializedViewObjectSupport",
    "ForeignTableObjectSupport",
    "IndexObjectSupport",
    "SequenceObjectSupport",
    "TriggerObjectSupport",
    "RoutineObjectSupport",
    "TypeObjectSupport",
    "SynonymObjectSupport",
    # Query protocols
    "GraphTableSupport",
    "ILIKESupport",
    "SQLFunctionSupport",
    "CollationSupport",
    "DataTypeSupport",
    "SQLXMLSupport",
    "SQLXMLParsingSupport",
    "SQLXMLSerializationSupport",
    "SQLXMLConstructionSupport",
    "SQLXMLAggregationSupport",
    "SQLXMLQueryingSupport",
    # DDL protocols
    "PartitionSupport",
    "ConstraintSupport",
    "TruncateSupport",
    "TransactionalDDLSupport",
    "GeneratedColumnSupport",
    "AutoIncrementColumnSupport",
    "IdentityColumnSupport",
    "ColumnAttributeSupport",
    "AlterTableModifierSupport",
    "CommentSupport",
    "CreateDatabaseSupport",
    "DropDatabaseSupport",
    "AlterDatabaseSupport",
    "CreateSchemaSupport",
    "DropSchemaSupport",
    # Introspection and sessions
    "IntrospectionSupport",
    "TransactionControlSupport",
    # Mixins
    "WindowFunctionMixin",
    "CTEMixin",
    "UpsertMixin",
    "LateralJoinMixin",
    "ArrayMixin",
    "TrimMixin",
    "LpadMixin",
    "RepeatMixin",
    "RpadMixin",
    "JSONMixin",
    "UUIDMixin",
    "ExplainMixin",
    "MergeMixin",
    "TemporalTableMixin",
    "PivotMixin",
    "GraphMixin",
    "JoinMixin",
    "SetOperationMixin",
    # DDL Mixins
    "TableMixin",
    "PartitionMixin",
    "ConstraintMixin",
    "CommentMixin",
    "ViewMixin",
    "TruncateMixin",
    "SchemaMixin",
    "IndexMixin",
    "SequenceMixin",
    "TriggerMixin",
    "FunctionMixin",
    "ILIKEMixin",
    "GeneratedColumnMixin",
    "AutoIncrementColumnMixin",
    "IdentityColumnMixin",
    "DataTypeMixin",
    "UserDefinedTypeMixin",
    "DomainMixin",
    "RelationSourceMixin",
    # Re-exported types from expression module
    "ExplainType",
    "ExplainFormat",
    "ExplainOptions",
]
