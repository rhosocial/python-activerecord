# tests/rhosocial/activerecord_test/feature/backend/partition/test_partition_contract.py
"""The engine-neutral partition-maintenance contract.

The backend owns the plan, the catalogue query and the DDL. What the core
standardizes is the answer shape -- one row per partition, one record per
statement, one report envelope -- and the set of verbs a caller may detect on
an executor. These tests pin that shape and the feature detection, not the
engine behaviour that the backend repositories test against live servers.
"""

import pytest
from dataclasses import FrozenInstanceError

from rhosocial.activerecord.backend.partition import (
    AsyncPartitionEnsurer,
    AsyncPartitionInventory,
    AsyncPartitionRetention,
    AsyncPartitionValidator,
    PartitionEnsurer,
    PartitionInfo,
    PartitionInventory,
    PartitionOperation,
    PartitionReport,
    PartitionRetention,
    PartitionValidator,
)


class _SyncExecutor:
    """A sync executor that offers every canonical verb."""

    def list(self, plan=None):
        return PartitionReport(target="events")

    def ensure(self, plan):
        return PartitionReport(target="events")

    def drop_before(self, plan, cutoff):
        return PartitionReport(target="events", dry_run=True)

    def validate(self, plan):
        return PartitionReport(target="events")


class _ListingOnly:
    """A sync executor that can read but cannot change anything."""

    def list(self):
        return PartitionReport(target="events")


class _AsyncExecutor:
    """An async executor that offers every canonical verb."""

    async def list(self, plan=None):
        return PartitionReport(target="events")

    async def ensure(self, plan):
        return PartitionReport(target="events")

    async def drop_before(self, plan, cutoff):
        return PartitionReport(target="events", dry_run=True)

    async def validate(self, plan):
        return PartitionReport(target="events")


class TestPartitionInfo:
    """One row per partition, in the shape every engine can fill."""

    def test_a_minimal_row_keeps_only_the_name(self):
        info = PartitionInfo(name="events_2026_01")

        assert info.parent is None
        assert info.level == 0
        assert info.method is None
        assert info.bound is None
        assert info.schema is None
        assert info.row_count is None
        assert info.size_bytes is None
        assert info.is_partitioned is False
        assert dict(info.extras) == {}

    def test_engine_specific_facts_live_in_extras(self):
        info = PartitionInfo(
            name="events_2026_01",
            parent="events",
            level=1,
            extras={"subpartition_count": 4, "partition_number": 2},
        )

        assert info.extras["subpartition_count"] == 4
        assert info.extras["partition_number"] == 2

    def test_extras_default_is_not_shared_between_rows(self):
        first = PartitionInfo(name="events_2026_01")
        second = PartitionInfo(name="events_2026_02")

        assert first.extras is not second.extras

    def test_a_row_is_immutable(self):
        info = PartitionInfo(name="events_2026_01")

        with pytest.raises(FrozenInstanceError):
            info.name = "events_2026_02"


class TestPartitionOperation:
    """One record per statement, with the engine's own action word."""

    def test_optional_fields_default_to_absent(self):
        operation = PartitionOperation(action="create", name="events_2026_01")

        assert operation.parent is None
        assert operation.sql is None
        assert operation.level is None

    def test_the_engine_keeps_its_own_action_word(self):
        operation = PartitionOperation(
            action="split",
            name="events_2026_01",
            sql="ALTER PARTITION FUNCTION ... SPLIT RANGE (...)",
        )

        assert operation.action == "split"
        assert operation.sql == "ALTER PARTITION FUNCTION ... SPLIT RANGE (...)"


