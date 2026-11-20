# tests/rhosocial/activerecord_test/feature/backend/adapters/test_batch_conversion.py
"""The batch half of the adapter contract.

``BatchConversionMixin`` is what a backend calls when it binds a whole
parameter list at once (``base/execution.py`` builds one such call per
statement). The default is deliberately naive -- one single-value call per
element -- and the point of the tests is that it is *correct* before any
optimisation replaces it: order preserved, ``None`` preserved, and the
per-value options carried through.

The mixin also exists so a backend **may** override it per adapter. That
override point is asserted here rather than left to trust, because an
optimised adapter that is never consulted is an optimisation nobody gets.
"""

import uuid
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.type_adapter import (
    BatchConversionMixin,
    BooleanAdapter,
    DateTimeAdapter,
    DecimalAdapter,
    EnumAdapter,
    JSONAdapter,
    UUIDAdapter,
)


@pytest.mark.parametrize(
    "adapter_factory",
    [DateTimeAdapter, JSONAdapter, UUIDAdapter, EnumAdapter, BooleanAdapter, DecimalAdapter],
    ids=["datetime", "json", "uuid", "enum", "boolean", "decimal"],
)
def test_every_builtin_adapter_exposes_the_batch_pair(adapter_factory):
    """The mixin is inherited, not composed per adapter, so the pair is
    available wherever a single-value conversion is."""
    adapter = adapter_factory()
    assert isinstance(adapter, BatchConversionMixin)
    assert callable(adapter.to_database_batch)
    assert callable(adapter.from_database_batch)


def test_a_batch_write_converts_each_value_in_order():
    adapter = DecimalAdapter()
    values = [Decimal("1.5"), None, Decimal("2")]

    assert adapter.to_database_batch(values, str) == ["1.5", None, "2"]


def test_a_batch_read_converts_each_value_in_order():
    adapter = UUIDAdapter()
    value = uuid.uuid4()

    assert adapter.from_database_batch([str(value), None], uuid.UUID) == [value, None]


def test_an_empty_batch_is_an_empty_list():
    adapter = JSONAdapter()

    assert adapter.to_database_batch([], str) == []
    assert adapter.from_database_batch([], dict) == []


def test_the_per_value_options_reach_the_single_value_conversion():
    """The batch is not a different conversion: a declared precision still
    applies element by element."""
    adapter = DecimalAdapter()

    converted = adapter.from_database_batch(["1.005", "2.004"], Decimal, {"precision": "0.01"})

    assert converted == [Decimal("1.01"), Decimal("2.00")]


def test_the_batch_does_not_share_the_input_list():
    adapter = JSONAdapter()
    values = [{"a": 1}]

    converted = adapter.to_database_batch(values, str)
    converted.append("sentinel")

    assert values == [{"a": 1}]


def test_an_adapter_may_replace_the_batch_behaviour():
    """The default is a floor, not a mandate: a backend that can bind a list
    in one driver call overrides these methods, and its override is what runs.
    This is the hook ``BatchConversionMixin``'s docstring promises."""

    class Recording(DecimalAdapter):
        def __init__(self):
            super().__init__()
            self.calls = []

        def to_database_batch(self, values, target_type, options=None):
            self.calls.append((tuple(values), target_type, options))
            return ["batched"]

    adapter = Recording()
    assert adapter.to_database_batch([Decimal("1.5")], str) == ["batched"]
    assert adapter.calls == [((Decimal("1.5"),), str, None)]
