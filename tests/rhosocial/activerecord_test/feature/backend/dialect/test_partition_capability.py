# tests/rhosocial/activerecord_test/feature/backend/dialect/test_partition_capability.py
"""The partition capability vocabulary and its backward-compatible derivation.

The enum restates a single boolean as three situations, so the derivation must
keep every existing dialect's meaning: a dialect that answers
``supports_table_partitioning()`` ``True`` keeps ``NATIVE``, one that answers
``False`` keeps ``UNSUPPORTED``, and only an explicit override reaches
``AUTOMATIC``.
"""

import inspect

import pytest

from rhosocial.activerecord.backend.dialect import PartitionCapability
from rhosocial.activerecord.backend.dialect.mixins import PartitionMixin
from rhosocial.activerecord.backend.dialect.protocols import PartitionSupport
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def test_members_are_the_three_possible_relationships():
    """One member per real-world relationship, in the documented order."""
    assert [member.name for member in PartitionCapability] == [
        "NATIVE",
        "AUTOMATIC",
        "UNSUPPORTED",
    ]
    assert {member.value for member in PartitionCapability} == {
        "native",
        "automatic",
        "unsupported",
    }


def test_members_are_strings():
    """String-valued so they serialize without a custom encoder."""
    for member in PartitionCapability:
        assert isinstance(member, str)
        assert str(member) == member.value


def test_automatic_is_constructible_from_its_value():
    """AUTOMATIC is a real member, not documentation-only."""
    assert PartitionCapability("automatic") is PartitionCapability.AUTOMATIC


def test_automatic_compares_as_its_string_and_differs_from_other_members():
    """Comparable both as an enum member and as the plain string value."""
    assert PartitionCapability.AUTOMATIC == "automatic"
    assert PartitionCapability.AUTOMATIC != PartitionCapability.NATIVE
    assert PartitionCapability.AUTOMATIC != PartitionCapability.UNSUPPORTED
    assert PartitionCapability("automatic") is PartitionCapability("automatic")


class _DeclaringDialect(PartitionMixin):
    """A dialect that renders addressable partition DDL."""

    def supports_table_partitioning(self) -> bool:
        return True


class _DecliningDialect(PartitionMixin):
    """A dialect without partitioning."""

    def supports_table_partitioning(self) -> bool:
        return False


def test_default_maps_true_to_native():
    """A ``True`` boolean keeps its old meaning: native, targetable partitions."""
    assert _DeclaringDialect().partition_capability() is PartitionCapability.NATIVE


def test_default_maps_false_to_unsupported():
    """A ``False`` boolean keeps its old meaning: no partitioning."""
    assert _DecliningDialect().partition_capability() is PartitionCapability.UNSUPPORTED


def test_mixin_default_is_unsupported():
    """The unconfigured mixin partitions nothing."""
    assert PartitionMixin().partition_capability() is PartitionCapability.UNSUPPORTED


@pytest.mark.parametrize("dialect_cls", [DummyDialect, SQLiteDialect], ids=lambda c: c.__name__)
def test_existing_dialects_keep_their_answer(dialect_cls):
    """No existing backend changes its answer; none needs to be edited."""
    dialect = dialect_cls()
    expected = (
        PartitionCapability.NATIVE
        if dialect.supports_table_partitioning()
        else PartitionCapability.UNSUPPORTED
    )
    assert dialect.partition_capability() is expected


def test_automatic_backend_keeps_the_boolean_honest():
    """AUTOMATIC pairs with a ``False`` boolean: storage is partitioned by the
    engine, but there is no partition DDL to address."""
    class _AutomaticDialect(PartitionMixin):
        def supports_table_partitioning(self) -> bool:
            return False

        def partition_capability(self) -> PartitionCapability:
            return PartitionCapability.AUTOMATIC

    dialect = _AutomaticDialect()
    assert dialect.partition_capability() is PartitionCapability.AUTOMATIC
    assert dialect.supports_table_partitioning() is False


def test_protocol_declares_the_method_and_returns_the_enum():
    """Conformance tests have a name to check, with the enum as return type."""
    assert "partition_capability" in PartitionSupport.__dict__
    signature = inspect.signature(PartitionSupport.partition_capability)
    assert signature.return_annotation is PartitionCapability


def test_protocol_and_mixin_signatures_agree():
    """The mixin remains a structural implementation of the protocol."""
    assert isinstance(PartitionMixin(), PartitionSupport)
    assert inspect.signature(PartitionMixin.partition_capability) == inspect.signature(
        PartitionSupport.partition_capability
    )
