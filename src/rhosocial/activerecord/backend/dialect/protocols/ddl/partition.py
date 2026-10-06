# src/rhosocial/activerecord/backend/dialect/protocols/partitionsupport.py
"""PartitionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import (
        PartitionClause,
        PartitionDefinition,
    )


@runtime_checkable
class PartitionSupport(Protocol):
    """Protocol for generic table partitioning expression support.

    The protocol covers capability detection, ``PARTITION BY`` clause
    formatting, and backend-owned partition definition formatting. Partition
    lifecycle orchestration is intentionally outside this protocol.
    """

    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported at the database level."""
        ...  # pragma: no cover

    def supports_partitioned_table_creation(self) -> bool:
        """Whether CREATE TABLE can create partitioned tables through this dialect."""
        ...  # pragma: no cover

    def supports_partition_metadata_introspection(self) -> bool:
        """Whether partition metadata introspection is supported."""
        ...  # pragma: no cover

    def supports_range_table_partitioning(self) -> bool:
        """Whether RANGE table partitioning is supported."""
        ...  # pragma: no cover

    def supports_list_table_partitioning(self) -> bool:
        """Whether LIST table partitioning is supported."""
        ...  # pragma: no cover

    def supports_hash_table_partitioning(self) -> bool:
        """Whether HASH table partitioning is supported."""
        ...  # pragma: no cover

    def supports_subpartitioning(self) -> bool:
        """Whether table subpartitioning is supported."""
        ...  # pragma: no cover

    def format_partition_clause(self, expr: "PartitionClause") -> Tuple[str, tuple]:
        """Format PARTITION BY clause from expression.

        Args:
            expr: PartitionClause with partition method and key expressions.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_partition_definition(self, definition: "PartitionDefinition") -> Tuple[str, tuple]:
        """Format an inline partition definition from a structural declaration.

        Backends that declare partitions inline in CREATE TABLE override this;
        the generic implementation raises ``UnsupportedFeatureError`` because
        partition boundary syntax is backend-specific.

        Args:
            definition: PartitionDefinition (or backend subclass) to render.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover
