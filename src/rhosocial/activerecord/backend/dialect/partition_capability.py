# src/rhosocial/activerecord/backend/dialect/partition_capability.py
"""Dialect vocabulary for how a backend relates to table partitioning.

The historical single boolean -- ``supports_table_partitioning()`` -- can only
answer "yes" or "no", but there are three distinct situations: a backend with
native partition DDL the caller addresses by name, a backend whose engine
partitions and manages storage on its own with no DDL to target, and a backend
with no partitioning at all. This vocabulary names all three so the automatic
case no longer has to be reported as either of the other two.
"""
from enum import Enum


class PartitionCapability(str, Enum):
    """How a dialect relates to table partitioning."""

    #: A member *is* the word it carries; ``Enum.__str__`` would say
    #: ``PartitionCapability.NATIVE`` instead. Stated once here.
    __str__ = str.__str__

    #: The dialect renders partition DDL that the caller can address by name or
    #: id: the caller chooses the strategy and the boundaries, and can name or
    #: target the resulting partitions afterwards.
    NATIVE = "native"

    #: The engine partitions and manages storage itself (for example
    #: micro-partitions and clustering). No partition DDL exists, so there is
    #: nothing for the caller to name, create, or target.
    AUTOMATIC = "automatic"

    #: No partitioning at all: the backend stores every table as a single
    #: unpartitioned unit.
    UNSUPPORTED = "unsupported"
