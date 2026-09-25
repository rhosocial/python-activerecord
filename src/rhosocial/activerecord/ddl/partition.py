# src/rhosocial/activerecord/ddl/partition.py
"""Source-bound partition lifecycle expression factory.

``table_partition`` declarations describe how a table is created.  This module
handles the separate lifecycle of an already-existing partitioned table.  The
facade carries a DDL source and dialect, delegates operation construction to a
backend provider, and returns backend-owned expressions without executing them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    FrozenSet,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
    runtime_checkable,
    TYPE_CHECKING,
)

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
    PartitionClause,
    PartitionDefinition,
)
from rhosocial.activerecord.base.ddl import DDLSource

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class PartitionOperation(str, Enum):
    """Portable partition lifecycle operation names."""

    ADD = "add"
    CREATE = "create"
    DROP = "drop"
    TRUNCATE = "truncate"
    ATTACH = "attach"
    DETACH = "detach"
    REORGANIZE = "reorganize"
    EXCHANGE = "exchange"
    REMOVE_PARTITIONING = "remove_partitioning"
    COALESCE = "coalesce"
    SPLIT = "split"
    MERGE = "merge"
    MOVE = "move"
    ANALYZE = "analyze"
    CHECK = "check"
    OPTIMIZE = "optimize"
    REBUILD = "rebuild"
    REPAIR = "repair"


@dataclass(frozen=True)
class PartitionCapabilities:
    """Operations and strategies exposed by a backend provider."""

    operations: FrozenSet[PartitionOperation] = field(default_factory=frozenset)
    strategies: Tuple[str, ...] = ()

    def supports(self, operation: PartitionOperation) -> bool:
        """Return whether *operation* is exposed by the provider."""
        return operation in self.operations


@dataclass(frozen=True)
class PartitionRequest:
    """Base request passed to a backend partition provider."""

    operation: PartitionOperation
    table: TableExpression


@dataclass(frozen=True)
class AddPartitionRequest(PartitionRequest):
    """Request to add one backend-defined partition declaration."""

    definition: PartitionDefinition


@dataclass(frozen=True)
class CreatePartitionRequest(PartitionRequest):
    """Request to create a child partition with explicit bounds."""

    partition_name: str
    partition_type: str
    partition_values: Mapping[str, Any]
    if_not_exists: bool = False
    tablespace: Optional[str] = None
    partition_clause: Optional[PartitionClause] = None
    partition_schema: Optional[str] = None
    parent_schema: Optional[str] = None


@dataclass(frozen=True)
class DropPartitionRequest(PartitionRequest):
    """Request to drop one named partition."""

    partition_name: str
    partition_schema: Optional[str] = None


@dataclass(frozen=True)
class TruncatePartitionRequest(PartitionRequest):
    """Request to truncate one named partition."""

    partition_name: str
    partition_schema: Optional[str] = None


@dataclass(frozen=True)
class AttachPartitionRequest(PartitionRequest):
    """Request to attach an existing table as a partition."""

    partition_name: str
    partition_type: str
    partition_values: Mapping[str, Any]
    concurrently: bool = False
    partition_schema: Optional[str] = None
    parent_schema: Optional[str] = None


@dataclass(frozen=True)
class DetachPartitionRequest(PartitionRequest):
    """Request to detach a partition without dropping its data."""

    partition_name: str
    concurrently: bool = False
    finalize: bool = False
    partition_schema: Optional[str] = None
    parent_schema: Optional[str] = None


@dataclass(frozen=True)
class ReorganizePartitionRequest(PartitionRequest):
    """Request to replace one partition with new definitions."""

    partition_name: str
    definitions: Tuple[PartitionDefinition, ...]


@dataclass(frozen=True)
class ExchangePartitionRequest(PartitionRequest):
    """Request to exchange a partition with another table."""

    partition_name: str
    exchange_table: TableExpression
    with_validation: bool = True


@dataclass(frozen=True)
class RemovePartitioningRequest(PartitionRequest):
    """Request to remove partitioning from a table."""


@dataclass(frozen=True)
class CoalescePartitionsRequest(PartitionRequest):
    """Request to coalesce a number of adjacent partitions."""

    count: int


@dataclass(frozen=True)
class SplitPartitionRequest(PartitionRequest):
    """Request to split one partition into two definitions."""

    partition_name: str
    at_values: Tuple[Any, ...]
    new_partitions: Tuple[PartitionDefinition, ...]


@dataclass(frozen=True)
class MergePartitionsRequest(PartitionRequest):
    """Request to merge two partitions into one definition."""

    partition_names: Tuple[str, ...]
    into_partition: PartitionDefinition


@dataclass(frozen=True)
class MovePartitionRequest(PartitionRequest):
    """Request to move a partition, optionally to a tablespace."""

    partition_name: str
    tablespace_name: Optional[str] = None


@dataclass(frozen=True)
class MaintenancePartitionRequest(PartitionRequest):
    """Request for a backend partition maintenance operation."""

    partition_name: str


class PartitionOperationNotSupportedError(UnsupportedFeatureError):
    """Raised when a dialect has no lifecycle provider for an operation."""

    def __init__(self, dialect_name: str, operation: PartitionOperation):
        super().__init__(
            dialect_name,
            f"partition lifecycle operation {operation.value}",
            "Expose a backend PartitionLifecycleProvider for this operation.",
        )


class PartitionLifecycleContractError(TypeError):
    """Raised when a provider returns an invalid lifecycle expression."""


@runtime_checkable
class PartitionLifecycleProvider(Protocol):
    """Backend extension point for constructing partition expressions."""

    def capabilities(self) -> PartitionCapabilities:
        """Return the provider's current operation and strategy surface."""
        ...

    def supports(self, operation: PartitionOperation) -> bool:
        """Return whether one operation can be constructed."""
        ...

    def build(self, request: PartitionRequest) -> BaseExpression:
        """Construct a backend-owned expression for *request*."""
        ...


