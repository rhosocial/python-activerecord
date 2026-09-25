# src/rhosocial/activerecord/ddl/__init__.py
"""Generation-only DDL expression generation surface.

This package converts declarations supplied by the :class:`~rhosocial.activerecord.base.ddl.DDLSource`
protocol into expression objects bound to the dialect of a storage backend.  The
source may be an ``ActiveRecord`` model or any other structural implementation of
that protocol; the generation layer does not require either one.

The public classes are re-exported here as the supported entry points:

* :class:`~rhosocial.activerecord.ddl.active.ActiveDDL` and
  :class:`~rhosocial.activerecord.ddl.active.AsyncActiveDDL` provide the
  source-bound table, index, view, comment, alter, truncate, and partition
  lifecycle factories.
* :class:`~rhosocial.activerecord.ddl.deriver.TableDDLDeriver` and
  :class:`~rhosocial.activerecord.ddl.selector.DialectExpressionSelector`
  implement declaration collection and dialect selection.
* :class:`~rhosocial.activerecord.ddl.binder.DialectBinder` binds declaration
  nodes, while :mod:`~rhosocial.activerecord.ddl.types` resolves Python types
  to supported :class:`~rhosocial.activerecord.backend.expression.types.DataType`
  expressions.
* :mod:`~rhosocial.activerecord.ddl.partition` defines the source-bound
  partition lifecycle façade, typed requests, capability reporting, and the
  backend provider seam.
* The selector and exception classes expose the explicit selection and
  statement-construction rules used by the deriver.

Only expression construction and the capability decisions needed to construct
an expression belong here.  This package does not produce final SQL, execute
DDL, create execution plans, or implement backend compatibility fallbacks.  A
selector may call ``to_sql()`` transiently to test renderability, but discards
that result; final SQL formatting remains in backend expression formatters and
capability protocols.

Notes:
    ``AsyncActiveDDL`` has the same generation methods as ``ActiveDDL`` and
    returns ordinary expression objects; the ``Async`` prefix denotes API
    parity, not an asynchronous execution operation.
"""

from .active import ActiveDDL, AsyncActiveDDL
from .binder import DialectBinder
from .deriver import StatementContractError, StatementParamSchema, TableDDLDeriver
from .partition import (
    AddPartitionRequest,
    AttachPartitionRequest,
    CoalescePartitionsRequest,
    CreatePartitionRequest,
    DetachPartitionRequest,
    DropPartitionRequest,
    ExchangePartitionRequest,
    MaintenancePartitionRequest,
    MergePartitionsRequest,
    MovePartitionRequest,
    PartitionCapabilities,
    PartitionLifecycle,
    PartitionLifecycleDialect,
    PartitionLifecycleContractError,
    PartitionLifecycleProvider,
    PartitionOperation,
    PartitionOperationNotSupportedError,
    PartitionRequest,
    RemovePartitioningRequest,
    ReorganizePartitionRequest,
    SplitPartitionRequest,
    TruncatePartitionRequest,
)
from .selector import DeclarationSelectionError, DialectExpressionSelector, ExpressionOwnership
from .types import ColumnTypeResolutionError, ColumnTypeResolver, PythonTypeMapping

__all__ = [
    "ActiveDDL",
    "AsyncActiveDDL",
    "AddPartitionRequest",
    "AttachPartitionRequest",
    "CoalescePartitionsRequest",
    "CreatePartitionRequest",
    "DetachPartitionRequest",
    "DropPartitionRequest",
    "ExchangePartitionRequest",
    "MaintenancePartitionRequest",
    "MergePartitionsRequest",
    "MovePartitionRequest",
    "PartitionCapabilities",
    "PartitionLifecycle",
    "PartitionLifecycleDialect",
    "PartitionLifecycleContractError",
    "PartitionLifecycleProvider",
    "PartitionOperation",
    "PartitionOperationNotSupportedError",
    "PartitionRequest",
    "RemovePartitioningRequest",
    "ReorganizePartitionRequest",
    "SplitPartitionRequest",
    "TruncatePartitionRequest",
    "ColumnTypeResolutionError",
    "ColumnTypeResolver",
    "DeclarationSelectionError",
    "DialectBinder",
    "DialectExpressionSelector",
    "ExpressionOwnership",
    "PythonTypeMapping",
    "StatementContractError",
    "StatementParamSchema",
    "TableDDLDeriver",
]
