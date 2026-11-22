# tests/rhosocial/activerecord_test/feature/backend/core/test_get_type_adapters.py
"""DB-free tests for the backend type adapter catalogue."""

from typing import Dict, List, Tuple, Type

import pytest

from rhosocial.activerecord.backend.base.type_adaption import TypeAdaptionMixin
from rhosocial.activerecord.backend.impl.dummy.backend import (
    AsyncDummyBackend,
    DummyBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import (
    AsyncSQLiteBackend,
    SQLiteBackend,
)
from rhosocial.activerecord.backend.type_adapter import (
    SQLTypeAdapter,
    TypeAdapterCatalogProtocol,
)


def _adapter_class_key(adapter: SQLTypeAdapter) -> Tuple[str, str]:
    adapter_cls = type(adapter)
    return (adapter_cls.__module__, adapter_cls.__qualname__)


def _suggestion_class_keys(
    suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]],
) -> List[Tuple[str, str]]:
    """Dedupe and sort suggestion adapters the same way the inventory does."""
    keys = {_adapter_class_key(suggestion[0]) for suggestion in suggestions.values()}
    return sorted(keys)


@pytest.fixture(params=[SQLiteBackend, AsyncSQLiteBackend], ids=["sync", "async"])
def sqlite_backend(request):
    """A SQLite backend instance; no connection is opened."""
    return request.param(database=":memory:")


@pytest.mark.parametrize(
    "backend_factory", [DummyBackend, AsyncDummyBackend], ids=["sync", "async"]
)
def test_dummy_backends_export_an_empty_catalogue(backend_factory):
    """Dummy backends are catalogues too: they explicitly provide nothing."""
    backend = backend_factory()

    assert isinstance(backend, TypeAdapterCatalogProtocol)
    assert backend.get_type_adapters() == []


@pytest.mark.parametrize(
    "backend_factory", [DummyBackend, AsyncDummyBackend], ids=["sync", "async"]
)
def test_dummy_catalogue_is_a_new_list_each_call(backend_factory):
    backend = backend_factory()

    first = backend.get_type_adapters()
    second = backend.get_type_adapters()

    assert first is not second
    first.append(object())  # must not leak into backend state
    assert backend.get_type_adapters() == []


def test_sqlite_backends_export_a_non_empty_catalogue(sqlite_backend):
    assert isinstance(sqlite_backend, TypeAdapterCatalogProtocol)
    adapters = sqlite_backend.get_type_adapters()

    assert adapters
    assert all(isinstance(adapter, SQLTypeAdapter) for adapter in adapters)


def test_sqlite_catalogue_is_unique_and_deterministic(sqlite_backend):
    first = sqlite_backend.get_type_adapters()
    second = sqlite_backend.get_type_adapters()

    keys = [_adapter_class_key(adapter) for adapter in first]
    assert len(keys) == len(set(keys))
    assert keys == sorted(keys)
    assert [_adapter_class_key(adapter) for adapter in second] == keys
    assert first is not second


def test_generic_mixin_inventory_derives_from_suggestions(sqlite_backend):
    """The mixin default is exactly the deduped/sorted suggestion adapters."""
    inventory = TypeAdaptionMixin.get_type_adapters(sqlite_backend)
    expected = _suggestion_class_keys(sqlite_backend.suggest_data_adapters().table)

    assert [_adapter_class_key(adapter) for adapter in inventory] == expected
