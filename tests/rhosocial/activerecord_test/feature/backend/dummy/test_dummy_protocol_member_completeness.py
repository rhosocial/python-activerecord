# tests/rhosocial/activerecord_test/feature/backend/dummy/test_dummy_protocol_member_completeness.py
"""
Tests to verify DummyDialect implements all protocol members.

This test ensures that when protocols are updated in the main module,
DummyDialect is also updated to implement all new methods.

The test collects all method names from all protocols and verifies
that DummyDialect implements each one.
"""
import inspect
from typing import Protocol

import pytest
from rhosocial.activerecord.backend.dialect import protocols
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestDummyProtocolMemberCompleteness:
    """Test that DummyDialect implements all methods defined in protocols."""

    @pytest.fixture
    def dialect(self):
        """Create a DummyDialect instance for testing."""
        return DummyDialect()

    def get_all_protocol_classes(self):
        """Dynamically discover all Protocol classes in the protocols module."""
        protocol_classes = []
        for name, obj in inspect.getmembers(protocols, inspect.isclass):
            if Protocol in getattr(obj, '__mro__', []) and name != 'Protocol':
                protocol_classes.append((name, obj))
        return protocol_classes

    def get_all_protocol_methods(self):
        """Collect all public method names from all protocols."""
        all_methods = {}
        protocol_classes = self.get_all_protocol_classes()

        for proto_name, proto_class in protocol_classes:
            for member_name, member in inspect.getmembers(proto_class):
                if not member_name.startswith('_') and callable(member):
                    if member_name not in all_methods:
                        all_methods[member_name] = []
                    all_methods[member_name].append(proto_name)

        return all_methods

    def test_dummy_dialect_has_all_protocol_methods(self, dialect):
        """
        Verify DummyDialect implements ALL methods defined in ALL protocols.

        This test dynamically discovers all methods in all protocols and checks
        that DummyDialect has each one implemented.

        If this test fails, it means a new method was added to a protocol but
        DummyDialect was not updated to implement it.
        """
        all_protocol_methods = self.get_all_protocol_methods()

        # Get all methods from DummyDialect
        dialect_methods = set()
        for member_name in dir(dialect):
            if not member_name.startswith('_') and callable(getattr(dialect, member_name, None)):
                dialect_methods.add(member_name)

        # Check that all protocol methods are in DummyDialect
        missing_methods = []
        for method_name in all_protocol_methods:
            if method_name not in dialect_methods:
                missing_protocols = all_protocol_methods[method_name]
                missing_methods.append(f"{method_name} (from: {', '.join(missing_protocols)})")

        assert len(missing_methods) == 0, (
            f"DummyDialect is missing {len(missing_methods)} method(s) defined in protocols:\n"
            + "\n".join(f"  - {m}" for m in missing_methods) + "\n\n"
            "Please update DummyDialect to implement these methods."
        )

    def test_all_protocols_have_expected_methods(self):
        """
        Verify all protocol classes are properly detected.

        This is a sanity check to ensure the test infrastructure correctly
        discovers all protocols. If a protocol is not detected here,
        the main test won't check its methods.
        """
        protocol_classes = self.get_all_protocol_classes()
        protocol_names = [name for name, _ in protocol_classes]

        # Expected protocols (update this list when adding new protocols)
        expected_protocols = {
            'WindowFunctionSupport',
            'TriggerSupport',
            'FunctionSupport',
            'CTESupport',
            'WildcardSupport',
            'AdvancedGroupingSupport',
            'ReturningSupport',
            'UpsertSupport',
            'LateralJoinSupport',
            'JoinSupport',
            'ArraySupport',
            'JSONSupport',
            'ExplainSupport',
            'GraphSupport',
            'FilterClauseSupport',
            'OrderedSetAggregationSupport',
            'MergeSupport',
            'TemporalTableSupport',
            'QualifyClauseSupport',
            'LockingSupport',
            'SetOperationSupport',
            'TableSupport',
            'ViewSupport',
            'TruncateSupport',
            'SchemaSupport',
            'IndexSupport',
            'SequenceSupport',
            'ILIKESupport',
        }

        discovered_protocols = set(protocol_names)

        missing = expected_protocols - discovered_protocols
        extra = discovered_protocols - expected_protocols

        assert len(missing) == 0, (
            f"Protocols not discovered (test infrastructure issue): {missing}\n"
            "Please update expected_protocols in this test."
        )

        assert len(extra) == 0, (
            f"New protocols discovered that are not in expected list: {extra}\n"
            "Please update expected_protocols in this test."
        )

    def test_protocol_method_count(self):
        """
        Track total number of protocol methods to detect additions/removals.

        This test ensures that when methods are added to or removed from protocols,
        developers are alerted to update DummyDialect accordingly.
        """
        all_protocol_methods = self.get_all_protocol_methods()
        method_count = len(all_protocol_methods)

        # Expected count (update this when adding/removing methods from protocols)
        # As of the last update, there are 167 protocol methods
        expected_count = 167

        assert method_count == expected_count, (
            f"Protocol method count changed from {expected_count} to {method_count}.\n"
            f"Methods: {sorted(all_protocol_methods.keys())}\n\n"
            "If you added/removed methods from protocols, please:\n"
            "1. Update DummyDialect to implement the new methods\n"
            "2. Update expected_count in this test"
        )
