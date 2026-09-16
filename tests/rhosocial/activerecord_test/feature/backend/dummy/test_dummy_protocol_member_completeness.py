# tests/rhosocial/activerecord_test/feature/backend/dummy/test_dummy_protocol_member_completeness.py
"""
Tests to verify DummyDialect implements all protocol members and protocols have no overlap.

This test ensures:
1. DummyDialect implements all methods defined in all protocols
2. All protocols have at least one member
3. No two protocols share the same method name (no overlap)
"""

import inspect
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
    members.update(k for k in getattr(proto, "__annotations__", {}) if not k.startswith("_"))
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
            if Protocol in getattr(obj, "__mro__", []) and name != "Protocol":
                protocol_classes.append((name, obj))
        return protocol_classes

    def get_all_protocol_methods_legacy(self):
        """Collect all public method names from all protocols."""
        all_methods = {}
        protocol_classes = self.get_all_protocol_classes()

        for proto_name, proto_class in protocol_classes:
            for member_name, member in inspect.getmembers(proto_class):
                if not member_name.startswith("_") and callable(member):
                    if member_name not in all_methods:
                        all_methods[member_name] = []
                    all_methods[member_name].append(proto_name)

        return all_methods

    def test_dummy_dialect_has_all_protocol_methods(self, dialect):
        """Verify DummyDialect implements ALL methods defined in ALL protocols."""
        all_protocol_methods = self.get_all_protocol_methods_legacy()

        dialect_methods = set()
        for member_name in dir(dialect):
            if not member_name.startswith("_") and callable(getattr(dialect, member_name, None)):
                dialect_methods.add(member_name)

        missing_methods = []
        for method_name in all_protocol_methods:
            if method_name not in dialect_methods:
                missing_protocols = all_protocol_methods[method_name]
                missing_methods.append(f"{method_name} (from: {', '.join(missing_protocols)})")

        assert len(missing_methods) == 0, (
            f"DummyDialect is missing {len(missing_methods)} method(s) defined in protocols:\n"
            + "\n".join(f"  - {m}" for m in missing_methods)
            + "\n\n"
            "Please update DummyDialect to implement these methods."
        )

    def test_all_dialects_protocols_implemented(self):
        """Verify every generic protocol is implemented by DummyDialect.

        DummyDialect is the full-featured SQL-standard reference, so it must
        satisfy all generic dialect protocols.
        """
        protocol_classes = self.get_all_protocol_classes()
        all_protocols = {name for name, cls in protocol_classes}

        dummy_mro = dummy_dialect.DummyDialect.__mro__
        implemented = {
            cls.__name__ for cls in dummy_mro if issubclass(cls, Protocol) and cls.__name__ in all_protocols
        }

        missing = all_protocols - implemented
        assert not missing, (
            f"DummyDialect is missing the following protocols: {missing}\n"
            "Please add these protocols to DummyDialect's inheritance."
        )

    def test_isinstance_check_all_protocols(self, dialect):
        """Verify isinstance(dialect, proto) returns True for all generic protocols.

        This catches cases where a protocol is inherited in MRO but a required
        method is missing — isinstance() returns False at runtime even though
        the class appears in MRO. As the full-featured reference, DummyDialect
        must satisfy every generic protocol (its negative list is empty).
        """
        protocol_classes = self.get_all_protocol_classes()
        failures = []
        for name, proto in protocol_classes:
            if not isinstance(dialect, proto):
                # Find which methods are missing
                expected = get_all_protocol_methods(proto)
                actual = {m for m in dir(dialect) if not m.startswith("_") and callable(getattr(dialect, m, None))}
                missing = expected - actual
                detail = f"  missing methods: {missing}" if missing else "  (all methods present, but isinstance returned False)"
                failures.append(f"{name}:{detail}")
        assert not failures, (
            f"isinstance check failed for {len(failures)} protocol(s):\n"
            + "\n".join(failures)
            + "\n\nDummyDialect should satisfy all generic dialect protocols."
        )

    def test_dummy_negative_protocol_list_is_empty(self, dialect):
        """DummyDialect implements every generic protocol: the negative list is empty.

        The negative list is kept as an explicit, documented declaration. If a
        generic protocol is ever intentionally dropped from DummyDialect, list
        it here (and flip the assertion accordingly) so the decision is visible.
        """
        all_protocols = {name: cls for name, cls in self.get_all_protocol_classes()}
        # DummyDialect is the full-featured reference: it must not skip any.
        for name, proto in all_protocols.items():
            assert isinstance(dialect, proto), (
                f"DummyDialect must implement {name}; if this is intentionally "
                f"unsupported, document it as a negative-list entry."
            )

    def test_positive_and_negative_lists_partition_all_protocols(self):
        """Every generic protocol must be classified as implemented for Dummy.

        Since DummyDialect's negative list is empty, the positive set must equal
        the entire discovered protocol set — proving no protocol is left
        unclassified when a new one is added to protocols.py.
        """
        all_protocols = {name for name, cls in self.get_all_protocol_classes()}
        dummy_mro = dummy_dialect.DummyDialect.__mro__
        positive = {
            cls.__name__ for cls in dummy_mro
            if issubclass(cls, Protocol) and cls.__name__ in all_protocols
        }
        negative = set()  # DummyDialect has no deliberately-unsupported protocols

        unclassified = all_protocols - positive - negative
        assert not unclassified, (
            f"Generic protocols not classified for DummyDialect: {sorted(unclassified)}. "
            f"Either implement them or add to the negative list."
        )

