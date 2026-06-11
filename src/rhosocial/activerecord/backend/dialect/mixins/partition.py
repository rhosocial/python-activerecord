# src/rhosocial/activerecord/backend/dialect/mixins/partition.py
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import PartitionClause


class PartitionMixin:
    """Mixin for table partitioning support.

    Implements the PartitionSupport protocol with default behavior:
    - All supports_*() methods return False by default
    - format_partition_clause() raises UnsupportedFeatureError by default
    """

    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported at the database level."""
        return False

    def supports_partitioned_table_creation(self) -> bool:
        """Whether CREATE TABLE can create partitioned tables through this dialect."""
        return False

    def supports_partition_metadata_introspection(self) -> bool:
        """Whether partition metadata introspection is supported."""
        return False

    def supports_range_table_partitioning(self) -> bool:
        """Whether RANGE table partitioning is supported."""
        return False

    def supports_list_table_partitioning(self) -> bool:
        """Whether LIST table partitioning is supported."""
        return False

    def supports_hash_table_partitioning(self) -> bool:
        """Whether HASH table partitioning is supported."""
        return False

    def supports_subpartitioning(self) -> bool:
        """Whether table subpartitioning is supported."""
        return False

    def supports_add_partition(self) -> bool:
        """Whether adding partitions through the public API is supported."""
        return False

    def supports_drop_partition(self) -> bool:
        """Whether dropping partitions through the public API is supported."""
        return False

    def supports_truncate_partition(self) -> bool:
        """Whether truncating partitions through the public API is supported."""
        return False

    def supports_reorganize_partition(self) -> bool:
        """Whether reorganizing partitions through the public API is supported."""
        return False

    def supports_attach_partition(self) -> bool:
        """Whether attaching partitions through the public API is supported."""
        return False

    def supports_detach_partition(self) -> bool:
        """Whether detaching partitions through the public API is supported."""
        return False

    def format_partition_clause(self, expr: "PartitionClause") -> Tuple[str, tuple]:
        """Format PARTITION BY clause from expression.

        The generic mixin does not generate backend-specific PARTITION BY
        syntax. Dialects that support partitioning must override this method.

        Args:
            expr: PartitionClause with partition method and key expressions.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        raise UnsupportedFeatureError(
            self.name,
            "PARTITION BY clause",
            "PartitionClause requires a dialect implementing PartitionSupport. "
            "Use a concrete backend partition protocol such as MySQL or PostgreSQL "
            "when table partitioning is available.",
        )
