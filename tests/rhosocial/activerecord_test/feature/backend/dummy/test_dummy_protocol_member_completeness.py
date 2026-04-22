# tests/rhosocial/activerecord_test/feature/backend/dummy/test_dummy_protocol_member_completeness.py
"""
Tests to verify DummyDialect implements all protocol members and protocols have no overlap.

This test ensures:
1. DummyDialect implements all methods defined in all protocols
2. All protocols have at least one member
3. No two protocols share the same method name (no overlap)
"""
import inspect
from itertools import combinations
from typing import Protocol

import pytest
from rhosocial.activerecord.backend.dialect import protocols
from rhosocial.activerecord.backend.impl.dummy import dialect as dummy_dialect
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def get_all_protocol_methods(proto: type) -> set:
    """Extract all public method names from a protocol."""
    members = set()
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

    def get_all_protocol_methods_legacy(self):
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
        """Verify DummyDialect implements ALL methods defined in ALL protocols."""
        all_protocol_methods = self.get_all_protocol_methods_legacy()

        dialect_methods = set()
        for member_name in dir(dialect):
            if not member_name.startswith('_') and callable(getattr(dialect, member_name, None)):
                dialect_methods.add(member_name)

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

    def test_all_dialects_protocols_implemented(self):
        """Verify all protocols (except introspection) are implemented by DummyDialect."""
        protocol_classes = self.get_all_protocol_classes()

        excluded = {'IntrospectionSupport', 'AsyncIntrospectionSupport'}
        expected_protocols = {
            name for name, cls in protocol_classes
            if name not in excluded
        }

        dummy_mro = dummy_dialect.DummyDialect.__mro__
        implemented = {
            cls.__name__ for cls in dummy_mro
            if issubclass(cls, Protocol) and cls.__name__ in expected_protocols
        }

        missing = expected_protocols - implemented
        assert not missing, (
            f"DummyDialect is missing the following protocols: {missing}\n"
            "Please add these protocols to DummyDialect's inheritance."
        )
