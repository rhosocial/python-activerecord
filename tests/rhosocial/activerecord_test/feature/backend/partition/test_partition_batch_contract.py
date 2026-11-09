# tests/rhosocial/activerecord_test/feature/backend/partition/test_partition_batch_contract.py
"""The batch and paired-report contract of engine-neutral partition maintenance.

`PartitionBatchReport` keeps the per-target reports intact and adds only the
drift between caller-declared pairs. These tests pin the B semantics: only an
actual first-level partition present on exactly one side is a difference, while
two-side absence stays in each report's `missing` and boundary disagreement
stays in `issues`.
"""

import pytest
from dataclasses import FrozenInstanceError

from rhosocial.activerecord.backend.partition import (
    PairedDifference,
    PartitionBatchReport,
    PartitionInfo,
    PartitionReport,
)


class TestPairedDifference:
    """One row of the paired drift, naming the side that holds it."""

    def test_a_left_only_row_names_only_the_left_partition(self):
        difference = PairedDifference(
            pair="log_tables",
            key="2026_01",
            present_in="left",
            left_partition="events_2026_01",
            right_partition=None,
        )

        assert difference.present_in == "left"
        assert difference.left_partition == "events_2026_01"
        assert difference.right_partition is None

    def test_a_right_only_row_names_only_the_right_partition(self):
        difference = PairedDifference(
            pair="log_tables",
            key="2026_01",
            present_in="right",
            left_partition=None,
            right_partition="audit_2026_01",
        )

        assert difference.present_in == "right"
        assert difference.left_partition is None
        assert difference.right_partition == "audit_2026_01"

    def test_a_difference_is_immutable(self):
        difference = PairedDifference(
            pair="log_tables",
            key="2026_01",
            present_in="left",
            left_partition="events_2026_01",
            right_partition=None,
        )

        with pytest.raises(FrozenInstanceError):
            difference.pair = "other_tables"


class TestPartitionBatchReport:
    """Reports of several targets plus the drift between declared pairs."""

    def test_an_empty_batch_has_no_targets_and_no_drift(self):
        batch = PartitionBatchReport(
            reports={},
            pairs=(),
            differences=(),
            issues=(),
        )

        assert batch.reports == {}
        assert batch.pairs == ()
        assert batch.differences == ()
        assert batch.issues == ()

    def test_per_target_reports_are_preserved(self):
        events = PartitionReport(
            target="events",
            partitions=(PartitionInfo(name="events_2026_01"),),
            missing=(("events", "events_2025_12"),),
        )
        audit = PartitionReport(
            target="audit",
            partitions=(PartitionInfo(name="audit_2026_01"),),
            orphans=("audit_2025_11",),
        )
        reports = {"events": events, "audit": audit}
        batch = PartitionBatchReport(
            reports=reports,
            pairs=("log_tables",),
            differences=(),
            issues=(),
        )

        assert batch.reports == reports
        assert batch.reports["events"].missing == events.missing
        assert batch.reports["audit"].orphans == audit.orphans

    def test_a_single_side_difference_is_reported_left(self):
        events = PartitionReport(
            target="events",
            partitions=(PartitionInfo(name="events_2026_01", level=1),),
        )
        audit = PartitionReport(target="audit")
        difference = PairedDifference(
            pair="log_tables",
            key="2026_01",
            present_in="left",
            left_partition="events_2026_01",
            right_partition=None,
        )
        batch = PartitionBatchReport(
            reports={"events": events, "audit": audit},
            pairs=("log_tables",),
            differences=(difference,),
            issues=(),
        )

        assert batch.differences == (difference,)
        assert batch.differences[0].present_in == "left"
        assert batch.differences[0].right_partition is None

    def test_a_single_side_difference_is_reported_right(self):
        events = PartitionReport(target="events")
        audit = PartitionReport(
            target="audit",
            partitions=(PartitionInfo(name="audit_2026_01", level=1),),
        )
        difference = PairedDifference(
            pair="log_tables",
            key="2026_01",
            present_in="right",
            left_partition=None,
            right_partition="audit_2026_01",
        )
        batch = PartitionBatchReport(
            reports={"events": events, "audit": audit},
            pairs=("log_tables",),
            differences=(difference,),
            issues=(),
        )

        assert batch.differences == (difference,)
        assert batch.differences[0].present_in == "right"
        assert batch.differences[0].left_partition is None

    def test_two_side_absence_stays_in_each_report_missing(self):
        events = PartitionReport(
            target="events",
            missing=(("events", "events_2025_12"),),
        )
        audit = PartitionReport(
            target="audit",
            missing=(("audit", "audit_2025_12"),),
        )
        batch = PartitionBatchReport(
            reports={"events": events, "audit": audit},
            pairs=("log_tables",),
            differences=(),
            issues=(),
        )

        assert batch.differences == ()
        assert batch.reports["events"].missing == (("events", "events_2025_12"),)
        assert batch.reports["audit"].missing == (("audit", "audit_2025_12"),)

    def test_boundary_disagreement_is_an_issue_not_a_difference(self):
        events = PartitionReport(
            target="events",
            partitions=(
                PartitionInfo(
                    name="events_2026_01",
                    parent="events",
                    level=1,
                    bound="[2026-01-01, 2026-02-01)",
                ),
            ),
        )
        audit = PartitionReport(
            target="audit",
            partitions=(
                PartitionInfo(
                    name="audit_2026_01",
                    parent="audit",
                    level=1,
                    bound="[2026-01-01, 2026-01-20)",
                ),
            ),
        )
        batch = PartitionBatchReport(
            reports={"events": events, "audit": audit},
            pairs=("log_tables",),
            differences=(),
            issues=("log_tables: boundary for 2026_01 disagrees",),
        )

        assert batch.differences == ()
        assert batch.issues == ("log_tables: boundary for 2026_01 disagrees",)

    def test_differences_are_ordered_by_pair_then_key(self):
        zeta = PairedDifference(
            pair="zeta",
            key="2026_01",
            present_in="left",
            left_partition="events_2026_01",
            right_partition=None,
        )
        alpha_later = PairedDifference(
            pair="alpha",
            key="2026_02",
            present_in="right",
            left_partition=None,
            right_partition="audit_2026_02",
        )
        alpha_earlier = PairedDifference(
            pair="alpha",
            key="2026_01",
            present_in="left",
            left_partition="events_2026_01",
            right_partition=None,
        )
        forward = PartitionBatchReport(
            reports={},
            pairs=("alpha", "zeta"),
            differences=(zeta, alpha_later, alpha_earlier),
            issues=(),
        )
        reverse = PartitionBatchReport(
            reports={},
            pairs=("alpha", "zeta"),
            differences=(alpha_earlier, alpha_later, zeta),
            issues=(),
        )

        assert tuple((item.pair, item.key) for item in forward.differences) == (
            ("alpha", "2026_01"),
            ("alpha", "2026_02"),
            ("zeta", "2026_01"),
        )
        assert forward.differences == reverse.differences

    def test_a_batch_is_immutable(self):
        batch = PartitionBatchReport(
            reports={"events": PartitionReport(target="events")},
            pairs=("log_tables",),
            differences=(),
            issues=(),
        )

        assert isinstance(batch.differences, tuple)
        with pytest.raises(FrozenInstanceError):
            batch.reports = {}
        with pytest.raises(FrozenInstanceError):
            batch.pairs = ()