@runtime_checkable
class PartitionLifecycleDialect(Protocol):
    """Optional dialect hook for exposing a partition provider."""

    def get_partition_lifecycle_provider(self) -> Optional[PartitionLifecycleProvider]:
        """Return the provider owned by this dialect, if one exists."""
        ...


class PartitionLifecycle:
    """Build backend-bound expressions for an existing partitioned table.

    The facade is intentionally stateless with respect to SQL execution.  It
    owns only the source-bound table reference and delegates operation-specific
    construction to the provider exposed by the active dialect.
    """

    def __init__(self, source: DDLSource, dialect: "SQLDialectBase"):
        """Bind a lifecycle facade to one source and dialect.

        Args:
            source: DDL declaration source supplying the target table.
            dialect: Active backend dialect used to obtain its provider.
        """
        self.source = source
        self.dialect = dialect
        self.table = TableExpression(
            dialect,
            source.table_name(),
            schema_name=source.schema_name(),
        )
        if isinstance(dialect, PartitionLifecycleDialect):
            self._provider = dialect.get_partition_lifecycle_provider()
        else:
            self._provider = None
        if self._provider is not None and not isinstance(
            self._provider, PartitionLifecycleProvider
        ):
            raise PartitionLifecycleContractError(
                f"{dialect.name} returned an invalid partition lifecycle provider: "
                f"{type(self._provider).__name__}"
            )

    @property
    def provider(self) -> Optional[PartitionLifecycleProvider]:
        """Return the backend provider, if one is registered."""
        return self._provider

    def capabilities(self) -> PartitionCapabilities:
        """Return the active provider capabilities or an empty surface."""
        if self._provider is None:
            return PartitionCapabilities()
        return self._provider.capabilities()

    def supports(self, operation: PartitionOperation) -> bool:
        """Return whether the active provider supports *operation*."""
        return self._provider is not None and self._provider.supports(operation)

    def build(self, request: PartitionRequest) -> BaseExpression:
        """Build one expression through the active provider.

        Raises:
            TypeError: If *request* is not a partition request.
            PartitionOperationNotSupportedError: If no provider supports it.
            PartitionLifecycleContractError: If the provider returns a
                non-expression value.
        """
        if not isinstance(request, PartitionRequest):
            raise TypeError("request must be a PartitionRequest")
        if self._provider is None or not self._provider.supports(request.operation):
            raise PartitionOperationNotSupportedError(self.dialect.name, request.operation)
        expression = self._provider.build(request)
        if not isinstance(expression, BaseExpression):
            raise PartitionLifecycleContractError(
                f"partition provider returned {type(expression).__name__}; "
                "expected a BaseExpression"
            )
        return expression

    def add_partition(self, definition: PartitionDefinition) -> BaseExpression:
        """Build an add-partition expression for one definition."""
        return self.build(
            AddPartitionRequest(
                operation=PartitionOperation.ADD,
                table=self.table,
                definition=definition,
            )
        )

    def create_partition(
        self,
        partition_name: str,
        partition_type: str,
        partition_values: Mapping[str, Any],
        *,
        if_not_exists: bool = False,
        tablespace: Optional[str] = None,
        partition_clause: Optional[PartitionClause] = None,
        partition_schema: Optional[str] = None,
        parent_schema: Optional[str] = None,
    ) -> BaseExpression:
        """Build a child-partition expression with explicit bounds."""
        return self.build(
            CreatePartitionRequest(
                operation=PartitionOperation.CREATE,
                table=self.table,
                partition_name=partition_name,
                partition_type=partition_type,
                partition_values=dict(partition_values),
                if_not_exists=if_not_exists,
                tablespace=tablespace,
                partition_clause=partition_clause,
                partition_schema=partition_schema,
                parent_schema=parent_schema,
            )
        )

    def drop_partition(
        self,
        partition_name: str,
        *,
        partition_schema: Optional[str] = None,
    ) -> BaseExpression:
        """Build a drop-partition expression."""
        return self.build(
            DropPartitionRequest(
                operation=PartitionOperation.DROP,
                table=self.table,
                partition_name=partition_name,
                partition_schema=partition_schema,
            )
        )

    def truncate_partition(
        self,
        partition_name: str,
        *,
        partition_schema: Optional[str] = None,
    ) -> BaseExpression:
        """Build a truncate-partition expression."""
        return self.build(
            TruncatePartitionRequest(
                operation=PartitionOperation.TRUNCATE,
                table=self.table,
                partition_name=partition_name,
                partition_schema=partition_schema,
            )
        )

    def attach_partition(
        self,
        partition_name: str,
        partition_type: str,
        partition_values: Mapping[str, Any],
        *,
        concurrently: bool = False,
        partition_schema: Optional[str] = None,
        parent_schema: Optional[str] = None,
    ) -> BaseExpression:
        """Build an attach-partition expression."""
        return self.build(
            AttachPartitionRequest(
                operation=PartitionOperation.ATTACH,
                table=self.table,
                partition_name=partition_name,
                partition_type=partition_type,
                partition_values=dict(partition_values),
                concurrently=concurrently,
                partition_schema=partition_schema,
                parent_schema=parent_schema,
            )
        )

    def detach_partition(
        self,
        partition_name: str,
        *,
        concurrently: bool = False,
        finalize: bool = False,
        partition_schema: Optional[str] = None,
        parent_schema: Optional[str] = None,
    ) -> BaseExpression:
        """Build a detach-partition expression."""
        return self.build(
            DetachPartitionRequest(
                operation=PartitionOperation.DETACH,
                table=self.table,
                partition_name=partition_name,
                concurrently=concurrently,
                finalize=finalize,
                partition_schema=partition_schema,
                parent_schema=parent_schema,
            )
        )

    def reorganize_partition(
        self,
        partition_name: str,
        definitions: Sequence[PartitionDefinition],
    ) -> BaseExpression:
        """Build a reorganize-partition expression."""
        return self.build(
            ReorganizePartitionRequest(
                operation=PartitionOperation.REORGANIZE,
                table=self.table,
                partition_name=partition_name,
                definitions=tuple(definitions),
            )
        )

    def exchange_partition(
        self,
        partition_name: str,
        exchange_table: Union[str, TableExpression],
        *,
        with_validation: bool = True,
    ) -> BaseExpression:
        """Build an exchange-partition expression."""
        if isinstance(exchange_table, str):
            target = TableExpression(self.dialect, exchange_table)
        elif isinstance(exchange_table, TableExpression):
            target = exchange_table
        else:
            raise TypeError(
                "exchange_table must be a string or TableExpression, "
                f"got {type(exchange_table).__name__}"
            )
        return self.build(
            ExchangePartitionRequest(
                operation=PartitionOperation.EXCHANGE,
                table=self.table,
                partition_name=partition_name,
                exchange_table=target,
                with_validation=with_validation,
            )
        )

    def remove_partitioning(self) -> BaseExpression:
        """Build a remove-partitioning expression."""
        return self.build(
            RemovePartitioningRequest(
                operation=PartitionOperation.REMOVE_PARTITIONING,
                table=self.table,
            )
        )

    def coalesce_partitions(self, count: int) -> BaseExpression:
        """Build a coalesce-partitions expression."""
        return self.build(
            CoalescePartitionsRequest(
                operation=PartitionOperation.COALESCE,
                table=self.table,
                count=count,
            )
        )

    def split_partition(
        self,
        partition_name: str,
        at_values: Sequence[Any],
        new_partitions: Sequence[PartitionDefinition],
    ) -> BaseExpression:
        """Build a split-partition expression."""
        return self.build(
            SplitPartitionRequest(
                operation=PartitionOperation.SPLIT,
                table=self.table,
                partition_name=partition_name,
                at_values=tuple(at_values),
                new_partitions=tuple(new_partitions),
            )
        )

    def merge_partitions(
        self,
        partition_names: Sequence[str],
        into_partition: PartitionDefinition,
    ) -> BaseExpression:
        """Build a merge-partitions expression."""
        return self.build(
            MergePartitionsRequest(
                operation=PartitionOperation.MERGE,
                table=self.table,
                partition_names=tuple(partition_names),
                into_partition=into_partition,
            )
        )

    def move_partition(
        self,
        partition_name: str,
        tablespace_name: Optional[str] = None,
    ) -> BaseExpression:
        """Build a move-partition expression."""
        return self.build(
            MovePartitionRequest(
                operation=PartitionOperation.MOVE,
                table=self.table,
                partition_name=partition_name,
                tablespace_name=tablespace_name,
            )
        )

    def _maintenance(self, operation: PartitionOperation, partition_name: str) -> BaseExpression:
        return self.build(
            MaintenancePartitionRequest(
                operation=operation,
                table=self.table,
                partition_name=partition_name,
            )
        )

    def analyze_partition(self, partition_name: str) -> BaseExpression:
        """Build an analyze-partition expression."""
        return self._maintenance(PartitionOperation.ANALYZE, partition_name)

    def check_partition(self, partition_name: str) -> BaseExpression:
        """Build a check-partition expression."""
        return self._maintenance(PartitionOperation.CHECK, partition_name)

    def optimize_partition(self, partition_name: str) -> BaseExpression:
        """Build an optimize-partition expression."""
        return self._maintenance(PartitionOperation.OPTIMIZE, partition_name)

    def rebuild_partition(self, partition_name: str) -> BaseExpression:
        """Build a rebuild-partition expression."""
        return self._maintenance(PartitionOperation.REBUILD, partition_name)

    def repair_partition(self, partition_name: str) -> BaseExpression:
        """Build a repair-partition expression."""
        return self._maintenance(PartitionOperation.REPAIR, partition_name)


__all__ = [
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
]
