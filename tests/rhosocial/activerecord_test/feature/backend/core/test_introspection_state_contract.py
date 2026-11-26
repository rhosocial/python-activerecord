# tests/rhosocial/activerecord_test/feature/backend/core/test_introspection_state_contract.py
"""The neutral object-state contract on the introspection manager.

The manager answers with core dataclasses only; a backend that cannot answer
refuses by name. Sync and async offer the same surface.
"""
import asyncio
import dataclasses
import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import ProtocolNotImplementedError
from rhosocial.activerecord.backend.introspection import types as introspection_types
from rhosocial.activerecord.backend.introspection.base import (
    AbstractIntrospector,
    AsyncAbstractIntrospector,
    IntrospectorMixin,
)


class _Stub(IntrospectorMixin):
    """A manager-shaped object with a dialect name and nothing else."""

    def __init__(self) -> None:
        self._backend = SimpleNamespace(dialect=SimpleNamespace(name="Probe"))

NEW_METHODS = {
    "get_table_state": ("orders",),
    "get_partition_state": ("orders",),
    "list_index_states": ("orders",),
    "list_constraint_states": ("orders",),
    "list_sequence_states": (),
    "list_schemas": (),
    "list_derived_objects": ("orders",),
    "item_exists": (introspection_types.ItemKind.SEQUENCE, "orders_seq"),
}


def _public_methods(cls):
    return {
        name
        for name, value in inspect.getmembers(cls, inspect.isfunction)
        if not name.startswith("_")
    }


def test_sync_and_async_expose_the_same_methods():
    assert _public_methods(AbstractIntrospector) == _public_methods(AsyncAbstractIntrospector)


def test_the_new_methods_are_on_both_managers():
    for name in NEW_METHODS:
        assert hasattr(AbstractIntrospector, name)
        assert hasattr(AsyncAbstractIntrospector, name)


def test_async_twins_are_coroutines():
    for name in NEW_METHODS:
        assert inspect.iscoroutinefunction(getattr(AsyncAbstractIntrospector, name))


@pytest.mark.parametrize("name", sorted(NEW_METHODS))
def test_default_answer_refuses_by_name(name):
    stub = _Stub()

    with pytest.raises(ProtocolNotImplementedError) as caught:
        getattr(AbstractIntrospector, name)(stub, *NEW_METHODS[name])

    message = str(caught.value)
    assert name in message
    assert "Probe" in message


@pytest.mark.parametrize("name", sorted(NEW_METHODS))
def test_async_default_answer_refuses_by_name(name):
    stub = _Stub()

    with pytest.raises(ProtocolNotImplementedError) as caught:
        asyncio.run(getattr(AsyncAbstractIntrospector, name)(stub, *NEW_METHODS[name]))

    assert name in str(caught.value)


def test_partition_state_uses_none_for_unpartitioned():
    state = introspection_types.PartitionState()
    assert state.scheme is None
    assert state.bounds == ()


def test_table_state_defaults():
    state = introspection_types.TableState(name="orders")
    assert state.kind == "regular"
    assert state.partitioning is not None and state.partitioning.scheme is None
    assert state.storage.engine is None


def test_table_state_partitioning_is_a_partition_state_not_optional():
    """``TableState.partitioning`` is never ``None``; ``scheme=None`` answers it.

    The field is a ``PartitionState`` with a factory default, so a table that
    was never asked about partitioning still carries the one neutral answer
    instead of a second, meaningless ``None``.
    """
    (partitioning,) = [
        f for f in dataclasses.fields(introspection_types.TableState) if f.name == "partitioning"
    ]

    annotation = partitioning.type
    if isinstance(annotation, str):
        assert "PartitionState" in annotation
        assert "Optional" not in annotation and "None" not in annotation
    else:
        assert annotation is introspection_types.PartitionState

    assert partitioning.default is dataclasses.MISSING, "a bare None default is the hole"
    state = partitioning.default_factory()
    assert isinstance(state, introspection_types.PartitionState)
    assert state.scheme is None


def test_no_backend_passes_none_as_the_partition_state():
    """A ``partitioning=None`` literal re-opens the hole the contract closed."""
    root = Path(__file__).resolve().parents[6] / "src"
    pattern = re.compile(r"partitioning\s*=\s*None\b|partitioning\s+is\s+None\b")

    offenders = []
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(root)}:{line_number}")

    assert not offenders, (
        "partitioning=None (or partitioning is None) remains in src; an empty "
        "PartitionState whose scheme is None is the only answer:\n"
        + "\n".join(f"  - {o}" for o in offenders)
    )


def test_partition_bound_carries_optional_statistics():
    bound = introspection_types.PartitionBound(name="p0", upper="2026-01-01")
    assert bound.row_count is None
    assert bound.size_bytes is None
    assert not bound.is_default


def test_partition_bound_carries_every_boundary_kind():
    bound = introspection_types.PartitionBound(
        name="p0",
        lower="2026-01-01",
        upper="2026-02-01",
        modulus=4,
        remainder=1,
    )
    assert bound.lower == "2026-01-01"
    assert bound.modulus == 4 and bound.remainder == 1


def test_str_enums_print_their_word():
    assert str(introspection_types.ItemKind.SEQUENCE) == "sequence"
    assert str(introspection_types.PartitionScheme.RANGE) == "range"


def test_index_state_defaults_to_usable_and_visible():
    state = introspection_types.IndexState(name="idx", table="orders")
    assert state.usable
    assert state.visible


def test_item_kinds_cover_shared_objects():
    names = {kind.value for kind in introspection_types.ItemKind}
    assert {"sequence", "type", "function", "partition_function", "partition_scheme"} <= names


def test_scope_has_a_partition_entry():
    assert introspection_types.IntrospectionScope.PARTITION.value == "partition"
