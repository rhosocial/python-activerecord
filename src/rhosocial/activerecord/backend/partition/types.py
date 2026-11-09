# src/rhosocial/activerecord/backend/partition/types.py
"""Engine-neutral value objects for partition maintenance.

A backend owns the plan, the catalogue query and the DDL: PostgreSQL describes a
recursive tree, SQL Server a function and a scheme, MySQL a flat list of
caller-owned definitions, ClickHouse a server-assigned partition id. The plan
grammar and the destructive verb therefore stay engine-specific.

What a caller needs in order to branch on the answer rather than on the engine is
the shape of the result: one row per partition, one record per statement, and one
report envelope that says what the catalogue held and what the operation did.
Those three objects live here.

Fields that only one engine can fill go into :attr:`PartitionInfo.extras`; a
backend with nothing to put there leaves the mapping empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class PartitionInfo:
    """One partition row as a backend's catalogue reports it.

    Attributes:
        name: Partition or subpartition name as the server spells it.
        parent: Name of the containing partitioned object, or ``None`` for a
            row that the catalogue reports at the top of the target.
        level: Nesting depth: ``0`` for a root/scope row, ``1`` for a
            first-level partition, ``2`` for a subpartition.
        method: Strategy word the server reports (``RANGE``, ``LIST``,
            ``HASH``, ``KEY``), when the catalogue names one.
        bound: Boundary text exactly as the server reports it. It is
            deliberately not parsed: every engine spells bounds differently.
        schema: Schema the partition lives in, when the engine has schemas.
        row_count: Estimated or exact row count, when the catalogue exposes it.
        size_bytes: On-disk size in bytes, when the catalogue exposes it.
        is_partitioned: Whether this row itself has children.
        extras: Engine-specific facts. SQL Server's partition number, Oracle's
            subpartition count, ClickHouse's partition id, MySQL's child names
            and anything else no second engine shares belong here.
    """

    name: str
    parent: Optional[str] = None
    level: int = 0
    method: Optional[str] = None
    bound: Optional[str] = None
    schema: Optional[str] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    is_partitioned: bool = False
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PartitionOperation:
    """A statement the executor ran, or would run under a dry run.

    The action word stays free-form on purpose. ``create`` and ``drop`` are the
    common verbs, but SQL Server splits and merges a boundary, Oracle drops a
    partition by name, and ClickHouse detaches and attaches one. Forcing those
    into an enum would make the distinction the caller loses the one it needs.

    Attributes:
        action: Verb the backend used, in the backend's own spelling.
        name: Object the statement acts on.
        parent: Containing object, when the statement has one.
        sql: Rendered SQL, when the backend chose to record it.
        level: Nesting depth of the affected object, when it has one.
    """

    action: str
    name: str
    parent: Optional[str] = None
    sql: Optional[str] = None
    level: Optional[int] = None


@dataclass(frozen=True)
class PartitionReport:
    """The state of one maintenance target and what an operation did to it.

    Every backend returns this envelope, whether its target is a parent table, a
    partition function, or a single table. A field an engine cannot populate
    stays empty rather than being replaced by a different shape.

    Attributes:
        target: Scope of the report: a parent table, a table, or a partition
            function/scheme name.
        engine: Backend name, when the executor records one.
        extras: Engine-specific facts that belong to the report rather than a
            single row, such as SQL Server's function, scheme and table
            collections.
        partitions: Catalogue rows, in the order the backend read them.
        missing: ``(parent, name)`` pairs the plan expects but the catalogue
            does not contain.
        orphans: Partitions that exist but that the plan does not describe.
        issues: Read-only findings such as gaps, overlaps or strategy
            mismatches None of them repairs anything.
        operations: Statements the executor ran or would run.
        added: Names the executor created, for backends that report outcomes by
            name rather than by statement.
        dropped: Names the executor removed.
        skipped: ``(name, reason)`` pairs for work the executor deliberately
            refused, including reasons that need a different verb first.
        errors: Failures an engine with non-transactional DDL reports per
            statement instead of raising.
        dry_run: Whether the report describes an operation that was not
            executed.
    """

    target: str
    engine: Optional[str] = None
    extras: Mapping[str, Any] = field(default_factory=dict)
    partitions: Tuple[PartitionInfo, ...] = ()
    missing: Tuple[Tuple[str, str], ...] = ()
    orphans: Tuple[str, ...] = ()
    issues: Tuple[str, ...] = ()
    operations: Tuple[PartitionOperation, ...] = ()
    added: Tuple[str, ...] = ()
    dropped: Tuple[str, ...] = ()
    skipped: Tuple[Tuple[str, str], ...] = ()
    errors: Tuple[str, ...] = ()
    dry_run: bool = False

    def children_of(self, name: str) -> Tuple[str, ...]:
        """Return the names whose parent is *name*.

        Args:
            name: Parent name to look up.

        Returns:
            Child names, or an empty tuple when *name* has none.
        """
        return tuple(info.name for info in self.partitions if info.parent == name)

    @property
    def partition_names(self) -> Tuple[str, ...]:
        """Return the names one level below the target.

        A row qualifies when it names no parent, or names the target as its
        parent, and is not the target row itself. That covers a flat report
        (MySQL, ClickHouse) and a recursive one (PostgreSQL, Oracle) without
        counting subpartitions.

        Returns:
            First-level partition names.
        """
        return tuple(
            info.name
            for info in self.partitions
            if info.name != self.target
            and (info.parent is None or info.parent == self.target)
        )

    @property
    def tree(self) -> Dict[str, Tuple[str, ...]]:
        """Return direct children grouped by parent name.

        Only rows that name a parent appear in the mapping. A flat report --
        MySQL's definitions, ClickHouse's rows -- therefore produces an empty
        mapping, which says there is no tree to show rather than inventing one.

        Returns:
            A mapping of parent name to child names.
        """
        grouped: Dict[str, List[str]] = {}
        for info in self.partitions:
            if info.parent is not None:
                grouped.setdefault(info.parent, []).append(info.name)
        return {key: tuple(names) for key, names in grouped.items()}

    @property
    def leaves(self) -> Tuple[PartitionInfo, ...]:
        """Return the rows that no other row names as its parent.

        In a recursive report this is the deepest row of every branch; in a
        flat report it is every row, because a flat engine has no children to
        exclude.
        """
        parents = {info.parent for info in self.partitions if info.parent is not None}
        return tuple(info for info in self.partitions if info.name not in parents)

    @property
    def has_errors(self) -> bool:
        """Return whether the executor recorded an error the caller must see."""
        return bool(self.errors)


@dataclass(frozen=True)
class PairedDifference:
    """One first-level partition present on exactly one side of a declared pair.

    This is the B set, not the symmetric difference of the two reports'
    ``missing`` collections. A row belongs here only when the catalogue of one
    target actually holds a first-level partition and the other target's
    catalogue does not:

    - A bucket absent from both sides belongs to each report's own ``missing``.
      It is a per-target fact, not drift between the pair.
    - A bucket present on both sides whose boundary text disagrees belongs to
      :attr:`PartitionBatchReport.issues`. That is structure the pair cannot
      compare, not a missing partition.

    Attributes:
        pair: Caller-chosen name for the pair, such as ``"log_tables"``.
        key: Normalized bucket the two sides are compared on, such as
            ``"2026_01"``.
        present_in: Side that holds the row: ``"left"`` or ``"right"``.
        left_partition: Name the left catalogue reported, or ``None`` when the
            row is only on the right.
        right_partition: Name the right catalogue reported, or ``None`` when
            the row is only on the left.
    """

    pair: str
    key: str
    present_in: str
    left_partition: Optional[str]
    right_partition: Optional[str]


@dataclass(frozen=True)
class PartitionBatchReport:
    """Reports for one batch, plus drift between the pairs the caller declared.

    The batch does not flatten the per-target reports. Each target keeps its
    own ``missing`` and ``orphans``; ``differences`` is only the paired view
    described on :class:`PairedDifference`.

    Attributes:
        reports: Mapping of target name to the original report, so each target's
            ``missing`` and ``orphans`` stay attributable.
        pairs: Pair names the caller declared, in the order it declared them.
            ``pairs`` may be empty for an independent batch, in which case
            ``differences`` is empty as well.
        differences: First-level partitions present on exactly one side of a
            declared pair. Sorted by ``(pair, key)`` in ``__post_init__`` so two
            backends that saw the same drift emit the same order.
        issues: Reasons the pair could not be compared, such as incompatible
            plans or boundary text that disagrees for a bucket present on both
            sides. Findings here never appear in ``differences``.
    """

    reports: Mapping[str, PartitionReport]
    pairs: Tuple[str, ...]
    differences: Tuple[PairedDifference, ...]
    issues: Tuple[str, ...]

    def __post_init__(self) -> None:
        """Order differences by pair name, then bucket key."""
        object.__setattr__(
            self,
            "differences",
            tuple(sorted(self.differences, key=lambda diff: (diff.pair, diff.key))),
        )
