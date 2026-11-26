# tests/rhosocial/activerecord_test/feature/backend/core/test_introspection_protocol_split.py
"""Guard the four-family split of the introspection protocol surface.

The single ``IntrospectionSupport`` protocol was split into four families so a
dialect can answer one question -- declarations, behaviour, data, retained text
-- without claiming the others. This test pins the split itself:

* each family declares exactly its members, in order;
* its async twin declares the same members;
* the sync and async mixin of each family declare the same members;
* the two composition-only aggregates declare none and inherit the four;
* the old single-name and ``supports_partition_info`` are gone from ``src``.
"""

import re
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.dialect import mixins, protocols

pytestmark = [pytest.mark.feature, pytest.mark.backend]


STRUCTURE_MEMBERS = [
    # Capability detection
    "supports_introspection",
    "supports_database_info",
    "supports_table_introspection",
    "supports_column_introspection",
    "supports_index_introspection",
    "supports_foreign_key_introspection",
    "supports_view_introspection",
    "supports_trigger_introspection",
    "supports_extensions",
    "supports_table_storage_introspection",
    # Query formatting
    "format_database_info_query_statement",
    "format_table_list_query_statement",
    "format_table_info_query_statement",
    "format_column_info_query_statement",
    "format_index_info_query_statement",
    "format_foreign_key_query_statement",
    "format_view_list_query_statement",
    "format_view_info_query_statement",
    "format_trigger_list_query_statement",
    "format_trigger_info_query_statement",
]

OPERATIONAL_STATS_MEMBERS = [
    # Capability detection
    "supports_runtime_stats",
    "supports_index_stats",
    "supports_table_stats",
    "supports_unused_indexes_detection",
    "supports_object_dependencies",
    # Query formatting
    "format_unused_indexes_query_statement",
    "format_table_usage_stats_query_statement",
    "format_runtime_metrics_query_statement",
    "format_index_usage_stats_query_statement",
    "format_object_dependency_query_statement",
]

DATA_PROFILE_MEMBERS = [
    # Capability detection
    "supports_column_data_profile",
    "supports_column_value_sample",
    "supports_join_coverage",
    # Query formatting
    "format_column_data_profile_query_statement",
    "format_column_value_sample_query_statement",
    "format_join_coverage_query_statement",
]

DDL_EXTRACTION_MEMBERS = [
    # Capability detection
    "supports_ddl_extraction",
    "supports_ddl_extraction_native",
    # Query formatting
    "format_ddl_statement_query_statement",
]

# family -> (sync protocol, async protocol, sync mixin, async mixin, members)
FAMILIES = [
    (
        "StructureIntrospectionSupport",
        "AsyncStructureIntrospectionSupport",
        "StructureIntrospectionMixin",
        "AsyncStructureIntrospectionMixin",
        STRUCTURE_MEMBERS,
    ),
    (
        "OperationalStatsIntrospectionSupport",
        "AsyncOperationalStatsIntrospectionSupport",
        "OperationalStatsIntrospectionMixin",
        "AsyncOperationalStatsIntrospectionMixin",
        OPERATIONAL_STATS_MEMBERS,
    ),
    (
        "DataProfileIntrospectionSupport",
        "AsyncDataProfileIntrospectionSupport",
        "DataProfileIntrospectionMixin",
        "AsyncDataProfileIntrospectionMixin",
        DATA_PROFILE_MEMBERS,
    ),
    (
        "DdlExtractionIntrospectionSupport",
        "AsyncDdlExtractionIntrospectionSupport",
        "DdlExtractionIntrospectionMixin",
        "AsyncDdlExtractionIntrospectionMixin",
        DDL_EXTRACTION_MEMBERS,
    ),
]


def _own_members(cls: type) -> list:
    """Public members declared on *cls* itself, in declaration order."""
    out = []
    for name, value in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if callable(value) or isinstance(value, (property, classmethod, staticmethod)):
            out.append(name)
    return out


@pytest.mark.parametrize("sync_proto,async_proto,sync_mixin,async_mixin,members", FAMILIES)
def test_family_protocols_declare_exactly_their_members(
    sync_proto, async_proto, sync_mixin, async_mixin, members
):
    """Each family protocol declares its members, in order, and nothing else."""
    protocol = getattr(protocols, sync_proto)
    assert _own_members(protocol) == members


@pytest.mark.parametrize("sync_proto,async_proto,sync_mixin,async_mixin,members", FAMILIES)
def test_async_twins_mirror_the_family_members(
    sync_proto, async_proto, sync_mixin, async_mixin, members
):
    """The async protocol exists and declares the same members as its sync twin."""
    async_twin = getattr(protocols, async_proto)
    assert _own_members(async_twin) == members


@pytest.mark.parametrize("sync_proto,async_proto,sync_mixin,async_mixin,members", FAMILIES)
def test_each_mixin_matches_its_protocol(
    sync_proto, async_proto, sync_mixin, async_mixin, members
):
    """Both mixins of a family declare exactly the protocol's member list."""
    assert _own_members(getattr(mixins, sync_mixin)) == members
    assert _own_members(getattr(mixins, async_mixin)) == members


def test_aggregators_declare_no_members_and_compose_the_four():
    """``IntrospectionMixin`` and its async twin are composition-only."""
    assert _own_members(mixins.IntrospectionMixin) == []
    assert _own_members(mixins.AsyncIntrospectionMixin) == []

    assert mixins.IntrospectionMixin.__bases__ == (
        mixins.StructureIntrospectionMixin,
        mixins.OperationalStatsIntrospectionMixin,
        mixins.DataProfileIntrospectionMixin,
        mixins.DdlExtractionIntrospectionMixin,
    )
    assert mixins.AsyncIntrospectionMixin.__bases__ == (
        mixins.AsyncStructureIntrospectionMixin,
        mixins.AsyncOperationalStatsIntrospectionMixin,
        mixins.AsyncDataProfileIntrospectionMixin,
        mixins.AsyncDdlExtractionIntrospectionMixin,
    )


def test_the_old_single_name_is_not_exported():
    """The split replaced the single name; it must not survive as an alias."""
    assert not hasattr(protocols, "IntrospectionSupport")
    assert not hasattr(protocols, "AsyncIntrospectionSupport")

    from rhosocial.activerecord.backend import dialect

    assert not hasattr(dialect, "IntrospectionSupport")


def test_legacy_names_are_absent_from_src():
    """Neither the old protocol name nor ``supports_partition_info`` remains.

    The surviving partition switch is
    ``supports_partition_metadata_introspection`` in ``ddl/partition.py``.
    """
    root = Path(__file__).resolve().parents[6] / "src"
    patterns = {
        "IntrospectionSupport": re.compile(r"\bIntrospectionSupport\b"),
        "supports_partition_info": re.compile(r"\bsupports_partition_info\b"),
    }
    offenders = []
    for path in root.rglob("*"):
        if path.suffix not in {".py", ".md"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in patterns.items():
            if pattern.search(text):
                offenders.append(f"{path.relative_to(root)}: {label}")

    assert not offenders, (
        "legacy introspection names remain in src:\n" + "\n".join(f"  - {o}" for o in offenders)
    )
