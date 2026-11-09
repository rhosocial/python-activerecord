# src/rhosocial/activerecord/backend/partition/__init__.py
"""Engine-neutral partition maintenance.

The backend owns the plan grammar, the catalogue query and the DDL. This package
owns what every backend returns and the verbs a caller may feature-detect, so a
caller can read a report without knowing which engine produced it.

The contract is deliberately narrow. There is no unified plan or policy class:
PostgreSQL's heterogeneous child branches, Oracle's table-level subpartition
strategy, SQL Server's function/scheme pair, MySQL's flat caller-owned
definitions and ClickHouse's server-assigned partition id are different models,
and flattening them would lose the distinction each engine's maintenance code
needs. Only the answer shape and the optional verbs are shared.
"""

from .protocols import (
    AsyncPartitionEnsurer,
    AsyncPartitionInventory,
    AsyncPartitionRetention,
    AsyncPartitionValidator,
    PartitionEnsurer,
    PartitionInventory,
    PartitionRetention,
    PartitionValidator,
)
from .types import (
    PairedDifference,
    PartitionBatchReport,
    PartitionInfo,
    PartitionOperation,
    PartitionReport,
)

__all__ = [
    "AsyncPartitionEnsurer",
    "AsyncPartitionInventory",
    "AsyncPartitionRetention",
    "AsyncPartitionValidator",
    "PairedDifference",
    "PartitionBatchReport",
    "PartitionEnsurer",
    "PartitionInfo",
    "PartitionInventory",
    "PartitionOperation",
    "PartitionReport",
    "PartitionRetention",
    "PartitionValidator",
]