class TestPartitionReport:
    """One envelope for the catalogue state and the operation's outcome."""

    def test_empty_report_names_its_target_only(self):
        report = PartitionReport(target="events")

        assert report.target == "events"
        assert report.engine is None
        assert report.partitions == ()
        assert report.operations == ()
        assert report.dry_run is False
        assert report.has_errors is False

    def test_tree_groups_children_under_their_parent(self):
        report = PartitionReport(
            target="events",
            partitions=(
                PartitionInfo(name="events", level=0, is_partitioned=True),
                PartitionInfo(name="events_2026_01", parent="events", level=1),
                PartitionInfo(name="events_2026_02", parent="events", level=1),
                PartitionInfo(name="events_2026_01_p0", parent="events_2026_01", level=2),
            ),
        )

        assert report.tree == {
            "events": ("events_2026_01", "events_2026_02"),
            "events_2026_01": ("events_2026_01_p0",),
        }
        assert report.children_of("events") == ("events_2026_01", "events_2026_02")
        assert report.children_of("events_2026_01") == ("events_2026_01_p0",)
        assert report.children_of("missing") == ()

    def test_a_flat_report_has_no_tree(self):
        report = PartitionReport(
            target="events",
            partitions=(
                PartitionInfo(name="events_2026_01"),
                PartitionInfo(name="events_2026_02"),
            ),
        )

        assert report.tree == {}
        assert report.partition_names == ("events_2026_01", "events_2026_02")

    def test_the_target_row_is_not_a_partition_name(self):
        report = PartitionReport(
            target="events",
            partitions=(
                PartitionInfo(name="events", level=0, is_partitioned=True),
                PartitionInfo(name="events_2026_01", parent="events", level=1),
            ),
        )

        assert report.partition_names == ("events_2026_01",)

    def test_recursive_leaves_are_the_deepest_rows(self):
        report = PartitionReport(
            target="events",
            partitions=(
                PartitionInfo(name="events", level=0, is_partitioned=True),
                PartitionInfo(name="events_2026_01", parent="events", level=1, is_partitioned=True),
                PartitionInfo(name="events_2026_02", parent="events", level=1),
                PartitionInfo(name="events_2026_01_p0", parent="events_2026_01", level=2),
            ),
        )

        leaves = {info.name for info in report.leaves}
        assert leaves == {"events_2026_02", "events_2026_01_p0"}

    def test_flat_leaves_are_every_row(self):
        report = PartitionReport(
            target="events",
            partitions=(
                PartitionInfo(name="events_2026_01"),
                PartitionInfo(name="events_2026_02"),
            ),
        )

        assert {info.name for info in report.leaves} == {"events_2026_01", "events_2026_02"}

    def test_errors_are_reported_rather_than_raised(self):
        report = PartitionReport(
            target="events",
            errors=("ADD PARTITION events_2026_02 failed: ORA-14074",),
        )

        assert report.has_errors is True

    def test_engine_specific_report_facts_live_in_extras(self):
        report = PartitionReport(
            target="orders",
            extras={"functions": ("order_month_fn",), "schemes": ("order_month_scheme",)},
        )

        assert report.extras["functions"] == ("order_month_fn",)
        assert report.extras["schemes"] == ("order_month_scheme",)

    def test_report_extras_default_is_not_shared_between_reports(self):
        first = PartitionReport(target="events")
        second = PartitionReport(target="orders")

        assert first.extras is not second.extras

    def test_a_dry_run_is_visible_in_the_report(self):
        report = PartitionReport(
            target="events",
            operations=(PartitionOperation(action="drop", name="events_2026_01"),),
            dry_run=True,
        )

        assert report.dry_run is True
        assert len(report.operations) == 1


class TestMaintenanceProtocols:
    """Each verb is its own protocol, so a caller can ask what exists."""

    def test_a_full_sync_executor_detects_every_verb(self):
        executor = _SyncExecutor()

        assert isinstance(executor, PartitionInventory)
        assert isinstance(executor, PartitionEnsurer)
        assert isinstance(executor, PartitionRetention)
        assert isinstance(executor, PartitionValidator)

    def test_a_listing_only_executor_claims_only_inventory(self):
        executor = _ListingOnly()

        assert isinstance(executor, PartitionInventory)
        assert not isinstance(executor, PartitionEnsurer)
        assert not isinstance(executor, PartitionRetention)
        assert not isinstance(executor, PartitionValidator)

    def test_an_ordinary_object_satisfies_none_of_them(self):
        executor = object()

        assert not isinstance(executor, PartitionInventory)
        assert not isinstance(executor, PartitionEnsurer)
        assert not isinstance(executor, PartitionRetention)
        assert not isinstance(executor, PartitionValidator)

    def test_a_full_async_executor_detects_every_async_verb(self):
        executor = _AsyncExecutor()

        assert isinstance(executor, AsyncPartitionInventory)
        assert isinstance(executor, AsyncPartitionEnsurer)
        assert isinstance(executor, AsyncPartitionRetention)
        assert isinstance(executor, AsyncPartitionValidator)
