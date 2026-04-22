# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_protocol_conformance.py
"""
Tests to verify SQLiteDialect protocol conformance and protocol non-overlap.

This test ensures:
1. SQLiteDialect implements all methods defined in the protocols it claims to support
2. Different protocols do not have overlapping method names (which causes confusion)

These tests serve as a regression prevention layer for the protocol design.
"""
import sys
from itertools import combinations
from typing import Protocol

if sys.version_info >= (3, 13):
    from typing import get_protocol_members
elif sys.version_info >= (3, 12):
    from typing import _get_protocol_attrs as get_protocol_members

import pytest
from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.impl.sqlite import dialect as sqlite_dialect
from rhosocial.activerecord.backend.impl.sqlite import protocols as sqlite_protocols


def get_all_protocol_methods(proto: type) -> set:
    """Extract all public method names from a protocol."""
    members = set()
    if sys.version_info >= (3, 13):
        members = get_protocol_members(proto)
    else:
        for name in proto.__dict__:
            if name.startswith("_"):
                continue
            val = proto.__dict__[name]
            if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
                members.add(name)
        members.update(
            k for k in getattr(proto, "__annotations__", {})
            if not k.startswith("_")
        )
    return members


SQLITE_PROTOCOLS = [
    sqlite_protocols.VirtualTableSupport,
    sqlite_protocols.SQLitePragmaSupport,
    sqlite_protocols.SQLiteExtensionSupport,
    dialect_protocols.CTESupport,
    dialect_protocols.FilterClauseSupport,
    dialect_protocols.WindowFunctionSupport,
    dialect_protocols.JSONSupport,
    dialect_protocols.ReturningSupport,
    dialect_protocols.AdvancedGroupingSupport,
    dialect_protocols.ArraySupport,
    dialect_protocols.ExplainSupport,
    dialect_protocols.GraphSupport,
    dialect_protocols.LockingSupport,
    dialect_protocols.MergeSupport,
    dialect_protocols.OrderedSetAggregationSupport,
    dialect_protocols.QualifyClauseSupport,
    dialect_protocols.TemporalTableSupport,
    dialect_protocols.UpsertSupport,
    dialect_protocols.LateralJoinSupport,
    dialect_protocols.WildcardSupport,
    dialect_protocols.JoinSupport,
    dialect_protocols.SetOperationSupport,
    dialect_protocols.ViewSupport,
    dialect_protocols.TableSupport,
    dialect_protocols.ConstraintSupport,
    dialect_protocols.TruncateSupport,
    dialect_protocols.SchemaSupport,
    dialect_protocols.IndexSupport,
    dialect_protocols.SequenceSupport,
    dialect_protocols.TriggerSupport,
    dialect_protocols.GeneratedColumnSupport,
    dialect_protocols.IntrospectionSupport,
    dialect_protocols.TransactionControlSupport,
    dialect_protocols.SQLFunctionSupport,
]


class TestSQLiteDialectProtocolConformance:
    """Assert SQLiteDialect implements all protocols it declares to support."""

    @pytest.fixture
    def dialect(self):
        """Create a SQLiteDialect instance for testing."""
        return sqlite_dialect.SQLiteDialect()

    @pytest.mark.parametrize("protocol", SQLITE_PROTOCOLS)
    def test_implements_protocol(self, dialect, protocol):
        """SQLiteDialect should implement each protocol in SQLITE_PROTOCOLS."""
        assert isinstance(dialect, protocol), (
            f"SQLiteDialect does not implement protocol {protocol.__name__}, "
            f"missing methods: {get_all_protocol_members(protocol) - set(dir(dialect))}"
        )


class TestProtocolNonOverlap:
    """Assert protocols do not have overlapping method names."""

    def test_no_interface_overlap_between_protocols(self):
        """No two protocols should share the same method name."""
        member_map = {
            proto.__name__: get_all_protocol_methods(proto)
            for proto in SQLITE_PROTOCOLS
        }

        for name, members in member_map.items():
            assert len(members) > 0, f"Protocol {name} has no members defined"

        excluded_overlaps = set()

        violations = []
        for (name_a, members_a), (name_b, members_b) in combinations(member_map.items(), 2):
            if (name_a, name_b) in excluded_overlaps:
                continue
            overlap = members_a & members_b
            if overlap:
                violations.append(f"{name_a} ∩ {name_b} = {overlap}")

        assert not violations, (
            "The following protocols have overlapping interfaces, need to merge or rename:\n"
            + "\n".join(f"  • {v}" for v in violations)
        )