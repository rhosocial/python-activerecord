# src/rhosocial/activerecord/backend/dialect/mixins/partition.py
"""Dialect mixin for generic table partitioning expressions.

Declares partitioning capabilities and formats the generic ``PARTITION BY``
clause. Lifecycle orchestration is not part of this mixin. All ``supports_*``
capability flags default to False; inline partition definitions have no
portable generic syntax, so ``format_partition_definition`` always raises
unless a backend overrides it.
"""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import PartitionClause, PartitionDefinition


class PartitionMixin:
    """Mixin for table partitioning support.

    Implements the PartitionSupport protocol with default behavior:
    - All supports_*() methods return False by default
    - format_partition_clause() raises UnsupportedFeatureError by default
    """

    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported at the database level.

        Defaults to False.
        """
        return False

    def supports_partitioned_table_creation(self) -> bool:
        """Whether CREATE TABLE can create partitioned tables through this dialect.

        Defaults to False.
        """
        return False

    def supports_partition_metadata_introspection(self) -> bool:
        """Whether partition metadata introspection is supported.

        Defaults to False.
        """
        return False

    def supports_range_table_partitioning(self) -> bool:
        """Whether RANGE table partitioning is supported. Defaults to False."""
        return False

    def supports_list_table_partitioning(self) -> bool:
        """Whether LIST table partitioning is supported. Defaults to False."""
        return False

    def supports_hash_table_partitioning(self) -> bool:
        """Whether HASH table partitioning is supported. Defaults to False."""
        return False

    def supports_subpartitioning(self) -> bool:
        """Whether table subpartitioning is supported. Defaults to False."""
        return False

    def format_partition_clause(self, expr: "PartitionClause") -> Tuple[str, tuple]:
        """Format the generic ``PARTITION BY <method> (<keys>)`` clause.

        This default renders only the clause shape shared by RANGE/LIST/HASH
        partitioning; concrete partition definitions are backend-specific and
        are never produced here. Dialects without declarative partitioning
        (``supports_partitioned_table_creation()`` returning False) raise
        ``UnsupportedFeatureError``.

        Args:
            expr: PartitionClause with partition method and key expressions.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If the dialect does not support creating
                partitioned tables, or the requested method is not supported.
        """
        if not self.supports_partitioned_table_creation():
            raise UnsupportedFeatureError(
                self.name,
                "PARTITION BY clause",
                "PartitionClause requires a dialect implementing PartitionSupport. "
                "Use a concrete backend partition protocol such as MySQL or PostgreSQL "
                "when table partitioning is available.",
            )

        method = expr.method.upper()
        method_gates = {
            "RANGE": self.supports_range_table_partitioning,
            "LIST": self.supports_list_table_partitioning,
            "HASH": self.supports_hash_table_partitioning,
        }
        gate = method_gates.get(method)
        if gate is None:
            raise UnsupportedFeatureError(
                self.name,
                f"{method} partitioning",
                f"{method} is not a generic partitioning method.",
            )
        if not gate():
            raise UnsupportedFeatureError(
                self.name,
                f"{method} partitioning",
                f"{self.name} does not support {method} table partitioning.",
            )

        key_parts = []
        params = []
        for key in expr.keys:
            key_sql, key_params = key.to_sql()
            key_parts.append(key_sql)
            params.extend(key_params)
        return f" PARTITION BY {method} ({', '.join(key_parts)})", tuple(params)

    def format_partition_definition(self, definition: "PartitionDefinition") -> Tuple[str, tuple]:
        """Format an inline partition definition.

        There is no portable generic syntax for a partition boundary
        (``VALUES LESS THAN`` / ``VALUES IN`` / ``FOR VALUES`` all differ),
        so the generic mixin does not render definitions. Backends that declare
        partitions inline must override this method.

        Args:
            definition: PartitionDefinition (or backend subclass) to render.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: Always, unless a concrete backend
                overrides this method.
        """
        raise UnsupportedFeatureError(
            self.name,
            "partition definition",
            "partition definitions require a dialect implementing inline "
            "partition rendering; use a concrete backend such as MySQL or Oracle.",
        )
