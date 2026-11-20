# tests/rhosocial/activerecord_test/feature/backend/adapters/test_adapters_field_type_adapters.py
"""Selection logic for ``ActiveRecord.get_field_type_adapters()`` (DB-free)."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from typing_extensions import Annotated

from rhosocial.activerecord.base.fields import UseAdapter
from rhosocial.activerecord.backend.adapters.geometry import Geometry
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
from rhosocial.activerecord.backend.impl.sqlite.adapters import SQLiteGeometryAdapter, SQLiteJSONAdapter
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.type_adapter import (
    BaseSQLTypeAdapter,
    DateTimeAdapter,
    DecimalAdapter,
    JSONAdapter,
    UUIDAdapter,
)
from rhosocial.activerecord.model import ActiveRecord


class UpperAdapter(BaseSQLTypeAdapter):
    """A custom adapter that is not part of any backend inventory."""

    def _do_to_database(self, value, target_type, options=None):
        return value.upper()

    def _do_from_database(self, value, target_type, options=None):
        return value.lower()


class DefaultModel(ActiveRecord):
    __primary_key__ = "id"
    """Uses only the framework/backend default suggestions."""

    @classmethod
    def table_name(cls) -> str:
        return "default_adapter_models"

    id: Optional[int] = None
    plain_text: str
    payload: dict
    tags: List[str]
    optional_tags: Optional[List[str]] = None
    created_at: datetime
    birthday: date
    alarm: time
    amount: Decimal
    token: UUID
    raw: bytes
    shape: Optional[Geometry] = None


def test_dummy_backend_uses_core_defaults():
    DefaultModel.configure(SQLiteConnectionConfig(database=":memory:"), DummyBackend)

    adapters = DefaultModel.get_field_type_adapters()

    assert isinstance(adapters["payload"][0], JSONAdapter)
    assert adapters["payload"][1] is str
    assert isinstance(adapters["tags"][0], JSONAdapter)
    assert adapters["tags"][1] is str
    assert isinstance(adapters["optional_tags"][0], JSONAdapter)
    assert isinstance(adapters["created_at"][0], DateTimeAdapter)
    assert adapters["created_at"][1] is str
    assert isinstance(adapters["amount"][0], DecimalAdapter)
    assert adapters["amount"][1] is float
    assert isinstance(adapters["token"][0], UUIDAdapter)
    assert adapters["token"][1] is str
    # Types the driver binds natively are passed through untouched.
    assert adapters["plain_text"] is None
    assert adapters["raw"] is None
    # Neutral families are backend-owned: the dummy backend has no adapter.
    assert adapters["shape"] is None


def test_field_with_declared_custom_adapter_uses_it_verbatim():
    class DeclaredModel(ActiveRecord):
        @classmethod
        def table_name(cls) -> str:
            return "declared_adapter_models"

        id: Optional[int] = None
        notes: Annotated[str, UseAdapter(UpperAdapter(), int)] = ""

    DeclaredModel.configure(SQLiteConnectionConfig(database=":memory:"), DummyBackend)

    adapter, target = DeclaredModel.get_field_type_adapters()["notes"]
    assert isinstance(adapter, UpperAdapter)
    assert target is int


def test_multiple_declarations_prefer_the_one_in_backend_inventory():
    first = UpperAdapter()
    second = SQLiteGeometryAdapter()

    class MultiDeclarationModel(ActiveRecord):
        @classmethod
        def table_name(cls) -> str:
            return "multi_declaration_models"

        id: Optional[int] = None
        shape: Annotated[Geometry, UseAdapter(first, str), UseAdapter(second, str)]

    MultiDeclarationModel.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

    adapter, _ = MultiDeclarationModel.get_field_type_adapters()["shape"]
    assert adapter is second


def test_multiple_declarations_fall_back_to_first_when_inventory_is_empty():
    first = UpperAdapter()
    second = SQLiteGeometryAdapter()

    class EmptyInventoryModel(ActiveRecord):
        @classmethod
        def table_name(cls) -> str:
            return "empty_inventory_models"

        id: Optional[int] = None
        shape: Annotated[Geometry, UseAdapter(first, str), UseAdapter(second, str)]

    EmptyInventoryModel.configure(SQLiteConnectionConfig(database=":memory:"), DummyBackend)

    adapter, _ = EmptyInventoryModel.get_field_type_adapters()["shape"]
    assert adapter is first


def test_sqlite_backend_overrides_core_defaults():
    DefaultModel.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

    adapters = DefaultModel.get_field_type_adapters()

    assert isinstance(adapters["payload"][0], SQLiteJSONAdapter)
    # SQLite has no blob suggestion, so bytes still pass through.
    assert adapters["raw"] is None
    # The neutral families SQLite carries as TEXT are selected by default.
    assert isinstance(adapters["shape"][0], SQLiteGeometryAdapter)
